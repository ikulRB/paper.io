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

ACK_INTERVAL_MS = 150
PEER_TIMEOUT_MS = 2500
DEDUP_WINDOW = 512
MAX_OUTSTANDING = 64


class Peer:
    def __init__(self, addr):
        self.addr = addr
        self.next_seq = 1
        self.pending = {}
        self.dedup = {}
        self.max_in_seq = -1
        self.last_rx_ms = now_ms()

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
        with self.lock:
            p = self.peer(addr)
            if require_ack:
                p.pending[msg.msg_seq] = (data, now_ms(), on_ack)
                if len(p.pending) > MAX_OUTSTANDING:
                    oldest = min(p.pending.keys())
                    del p.pending[oldest]
        try:
            self.sock.sendto(data, addr)
        except OSError:
            pass

    def _requires_ack(self, msg):
        k = msg.WhichOneof("payload")
        return k not in ("announcement", "discover", "ack", "steer", "state", "ping")
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

            try:
                msg = pb.GameMessage()
                msg.ParseFromString(data)
            except Exception:
                continue
            if msg.protocol_version != PROTOCOL_VERSION:
                continue

            with self.lock:
                p = self.peer(addr)
                p.last_rx_ms = now_ms()

            kind = msg.WhichOneof("payload")

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
                            cached_bytes, _ = cached if isinstance(cached, tuple) else (cached, None)
                            try:
                                self.sock.sendto(cached_bytes, addr)
                            except OSError:
                                pass
                        continue
                try:
                    reply = self.on_message(addr, msg)
                except Exception:
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
                    reply_bytes, _ = reply if isinstance(reply, tuple) else (reply, None)
                    try:
                        self.sock.sendto(reply_bytes, addr)
                    except OSError:
                        pass
            else:
                try:
                    self.on_message(addr, msg)
                except Exception:
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
                try:
                    self.sock.sendto(data, addr)
                except OSError:
                    pass

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
