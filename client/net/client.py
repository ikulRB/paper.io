import socket
import threading
import time
import traceback

try:
    from net import paper_pb2 as pb
except ImportError:
    import sys, os
    sys.path.insert(0, os.path.dirname(__file__))
    import paper_pb2 as pb  # type: ignore

from net.protocol import PROTOCOL_VERSION, now_ms
from config import CATALOG_ADDR

ACK_INTERVAL_MS = 100
PEER_TIMEOUT_MS = 2500
RELAY_FALLBACK_MS = 1000
DEDUP_WINDOW = 1024
MAX_OUTSTANDING = 64


def _log(msg):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}][NET] {msg}", flush=True)


class Peer:
    def __init__(self, addr):
        self.addr = addr
        self.next_seq = 1
        self.pending = {}
        self.dedup = {}
        self.max_in_seq = -1
        self.last_rx_ms = now_ms()
        self.first_tx_ms = 0
        self.direct_confirmed = False
        self.use_relay = False

    def alloc_seq(self):
        s = self.next_seq
        self.next_seq += 1
        if s > 2**63 - 2:
            raise RuntimeError("msg_seq exhausted")
        return s


class NetClient:
    def __init__(self, on_message):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("0.0.0.0", 0))
        self.sock.settimeout(0.05)
        self.on_message = on_message
        self.peers = {}
        self.lock = threading.RLock()
        self.running = True
        _log(f"Socket bound to {self.sock.getsockname()}")
        self.t_recv = threading.Thread(target=self._recv_loop, daemon=True)
        self.t_tick = threading.Thread(target=self._tick_loop, daemon=True)
        self.t_recv.start()
        self.t_tick.start()

    def endpoint(self):
        return self.sock.getsockname()

    def peer(self, addr):
        with self.lock:
            if addr not in self.peers:
                self.peers[addr] = Peer(addr)
            return self.peers[addr]

    def punch_nat(self, target_addr):
        """Отправляет запрос на пробитие NAT через коннект-сервер и пробный пакет напрямую"""
        if not self.running or target_addr == CATALOG_ADDR:
            return
        host, port = target_addr
        _log(f"NAT punch requested for {host}:{port}")
        try:
            self.sock.sendto(f"PUNCH|{host}:{port}".encode("utf-8"), CATALOG_ADDR)
            self.sock.sendto(b"HOLE", target_addr)
        except OSError:
            pass

    def _raw_send_to_peer(self, addr, data):
        if not self.running:
            return
        if addr == CATALOG_ADDR:
            try:
                self.sock.sendto(data, addr)
            except OSError:
                pass
            return

        with self.lock:
            p = self.peer(addr)
            if p.first_tx_ms == 0:
                p.first_tx_ms = now_ms()
            if not p.direct_confirmed and not p.use_relay:
                if now_ms() - p.first_tx_ms >= RELAY_FALLBACK_MS:
                    p.use_relay = True
                    _log(f"Switching peer {addr} to RELAY via {CATALOG_ADDR}")
            use_relay = p.use_relay

        try:
            if use_relay:
                host, port = addr
                header = f"RELAY|{host}:{port}|".encode("utf-8")
                self.sock.sendto(header + data, CATALOG_ADDR)
            else:
                self.sock.sendto(data, addr)
        except OSError:
            pass

    def stop(self):
        self.running = False
        try:
            self.sock.close()
        except OSError:
            pass
        self.t_recv.join(timeout=0.5)
        self.t_tick.join(timeout=0.5)

    def send(self, addr, msg, require_ack=True, on_ack=None):
        if not self.running:
            return
        data = msg.SerializeToString()
        kind = msg.WhichOneof("payload")
        with self.lock:
            p = self.peer(addr)
            if require_ack:
                p.pending[msg.msg_seq] = (data, now_ms(), on_ack)
                if len(p.pending) > MAX_OUTSTANDING:
                    oldest = min(p.pending.keys())
                    del p.pending[oldest]
        if kind not in ("announcement", "ping", "state", "steer"):
            _log(f"SEND -> {addr} kind={kind} seq={msg.msg_seq} ack={require_ack} bytes={len(data)}")
        self._raw_send_to_peer(addr, data)

    def _requires_ack(self, msg):
        k = msg.WhichOneof("payload")
        return k not in ("announcement", "discover", "ack", "steer")
    def _recv_loop(self):
        while self.running:
            try:
                data, addr = self.sock.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError:
                break
            if not self.running:
                break

            # Служебный сигнал пробития NAT от коннект-сервера: "PUNCH|<client_ip:port>"
            if data.startswith(b"PUNCH|"):
                try:
                    peer_str = data[6:].decode("utf-8")
                    h, pt = peer_str.rsplit(":", 1)
                    target = (h, int(pt))
                    _log(f"Received PUNCH signal -> sending HOLE to {target}")
                    self.sock.sendto(b"HOLE", target)
                except Exception:
                    pass
                continue

            if data == b"HOLE":
                with self.lock:
                    p = self.peer(addr)
                    p.direct_confirmed = True
                    p.use_relay = False
                    p.last_rx_ms = now_ms()
                continue

            via_relay = False
            if data.startswith(b"FROM|"):
                rest = data[5:]
                sep = rest.find(b"|")
                if sep <= 0:
                    continue
                try:
                    src_str = rest[:sep].decode("utf-8")
                    h, pt = src_str.rsplit(":", 1)
                    addr = (h, int(pt))
                    data = rest[sep + 1:]
                    via_relay = True
                except Exception:
                    continue

            try:
                msg = pb.GameMessage()
                msg.ParseFromString(data)
            except Exception as e:
                _log(f"RECV PARSE ERROR from {addr}: {e}")
                continue
            if msg.protocol_version != PROTOCOL_VERSION:
                continue

            with self.lock:
                p = self.peer(addr)
                p.last_rx_ms = now_ms()
                if via_relay:
                    if not p.direct_confirmed:
                        p.use_relay = True
                else:
                    p.direct_confirmed = True
                    p.use_relay = False

            kind = msg.WhichOneof("payload")
            if kind not in ("ping", "state", "steer", "ack"):
                _log(f"RECV <- {addr} (relay={via_relay}) kind={kind} seq={msg.msg_seq} sender={msg.sender_id}")

            if kind == "ack":
                with self.lock:
                    entry = p.pending.pop(msg.msg_seq, None)
                if entry is not None:
                    _, _, cb = entry
                    if cb is not None:
                        try:
                            cb(msg)
                        except Exception:
                            traceback.print_exc()
                continue

            if self._requires_ack(msg):
                with self.lock:
                    if msg.msg_seq < p.max_in_seq - DEDUP_WINDOW:
                        continue
                    if msg.msg_seq in p.dedup:
                        cached = p.dedup[msg.msg_seq]
                        if cached is not None and self.running:
                            cached_bytes = cached[0] if isinstance(cached, tuple) else cached
                            self._raw_send_to_peer(addr, cached_bytes)
                        continue
                try:
                    reply = self.on_message(addr, msg)
                except Exception:
                    _log(f"EXCEPTION in on_message for {kind} from {addr}:")
                    traceback.print_exc()
                    reply = None
                with self.lock:
                    p.dedup[msg.msg_seq] = reply
                    if msg.msg_seq > p.max_in_seq:
                        p.max_in_seq = msg.msg_seq
                    floor = p.max_in_seq - DEDUP_WINDOW
                    for k in [k for k in p.dedup.keys() if k <= floor]:
                        del p.dedup[k]
                if reply is not None and self.running:
                    reply_bytes = reply[0] if isinstance(reply, tuple) else reply
                    self._raw_send_to_peer(addr, reply_bytes)
            else:
                try:
                    self.on_message(addr, msg)
                except Exception:
                    _log(f"EXCEPTION in on_message (no-ack) for {kind} from {addr}:")
                    traceback.print_exc()

    def _tick_loop(self):
        while self.running:
            time.sleep(ACK_INTERVAL_MS / 1000.0)
            if not self.running:
                break
            now = now_ms()
            with self.lock:
                entries = []
                for addr, p in self.peers.items():
                    for seq, (data, last, cb) in list(p.pending.items()):
                        if now - last >= ACK_INTERVAL_MS:
                            entries.append((addr, seq, data))
                            p.pending[seq] = (data, now, cb)
            for addr, seq, data in entries:
                if not self.running:
                    break
                self._raw_send_to_peer(addr, data)

    def check_timeouts(self):
        now = now_ms()
        dead = []
        with self.lock:
            for addr, p in self.peers.items():
                if addr == CATALOG_ADDR:
                    continue
                if now - p.last_rx_ms > PEER_TIMEOUT_MS:
                    dead.append(addr)
        return dead
