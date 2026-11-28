import math
import time
import traceback
import pygame

from config import (
    WIDTH, HEIGHT, COLOR_TEXT, COLOR_BG, COLOR_PANEL,
    AVAILABLE_COLORS, DEFAULT_STATE_DELAY_MS, DEFAULT_PLAYERS_PER_GAME,
    MIN_PLAYERS_PER_GAME,
)
from ui.widgets import draw_rounded_button
from ui.end_screen import EndScreen
from net.session import GameSession
from net.discovery import DiscoverySource
from net.protocol import PROTOCOL_VERSION
from game.game import Game
from game.player import Player
try:
    from net import paper_pb2 as pb
except ImportError:
    import paper_pb2 as pb  # type: ignore

# FIX: полный синк территории реже (3 сек вместо 1.5) — меньше «прыжков» формы
FULL_SYNC_INTERVAL_S = 3.0

# FIX: автостарт лобби. Игра начнётся либо при заполнении max_players,
# либо через LOBBY_TIMEOUT_S секунд после первого не-мастер join'а,
# при условии, что в лобби есть хотя бы LOBBY_MIN_PLAYERS игроков.
LOBBY_TIMEOUT_S = 8.0
LOBBY_MIN_PLAYERS = 2


def _parse_name_and_color(raw_name, fallback_idx=0):
    if "#" in raw_name:
        clean_name, idx_str = raw_name.rsplit("#", 1)
        try:
            idx = int(idx_str)
            if 0 <= idx < len(AVAILABLE_COLORS):
                return clean_name, idx
        except ValueError:
            pass
    return raw_name, fallback_idx % len(AVAILABLE_COLORS)


