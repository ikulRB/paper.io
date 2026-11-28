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


def _get_all_local_ips():
    """Возвращает множество всех локальных IPv4-адресов машины."""
    ips = set()
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ips.add(info[4][0])
    except Exception:
        pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ips.add(s.getsockname()[0])
        s.close()
    except Exception:
        pass
    ips.discard("127.0.0.1")
    ips.discard("0.0.0.0")
    return ips


def _is_private_ip(ip):
    try:
        parts = [int(x) for x in ip.split(".")]
        if len(parts) != 4:
            return False
        if parts[0] == 10:
            return True
        if parts[0] == 172 and 16 <= parts[1] <= 31:
            return True
        if parts[0] == 192 and parts[1] == 168:
            return True
    except Exception:
        pass
    return False


class DiscoverySource:
    DISCOVER_PERIOD_S = 1.0

    def __init__(self, catalog_addr=CATALOG_ADDR):
        self.catalog_addr = catalog_addr
        self.my_local_ips = _get_all_local_ips()
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
                pub_addr = addr
                if "|" in raw_name:
                    raw_name, pub_str = raw_name.rsplit("|", 1)
                    if ":" in pub_str:
                        h, p = pub_str.rsplit(":", 1)
                        try:
                            pub_addr = (h, int(p))
                        except ValueError:
                            pass

                lan_addr = None
                if "@" in raw_name:
                    clean_name, lan_str = raw_name.rsplit("@", 1)
                    if ":" in lan_str:
                        lh, lp = lan_str.rsplit(":", 1)
                        try:
                            lan_addr = (lh, int(lp))
                        except ValueError:
                            pass
                else:
                    clean_name = raw_name

                if lan_addr is not None:
                    lan_ip, _ = lan_addr
                    if _is_private_ip(lan_ip) and self.my_local_ips:
                        master_addr = lan_addr
                    else:
                        master_addr = pub_addr
                else:
                    master_addr = pub_addr

                # Ключ — по (имя, публичный адрес): LAN-адрес может меняться,
                # а публичный стабилен для конкретного сокета мастера.
                self.entries[(clean_name, pub_addr)] = (
                    clean_name, g, now, master_addr, pub_addr,
                )

    def poll(self):
        out = []
        now = now_ms()
        with self.lock:
            for key in [k for k, (_, _, t, _, _) in self.entries.items()
                        if now - t > ANNOUNCE_TTL_MS]:
                del self.entries[key]
            for (clean_name, _pub), (_, g, _, master_addr, pub_addr) in self.entries.items():
                max_p = g.config.max_players if g.config.max_players > 0 else DEFAULT_PLAYERS_PER_GAME
                out.append({
                    "name": clean_name,
                    "master": master_addr,       # куда слать join (может быть LAN)
                    "master_pub": pub_addr,      # публичный адрес для hole punching
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