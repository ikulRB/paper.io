import threading
import time
import traceback

try:
    from net import paper_pb2 as pb
except ImportError:
    import sys, os
    sys.path.insert(0, os.path.dirname(__file__))
    import paper_pb2 as pb  # type: ignore

from net.client import NetClient
from net.protocol import PROTOCOL_VERSION, now_ms
from config import CATALOG_ADDR, DEFAULT_PLAYERS_PER_GAME, DEFAULT_STATE_DELAY_MS

ANNOUNCE_INTERVAL_MS = 1000
PING_INTERVAL_MS = 500


def _slog(msg):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}][SESSION] {msg}", flush=True)


class GameSession:
    def __init__(self, game_name, player_name, status, max_players=DEFAULT_PLAYERS_PER_GAME,
                 on_state=None, on_role_change=None, on_error=None, on_steer=None,
                 on_get_state=None, on_player_join=None, on_player_leave=None):
        self.game_name = game_name
        self.player_name = player_name
        self.status = status
        self.max_players = max_players
        self.on_steer = on_steer
        self.on_get_state = on_get_state
        self.on_player_join = on_player_join
        self.on_player_leave = on_player_leave

        self.my_id = 0
        self.role = pb.NORMAL
        self.master_addr = None
        self.master_id = 0
        self.deputy_addr = None
        self.deputy_id = 0

        self.other_addrs = {}
        self.player_names = {}
        self.player_roles = {}
        self.player_status = {}
        self.rtt = {}
        self.rtt_ping_sent = {}

        self.state = None
        self.state_order = -1
        self.next_player_id = 1

        self.on_state = on_state
        self.on_role_change = on_role_change
        self.on_error = on_error

        self.lock = threading.RLock()
        self.net = NetClient(on_message=self._on_message)
        self.running = True
        self.ticker_thread = None
        self._last_announce = 0
        self._last_ping = 0

    def join(self, master_addr):
        _slog(f"join() called -> master_addr={master_addr}, game={self.game_name}, player={self.player_name}")
        self.master_addr = master_addr
        self.net.punch_nat(master_addr)
        self._send_join(master_addr)

    def _send_join(self, addr):
        seq = self.net.peer(addr).alloc_seq()
        j = pb.JoinMsg()
        j.game_name = self.game_name
        j.player_name = self.player_name
        j.requested_status = self.status
        msg = pb.GameMessage(protocol_version=PROTOCOL_VERSION, msg_seq=seq,
                             game_name=self.game_name)
        msg.join.CopyFrom(j)
        self.net.send(addr, msg, require_ack=True)

    def stop(self):
        _slog("stop() called")
        self.running = False
        self.net.stop()

    def _ack(self, addr, seq):
        a = pb.AckMsg()
        a.ack_seq = seq
        m = pb.GameMessage(protocol_version=PROTOCOL_VERSION, msg_seq=seq)
        m.ack.CopyFrom(a)
        return (m.SerializeToString(), m)

    def _error(self, addr, request_seq, text):
        e = pb.ErrorMsg()
        e.request_seq = request_seq
        e.message = text
        m = pb.GameMessage(protocol_version=PROTOCOL_VERSION,
                           msg_seq=self.net.peer(addr).alloc_seq(),
                           game_name=self.game_name)
        m.error.CopyFrom(e)
        return (m.SerializeToString(), m)

    def _on_message(self, addr, msg):
        kind = msg.WhichOneof("payload")
        if kind == "join":
            return self._on_join(addr, msg)
        if kind == "leave":
            return self._on_leave(addr, msg)
        if kind == "steer":
            return self._on_steer(addr, msg)
        if kind == "state":
            return self._on_state(addr, msg)
        if kind == "ping":
            return self._on_ping(addr, msg)
        if kind == "role_change":
            return self._on_role_change(addr, msg)
        if kind == "status_change":
            return self._on_status_change(addr, msg)
        if kind == "error":
            _slog(f"Received ErrorMsg from {addr}: {msg.error.message}")
            if self.on_error is not None:
                try:
                    self.on_error(addr, msg.error)
                except Exception:
                    traceback.print_exc()
            return None
        return None

    def _on_join(self, addr, msg):
        with self.lock:
            j = msg.join
            _slog(f"_on_join from {addr}: player={j.player_name}, game={j.game_name}, my_role={self.role}")
            for pid, a in self.other_addrs.items():
                if a == addr:
                    _slog(f"_on_join duplicate from {addr}, returning ACK")
                    return self._ack(addr, msg.msg_seq)

            if self.role != pb.MASTER:
                _slog(f"_on_join ignored: I am not MASTER (role={self.role})")
                return None

            if len(self.player_names) >= self.max_players:
                _slog(f"_on_join rejected: game full ({len(self.player_names)}/{self.max_players})")
                return self._error(addr, msg.msg_seq, "game full")

            pid = self.next_player_id
            self.next_player_id += 1
            self.player_names[pid] = j.player_name
            self.player_status[pid] = j.requested_status
            self.other_addrs[pid] = addr
            self.player_roles[pid] = pb.NORMAL
            _slog(f"Assigned pid={pid} to {j.player_name} @ {addr}")

            if self.on_player_join is not None:
                try:
                    self.on_player_join(pid, j.player_name, j.requested_status)
                except Exception:
                    _slog("Exception in on_player_join:")
                    traceback.print_exc()

            if self.on_get_state is not None:
                try:
                    self.state = self.on_get_state()
                except Exception:
                    _slog("Exception in on_get_state during _on_join:")
                    traceback.print_exc()
            elif self.state is not None:
                ps = self.state.players.add()
                ps.player_id = pid
                ps.name = j.player_name
                ps.role = pb.NORMAL
                ps.status = j.requested_status
                ps.score = 0
                ps.angle = 0.0
                ps.head.x = 0.0
                ps.head.y = 0.0

            self._ensure_deputy()
            self._broadcast_state()
            return self._ack(addr, msg.msg_seq)

    def _on_steer(self, addr, msg):
        with self.lock:
            if self.role == pb.MASTER:
                pid = msg.sender_id
                if pid == 0:
                    for p_id, a in self.other_addrs.items():
                        if a == addr:
                            pid = p_id
                            break
                ang = msg.steer.target_angle
                if self.on_steer is not None and pid != 0:
                    try:
                        self.on_steer(pid, ang)
                    except Exception:
                        traceback.print_exc()
            return self._ack(addr, msg.msg_seq)

    def _on_leave(self, addr, msg):
        with self.lock:
            if self.role == pb.MASTER:
                self._remove_player(addr)
                self._broadcast_state()
            return self._ack(addr, msg.msg_seq)

    def _on_status_change(self, addr, msg):
        with self.lock:
            if self.role != pb.MASTER:
                return self._ack(addr, msg.msg_seq)
            target = msg.status_change.requested_status
            pid = msg.sender_id
            if pid in self.player_status:
                self.player_status[pid] = target
                if self.state is not None:
                    for p in self.state.players:
                        if p.player_id == pid:
                            p.status = target
                self._broadcast_state()
            return self._ack(addr, msg.msg_seq)

    def _on_ping(self, addr, msg):
        pm = msg.ping
        sender = msg.sender_id
        if sender == 0:
            return None
        key = self.rtt_ping_sent.pop(sender, None)
        if key is not None:
            self.rtt[sender] = now_ms() - pm.sent_at_ms
        reply = pb.GameMessage(
            protocol_version=PROTOCOL_VERSION,
            msg_seq=self.net.peer(addr).alloc_seq(),
            game_name=self.game_name,
            sender_id=self.my_id, receiver_id=sender,
        )
        reply.ping.CopyFrom(pm)
        self.net.send(addr, reply, require_ack=False)
        return None

    def _on_state(self, addr, msg):
        with self.lock:
            gs = msg.state.state
            if gs.state_order <= self.state_order:
                return self._ack(addr, msg.msg_seq)
            if self.state_order == -1:
                _slog(f"First StateMsg received from {addr}! order={gs.state_order}, players={len(gs.players)}")
            self.state = gs
            self.state_order = gs.state_order
            if self.state.config.max_players > 0:
                self.max_players = self.state.config.max_players
            if self.my_id == 0:
                if msg.receiver_id != 0:
                    self.my_id = msg.receiver_id
                elif gs.next_player_id > 1:
                    self.my_id = gs.next_player_id - 1
                else:
                    for p in reversed(list(self.state.players)):
                        if p.name == self.player_name:
                            self.my_id = p.player_id
                            break
                for p in self.state.players:
                    if p.role == pb.MASTER:
                        self.master_id = p.player_id
                _slog(f"Resolved my_id={self.my_id}, master_id={self.master_id}")
            if self.on_state is not None:
                try:
                    self.on_state(self.state)
                except Exception:
                    _slog("Exception in on_state callback:")
                    traceback.print_exc()
            return self._ack(addr, msg.msg_seq)
    def _on_role_change(self, addr, msg):
        rc = msg.role_change
        with self.lock:
            if rc.receiver_role == pb.MASTER:
                self._take_master(addr, rc.state_order)
            elif rc.receiver_role == pb.DEPUTY:
                self.role = pb.DEPUTY
                self.deputy_addr = self.net.endpoint()
                self.deputy_id = self.my_id
                self.master_addr = addr
            if rc.sender_role == pb.NORMAL and msg.sender_id:
                self._remove_player_id(msg.sender_id)
            if self.on_role_change is not None:
                try:
                    self.on_role_change(self.role)
                except Exception:
                    traceback.print_exc()
            return self._ack(addr, msg.msg_seq)

    def _ensure_deputy(self):
        if self.role != pb.MASTER or self.deputy_addr is not None:
            return
        candidates = [(pid, a) for pid, a in self.other_addrs.items()
                      if pid != self.my_id
                      and self.player_roles.get(pid, pb.NORMAL) == pb.NORMAL]
        if not candidates:
            return
        pid, addr = min(candidates, key=lambda x: self.rtt.get(x, 10**9))
        self.player_roles[pid] = pb.DEPUTY
        self.deputy_addr = addr
        self.deputy_id = pid
        rc = pb.NodeRoleChangeMsg()
        rc.receiver_role = pb.DEPUTY
        rc.sender_role = pb.MASTER
        rc.state_order = self.state_order + 1
        m = pb.GameMessage(protocol_version=PROTOCOL_VERSION,
                           msg_seq=self.net.peer(addr).alloc_seq(),
                           game_name=self.game_name,
                           sender_id=self.my_id, receiver_id=pid)
        m.role_change.CopyFrom(rc)
        self.net.send(addr, m, require_ack=True)

    def _take_master(self, from_addr, new_state_order):
        old_master_id = self.master_id
        self.role = pb.MASTER
        self.master_addr = self.net.endpoint()
        self.master_id = self.my_id
        self.state_order = max(self.state_order, new_state_order - 1)
        self.player_roles[self.my_id] = pb.MASTER
        if old_master_id and old_master_id != self.my_id:
            self._remove_player_id(old_master_id)
        self.deputy_addr = None
        self.deputy_id = 0
        self._ensure_deputy()
        self._start_ticker()
        if self.on_role_change is not None:
            try:
                self.on_role_change(self.role)
            except Exception:
                traceback.print_exc()

    def _start_ticker(self):
        if self.ticker_thread is not None and self.ticker_thread.is_alive():
            return
        _slog("Starting MASTER ticker thread")
        self.ticker_thread = threading.Thread(target=self._ticker_loop, daemon=True)
        self.ticker_thread.start()

    def _ticker_loop(self):
        delay = DEFAULT_STATE_DELAY_MS / 1000.0
        while self.running and self.role == pb.MASTER:
            t0 = time.monotonic()
            self._broadcast_state()
            self._maybe_announce()
            self._send_pings()
            elapsed = time.monotonic() - t0
            time.sleep(max(0.0, delay - elapsed))

    def _broadcast_state(self):
        if self.role != pb.MASTER:
            return
        if self.on_get_state is not None:
            try:
                new_state = self.on_get_state()
                if new_state is not None:
                    self.state = new_state
            except Exception:
                _slog("Exception in on_get_state:")
                traceback.print_exc()
        if self.state is None:
            return
        self.state_order += 1
        self.state.state_order = self.state_order
        self.state.next_player_id = self.next_player_id
        targets = [(pid, addr) for pid, addr in self.other_addrs.items()
                   if pid != self.my_id]
        for pid, addr in targets:
            m = pb.GameMessage(protocol_version=PROTOCOL_VERSION,
                               msg_seq=self.net.peer(addr).alloc_seq(),
                               game_name=self.game_name,
                               sender_id=self.my_id, receiver_id=pid)
            m.state.CopyFrom(pb.StateMsg(state=self.state))
            self.net.send(addr, m, require_ack=True)

    def _maybe_announce(self):
        now = now_ms()
        if now - self._last_announce < ANNOUNCE_INTERVAL_MS:
            return
        self._last_announce = now
        ann = pb.AnnouncementMsg()
        g = ann.games.add()
        g.game_name = self.game_name
        g.can_join = len(self.player_names) < self.max_players
        g.players_count = max(1, len(self.player_names))
        if self.state is not None:
            g.config.CopyFrom(self.state.config)
        g.config.max_players = self.max_players
        m = pb.GameMessage(protocol_version=PROTOCOL_VERSION,
                           msg_seq=self.net.peer(CATALOG_ADDR).alloc_seq(),
                           game_name=self.game_name)
        m.announcement.CopyFrom(ann)
        self.net.send(CATALOG_ADDR, m, require_ack=False)

    def _remove_player(self, addr):
        with self.lock:
            for pid, a in list(self.other_addrs.items()):
                if a == addr:
                    self._remove_player_id(pid)

    def _remove_player_id(self, pid):
        self.other_addrs.pop(pid, None)
        self.player_names.pop(pid, None)
        self.player_status.pop(pid, None)
        self.player_roles.pop(pid, None)
        self.rtt.pop(pid, None)
        if self.on_player_leave is not None:
            try:
                self.on_player_leave(pid)
            except Exception:
                traceback.print_exc()
        if self.deputy_id == pid:
            self.deputy_addr = None
            self.deputy_id = 0
            self._ensure_deputy()
        if self.state is not None:
            keep = [p for p in self.state.players if p.player_id != pid]
            del self.state.players[:]
            self.state.players.extend(keep)

    def check_failover(self):
        dead = self.net.check_timeouts()
        if not dead:
            self._send_pings()
            return
        with self.lock:
            if self.role == pb.NORMAL and self.master_addr in dead:
                if self.deputy_addr and self.deputy_addr not in dead:
                    self.master_addr = self.deputy_addr
                    self._send_join(self.master_addr)
                else:
                    if self.on_error is not None:
                        try:
                            self.on_error(None, None)
                        except Exception:
                            traceback.print_exc()
            elif self.role == pb.MASTER:
                for addr in dead:
                    self._remove_player(addr)
                self._broadcast_state()

    def _send_pings(self):
        now = now_ms()
        if now - self._last_ping < PING_INTERVAL_MS:
            return
        self._last_ping = now
        with self.lock:
            for pid, addr in list(self.other_addrs.items()):
                if pid == self.my_id:
                    continue
                seq = self.net.peer(addr).alloc_seq()
                pm = pb.PingMsg()
                pm.sent_at_ms = now
                m = pb.GameMessage(protocol_version=PROTOCOL_VERSION,
                                   msg_seq=seq, game_name=self.game_name,
                                   sender_id=self.my_id, receiver_id=pid)
                m.ping.CopyFrom(pm)
                self.rtt_ping_sent[pid] = (seq, now)
                self.net.send(addr, m, require_ack=False)