class NetworkPlayState:
    def __init__(self, screen, clock, fonts):
        self.screen = screen
        self.clock = clock
        self.fonts = fonts
        self.session = None
        self.my_id = 0
        self.game = None
        self.disconnected = False
        self.game_started = False
        self._last_steer_dir = 0
        self._last_steer_sent_t = 0.0
        self._end_anim_time = 0.0
        self._sent_territory_versions = {}
        self._last_full_sync_t = 0.0
        self._player_color_indices = {}
        self._fallback_discovery = None
        self._last_rejoin_t = 0.0
        self._migration_grace_until = 0.0

        # FIX: таймер автостарта лобби
        self._lobby_first_join_t = 0.0

        # Общий экран окончания игры
        self.end_screen = EndScreen(screen, fonts)

        self.btn_leave = pygame.Rect(WIDTH - 260, HEIGHT - 70, 240, 50)

    def run(self, session_info):
        self._init_session(session_info)

        while True:
            if self.disconnected:
                self._leave()
                return

            self.session.check_failover()
            self._check_normal_migration()
            mx, my = pygame.mouse.get_pos()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._leave()
                    return
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    is_finished = self.game_started and (self.game.result in ("win", "lose"))
                    if (is_finished
                            and self.end_screen.ok_clicked(event.pos, self._end_anim_time)):
                        self._leave()
                        return
                    if self.btn_leave.collidepoint(event.pos):
                        self._leave()
                        return

            self._poll_steer_keys()
            self._update_logic()

            is_finished = self.game_started and (self.game.result in ("win", "lose"))
            if is_finished:
                self._end_anim_time += 16.67

            self._draw(mx, my, is_finished)
            pygame.display.flip()
            self.clock.tick(60)

    def _init_session(self, info):
        my_color = info.get("color")
        my_color_idx = AVAILABLE_COLORS.index(my_color) if my_color in AVAILABLE_COLORS else 0
        self.game = Game(self.screen, info.get("player_name"), my_color, num_bots=0, is_network=True)
        max_players = info.get("max_players", DEFAULT_PLAYERS_PER_GAME)

        if info.get("session") is not None:
            self.session = info.get("session")
            self.session.max_players = max_players
            self.session.on_state = self._on_new_state
            self.session.on_steer = self._on_remote_steer
            self.session.on_player_join = self._on_remote_join
            self.session.on_player_leave = self._on_remote_leave
            self.session.on_role_change = self._on_role_changed
            self.session.on_error = self._on_session_error
            if self.session.my_id:
                self.my_id = self.session.my_id
        else:
            self.session = GameSession(
                game_name=info.get("game_name"),
                player_name=f"{info.get('player_name')}#{my_color_idx}",
                status=info.get("status", pb.PLAYING),
                max_players=max_players,
                on_state=self._on_new_state,
                on_steer=self._on_remote_steer,
                on_player_join=self._on_remote_join,
                on_player_leave=self._on_remote_leave,
                on_role_change=self._on_role_changed,
                on_error=self._on_session_error,
            )

        if info.get("mode") == "master":
            self.session.role = pb.MASTER
            self.session.master_addr = self.session.net.endpoint()
            self.session.my_id = 1
            self.session.master_id = 1
            self.session.next_player_id = 2
            self.session.player_names = {1: info.get("player_name")}
            self.session.player_status = {1: pb.PLAYING}
            self.session.player_roles = {1: pb.MASTER}
            self.my_id = 1
            self._player_color_indices.update({1: my_color_idx})

            self.game.main_player.player_id = 1

            self.session.on_get_state = self._build_state_from_game
            self.session.state = self._build_state_from_game()
            # FIX: сбрасываем «прогретые» версии территорий, иначе первый
            # broadcast после старта пойдёт без territory и клиенты увидят
            # игроков «без территорий» до FULL_SYNC_INTERVAL_S.
            self._sent_territory_versions.clear()
            self._last_full_sync_t = 0.0
            self.session._maybe_announce()
            self.session._start_ticker()
        else:
            if self.session.my_id:
                self.my_id = self.session.my_id
                self._player_color_indices.update({self.my_id: my_color_idx})
                self.game.main_player.player_id = self.my_id
            if info.get("state") is not None:
                self._on_new_state(info.get("state"))
            elif info.get("session") is None:
                master_pub = info.get("master_pub")
                self.session.join(info.get("master_addr"), master_pub=master_pub)

    def _on_role_changed(self, new_role):
        if new_role == pb.MASTER:
            self._migration_grace_until = time.monotonic() + 0.6
            self.game.network_steer_dirs.clear()
            self._sent_territory_versions.clear()
            self._last_full_sync_t = 0.0
            self.session.on_get_state = self._build_state_from_game
            self.session.state = self._build_state_from_game()
            self.session._maybe_announce()
            self.session._start_ticker()
            if self._fallback_discovery is not None:
                self._fallback_discovery.close()
                self._fallback_discovery = None

    def _check_normal_migration(self):
        if self.session is None or self.session.role != pb.NORMAL:
            return
        if self.session._master_lost_since == 0:
            if self._fallback_discovery is not None:
                self._fallback_discovery.close()
                self._fallback_discovery = None
            return

        if self._fallback_discovery is None:
            self._fallback_discovery = DiscoverySource()

        now_t = time.monotonic()
        if now_t - self._last_rejoin_t < 0.35:
            return
        self._last_rejoin_t = now_t

        for g in self._fallback_discovery.poll():
            if g.get("name") == self.session.game_name:
                new_master = tuple(g.get("master"))
                new_pub = tuple(g.get("master_pub")) if g.get("master_pub") else new_master
                if new_master != self.session.master_addr:
                    self.session.join(new_master, master_pub=new_pub)
                    break

    def _on_session_error(self, addr, err):
        self.disconnected = True

    def _on_remote_join(self, pid, raw_player_name, status):
        for p in self.game.players:
            if p.player_id == pid:
                return
        clean_name, color_idx = _parse_name_and_color(raw_player_name, pid - 1)
        self._player_color_indices.update({pid: color_idx})
        self.session.player_names.update({pid: clean_name})
        color = AVAILABLE_COLORS[color_idx]
        new_p = Player(clean_name, color, self.game.MAP_RADIUS)
        new_p.player_id = pid
        self.game.players.append(new_p)
        # Новый игрок должен получить полную территорию всех на ближайшем тике
        self._sent_territory_versions.clear()

        # FIX: запускаем таймер автостарта при первом не-мастер игроке
        if self._lobby_first_join_t == 0.0 and not self.game_started:
            self._lobby_first_join_t = time.monotonic()

    def _on_remote_leave(self, pid):
        for p in self.game.players:
            if p.player_id == pid and not p.is_dead:
                self.game._kill_player(p)
        self.game.players = [p for p in self.game.players if p.player_id != pid]

    def _on_remote_steer(self, pid, steer_val):
        self.game.apply_steer(pid, steer_val)

    def _build_state_from_game(self):
        state = pb.GameState()
        state.state_order = self.session.state_order
        state.next_player_id = self.session.next_player_id

        state.config.map_radius = float(getattr(self.game, "MAP_RADIUS", 2000.0))
        state.config.state_delay_ms = DEFAULT_STATE_DELAY_MS
        state.config.max_players = self.session.max_players

        now_t = time.monotonic()
        force_full_sync = (now_t - self._last_full_sync_t) >= FULL_SYNC_INTERVAL_S
        if force_full_sync:
            self._last_full_sync_t = now_t
            self._sent_territory_versions.clear()

        for p in list(self.game.players):
            ps = state.players.add()
            ps.player_id = p.player_id
            c_idx = self._player_color_indices.get(p.player_id, (p.player_id - 1) % len(AVAILABLE_COLORS))
            ps.name = f"{p.name}#{c_idx}"
            ps.role = self.session.player_roles.get(p.player_id, pb.NORMAL)
            ps.status = pb.VIEWING if p.is_dead else self.session.player_status.get(p.player_id, pb.PLAYING)
            ps.score = int(p.area_percentage * 100)
            ps.angle = p.angle
            hx, hy = p.get_head()
            ps.head.x = float(hx)
            ps.head.y = float(hy)

            if not p.in_base:
                ps.trail.add(x=float(hx), y=float(hy))

            ver = getattr(p, "territory_version", 1)
            if self._sent_territory_versions.get(p.player_id) != ver:
                self._sent_territory_versions.update({p.player_id: ver})
                # FIX: без downsample — шлём точную форму территории.
                # Иначе при повторной отправке точки «перескакивали»,
                # и у клиентов форма территории мерцала/ломалась.
                for px, py in p.territory_points:
                    ps.territory.add(x=float(px), y=float(py))

        return state

    def _on_new_state(self, state):
        if self.my_id == 0 and self.session.my_id:
            self.my_id = self.session.my_id

        # FIX: на клиентах on_player_join не вызывается (join обрабатывает мастер),
        # поэтому таймер автостарта взводим здесь, как только в state
        # появляется первый не-мастер игрок.
        if not self.game_started and self._lobby_first_join_t == 0.0:
            non_master = [ps for ps in state.players if ps.role != pb.MASTER]
            if non_master:
                self._lobby_first_join_t = time.monotonic()

        net_players = []
        for ps in state.players:
            clean_name, color_idx = _parse_name_and_color(ps.name, ps.player_id - 1)
            self._player_color_indices.update({ps.player_id: color_idx})
            net_players.append({
                "player_id": ps.player_id,
                "name": clean_name,
                "color_idx": color_idx,
                "angle": ps.angle,
                "score": ps.score,
                "is_dead": (ps.status == pb.VIEWING),
                "in_base": (len(ps.trail) == 0),
                "head": (ps.head.x, ps.head.y),
                "territory": [(pt.x, pt.y) for pt in ps.territory],
            })
        try:
            self.game.sync_players(net_players, my_id=self.my_id)
        except Exception:
            traceback.print_exc()

    def _poll_steer_keys(self):
        if self.session is None or not self.game_started or self.game.main_player.is_dead:
            return
        keys = pygame.key.get_pressed()
        steer = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            steer -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            steer += 1

        now_t = time.monotonic()
        need_send = (steer != self._last_steer_dir) or (steer != 0 and (now_t - self._last_steer_sent_t) >= 0.08)
        if need_send:
            self._last_steer_dir = steer
            self._last_steer_sent_t = now_t
            if self.session.role == pb.MASTER:
                self.game.apply_steer(self.my_id, steer)
            elif self.session.master_addr:
                seq = self.session.net.peer(self.session.master_addr).alloc_seq()
                m = pb.GameMessage(
                    protocol_version=PROTOCOL_VERSION,
                    msg_seq=seq,
                    game_name=self.session.game_name,
                    sender_id=self.my_id,
                    receiver_id=self.session.master_id,
                )
                s = pb.SteerMsg()
                s.target_angle = float(steer)
                m.steer.CopyFrom(s)
                self.session.net.send(self.session.master_addr, m, require_ack=False)

    def _update_logic(self):
        # FIX: старт лобби — либо полный состав, либо таймаут после первого join'а.
        # Раньше требовалось ровно len(players) >= max_players, из-за чего
        # при недоборе игра «висела» в ожидании.
        if not self.game_started:
            players_now = len(self.game.players)
            started = False
            if players_now >= self.session.max_players:
                started = True
            elif (players_now >= LOBBY_MIN_PLAYERS
                  and self._lobby_first_join_t > 0.0
                  and time.monotonic() - self._lobby_first_join_t >= LOBBY_TIMEOUT_S):
                started = True
            if started:
                self.game_started = True
                self._lobby_first_join_t = 0.0
                # FIX: принудительный полный синк территорий на первом же
                # тике после старта. Иначе клиенты получат state без territory
                # и увидят «пустые» базы до FULL_SYNC_INTERVAL_S.
                self._sent_territory_versions.clear()
                self._last_full_sync_t = 0.0
            else:
                return

        if self.session.role == pb.MASTER:
            skip_collisions = (time.monotonic() < self._migration_grace_until)
            self.game.update_network(skip_collisions=skip_collisions)
        else:
            self.game.step_client_local(self._last_steer_dir)

    def _draw(self, mx, my, is_finished):
        s = self.screen

        if not self.game_started:
            s.fill(COLOR_BG)
            wait_text = self.fonts["title"].render("ОЖИДАНИЕ ИГРОКОВ...", True, COLOR_TEXT)
            s.blit(wait_text, (WIDTH // 2 - wait_text.get_width() // 2, HEIGHT // 2 - 60))

            need = self.session.max_players
            cnt = len(self.game.players)
            info = self.fonts["ui"].render(f"{cnt} / {need}", True, COLOR_TEXT)
            s.blit(info, (WIDTH // 2 - info.get_width() // 2, HEIGHT // 2))

            draw_rounded_button(s, self.btn_leave, "Выйти",
                                self.btn_leave.collidepoint(mx, my), self.fonts["ui"])
            return

        self.game.draw()

        if is_finished:
            self.end_screen.draw(self.game, self._end_anim_time, mx, my)

        draw_rounded_button(s, self.btn_leave, "Выйти",
                            self.btn_leave.collidepoint(mx, my), self.fonts["ui"])

    def _leave(self):
        try:
            if self.session is not None:
                self.session.resign_master()
                if self.session.role != pb.MASTER and self.session.master_addr:
                    seq = self.session.net.peer(self.session.master_addr).alloc_seq()
                    m = pb.GameMessage(
                        protocol_version=PROTOCOL_VERSION,
                        msg_seq=seq,
                        game_name=self.session.game_name,
                        sender_id=self.my_id,
                        receiver_id=self.session.master_id,
                    )
                    m.leave.CopyFrom(pb.LeaveMsg())
                    self.session.net.send(self.session.master_addr, m, require_ack=False)
                self.session.stop()
        except Exception:
            traceback.print_exc()
        finally:
            if self._fallback_discovery is not None:
                try:
                    self._fallback_discovery.close()
                except Exception:
                    pass
                self._fallback_discovery = None