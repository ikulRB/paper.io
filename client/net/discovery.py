import socket
import threading
import time

try:
    from net import paper_pb2 as pb
except ImportError:
    import sys, os
    sys.path.insert(0, os.path.dirname(__file__))
    import paper_pb2 as pb  # type: ignore

from net.protocol import PROTOCOL_VERSION, now_ms
from config import CATALOG_ADDR, ANNOUNCE_TTL_MS, DEFAULT_PLAYERS_PER_GAME


class DiscoverySource:
    DISCOVER_PERIOD_S = 1.0

    def __init__(self, catalog_addr=CATALOG_ADDR):
        self.catalog_addr = catalog_addr
        self.entries = {}
        self.lock = threading.Lock()
        self.running = True

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("", 0))
        self.sock.settimeout(0.1)

        self.seq = 0

        threading.Thread(target=self._discover_loop, daemon=True).start()
        threading.Thread(target=self._recv_loop, daemon=True).start()

    def _discover_loop(self):
        while self.running:
            self._send_discover()
            time.sleep(self.DISCOVER_PERIOD_S)

    def _send_discover(self):
        self.seq += 1
        m = pb.GameMessage(protocol_version=PROTOCOL_VERSION, msg_seq=self.seq)
        m.discover.CopyFrom(pb.DiscoverMsg())
        try:
            self.sock.sendto(m.SerializeToString(), self.catalog_addr)
        except OSError:
            pass

    def _recv_loop(self):
        while self.running:
            try:
                data, addr = self.sock.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError:
                break
            self._handle(data, addr)

    def _handle(self, data, addr):
        try:
            m = pb.GameMessage()
            m.ParseFromString(data)
        except Exception:
            return
        if m.protocol_version != PROTOCOL_VERSION:
            return
        if m.WhichOneof("payload") != "announcement":
            return
        now = now_ms()
        with self.lock:
            for g in m.announcement.games:
                raw_name = g.game_name
                master_addr = addr
                if "|" in raw_name:
                    clean_name, host_port = raw_name.rsplit("|", 1)
                    if ":" in host_port:
                        h, p = host_port.rsplit(":", 1)
                        try:
                            master_addr = (h, int(p))
                        except ValueError:
                            pass
                else:
                    clean_name = raw_name
                self.entries[(clean_name, master_addr)] = (clean_name, g, now)

    def poll(self):
        out = []
        now = now_ms()
        with self.lock:
            for key in [k for k, (_, _, t) in self.entries.items()
                        if now - t > ANNOUNCE_TTL_MS]:
                del self.entries[key]
            for (clean_name, addr), (_, g, _) in self.entries.items():
                max_p = g.config.max_players if g.config.max_players > 0 else DEFAULT_PLAYERS_PER_GAME
                out.append({
                    "name": clean_name,
                    "master": addr,
                    "players": g.players_count,
                    "max_players": max_p,
                    "can_join": g.can_join,
                    "config": g.config,
                })
        return out

    def close(self):
        self.running = False
        try:
            self.sock.close()
        except OSError:
            pass
