import math
import time
import traceback
import pygame

from config import (
    WIDTH, HEIGHT, COLOR_TEXT, COLOR_BG, COLOR_PANEL,
    AVAILABLE_COLORS, DEFAULT_STATE_DELAY_MS, DEFAULT_PLAYERS_PER_GAME,
)
from ui.widgets import draw_rounded_button
from net.session import GameSession
from net.discovery import DiscoverySource
from net.protocol import PROTOCOL_VERSION
from game.game import Game
from game.player import Player
try:
    from net import paper_pb2 as pb
except ImportError:
    import paper_pb2 as pb  # type: ignore

FULL_SYNC_INTERVAL_S = 1.5


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


def _downsample_points(pts, min_dist=10.0, max_pts=64):
    n = len(pts)
    if n <= 4:
        return pts
    first_pt = next(iter(pts))
    out = [first_pt]
    last_x, last_y = first_pt
    min_d2 = min_dist * min_dist
    for pt in pts:
        px, py = pt
        dx = px - last_x
        dy = py - last_y
        if dx * dx + dy * dy >= min_d2:
            out.append(pt)
            last_x, last_y = px, py
    last_pt = pts[-1]
    if out[-1] != last_pt:
        out.append(last_pt)
    if len(out) > max_pts:
        step = max(1, len(out) // max_pts)
        out = out[::step]
        if out[-1] != last_pt:
            out.append(last_pt)
    return out


class NetworkPlayState:
    DEATH_RED_DELAY = 900
    DEATH_PANEL_DELAY = 1000
    DEATH_OK_DELAY = 1500

    WIN_COLOR = (40, 160, 60)
    LOSE_COLOR = (200, 30, 30)

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

        self.panel_w, self.panel_h = 440, 420
        self.panel_x = WIDTH // 2 - self.panel_w // 2
        self.ok_btn = pygame.Rect(WIDTH // 2 - 60, 0, 120, 40)
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

            is_finished = self.game_started and (self.game.result in ("win", "lose"))

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._leave()
                    return
                if (is_finished and event.type == pygame.MOUSEBUTTONDOWN
                        and event.button == 1
                        and self._end_anim_time > self.DEATH_OK_DELAY):
                    if self.ok_btn.collidepoint(event.pos):
                        self._leave()
                        return
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.btn_leave.collidepoint(event.pos):
                        self._leave()
                        return

            self._poll_steer_keys()
            self._update_logic()

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
                self.session.join(info.get("master_addr"))

    def _on_role_changed(self, new_role):
        if new_role == pb.MASTER:
            # Даём 0.6 сек на переподключение игроков после смены хоста без ложных коллизий
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
                if new_master != self.session.master_addr:
                    self.session.join(new_master)
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
        self._sent_territory_versions.clear()
        if len(self.game.players) >= self.session.max_players:
            self.game_started = True

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
                terr_pts = _downsample_points(p.territory_points, min_dist=10.0, max_pts=64)
                for px, py in terr_pts:
                    ps.territory.add(x=float(px), y=float(py))

        return state

    def _on_new_state(self, state):
        if self.my_id == 0 and self.session.my_id:
            self.my_id = self.session.my_id

        if len(state.players) >= self.session.max_players:
            self.game_started = True

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
        if not self.game_started:
            if len(self.game.players) >= self.session.max_players:
                self.game_started = True
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
            s.blit(wait_text, (WIDTH // 2 - wait_text.get_width() // 2, HEIGHT // 2 - 50))
            sub_text = self.fonts["ui"].render(
                f"Подключено: {len(self.game.players)}/{self.session.max_players}",
                True, COLOR_TEXT
            )
            s.blit(sub_text, (WIDTH // 2 - sub_text.get_width() // 2, HEIGHT // 2 + 10))
        else:
            self.game.draw()

            role_name = {
                pb.MASTER: "MASTER",
                pb.DEPUTY: "DEPUTY",
                pb.NORMAL: "NORMAL",
            }.get(self.session.role, "?")
            role_surf = self.fonts["ui"].render(f"Сеть: {role_name} (ID {self.my_id})", True, (0, 0, 0))
            s.blit(role_surf, (20, HEIGHT - 35))

            if is_finished:
                self._draw_end_overlay(mx, my)

        draw_rounded_button(s, self.btn_leave, "Выйти", self.btn_leave.collidepoint(mx, my), self.fonts["ui"])

    def _draw_end_overlay(self, mx, my):
        win = (self.game.result == "win")
        overlay_color = (30, 120, 40) if win else (160, 20, 20)

        if self._end_anim_time > self.DEATH_RED_DELAY:
            alpha = min(110, int((self._end_anim_time - self.DEATH_RED_DELAY) * 0.18))
            surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            surf.fill((*overlay_color, alpha))
            self.screen.blit(surf, (0, 0))

        if self._end_anim_time >= self.DEATH_PANEL_DELAY:
            panel_y = self._compute_panel_y()
            self._draw_panel(panel_y, win)
            if self._end_anim_time > self.DEATH_OK_DELAY:
                self._draw_ok_button(panel_y, mx, my)

    def _compute_panel_y(self):
        progress = min(1.0, (self._end_anim_time - self.DEATH_PANEL_DELAY) / 500.0)
        elastic_offset = math.sin(progress * math.pi) * 30 * (1.0 - progress)
        return int(-self.panel_h + (HEIGHT // 2 - self.panel_h // 2 + self.panel_h) * progress - elastic_offset)

    def _draw_panel(self, panel_y, win):
        s = self.screen
        pygame.draw.rect(s, COLOR_PANEL, (self.panel_x, panel_y, self.panel_w, self.panel_h), border_radius=14)
        pygame.draw.rect(s, (0, 0, 0), (self.panel_x, panel_y, self.panel_w, self.panel_h), width=3, border_radius=14)

        title_text = "ПОБЕДА!" if win else "ПОРАЖЕНИЕ"
        title_color = self.WIN_COLOR if win else self.LOSE_COLOR
        go = self.game.font_gameover.render(title_text, True, title_color)
        s.blit(go, (WIDTH // 2 - go.get_width() // 2, panel_y + 20))

        score = self.game.font_name.render(
            f"Ваша доля: {self.game.main_player.area_percentage:.2f} %", True, COLOR_TEXT
        )
        s.blit(score, (WIDTH // 2 - score.get_width() // 2, panel_y + 75))

        self._draw_end_minimap(panel_y)

    def _draw_end_minimap(self, panel_y):
        s = self.screen
        radius = 110
        m_cx, m_cy = WIDTH // 2, panel_y + 220
        scale = radius / self.game.MAP_RADIUS

        pygame.draw.circle(s, (230, 230, 230), (m_cx, m_cy), radius)

        for p in self.game.players:
            if p.is_dead or len(p.territory_points) <= 2:
                continue
            mini = [(int(x * scale + m_cx), int(y * scale + m_cy)) for x, y in p.territory_points]
            pygame.draw.polygon(s, p.territory_color, mini)

        if self.game.main_player.is_dead and len(self.game.final_territory_points) > 2:
            mini = [(int(x * scale + m_cx), int(y * scale + m_cy)) for x, y in self.game.final_territory_points]
            pygame.draw.polygon(s, self.game.final_territory_color, mini)

        pygame.draw.circle(s, (40, 40, 40), (m_cx, m_cy), radius, 2)

    def _draw_ok_button(self, panel_y, mx, my):
        self.ok_btn.y = panel_y + 355
        hover = self.ok_btn.collidepoint(mx, my)
        draw_rounded_button(self.screen, self.ok_btn, "OK", hover, self.fonts["ui"])

    def _leave(self):
        if self._fallback_discovery is not None:
            self._fallback_discovery.close()
            self._fallback_discovery = None
        if self.session is not None:
            try:
                if self.session.role == pb.MASTER:
                    self.session.resign_master()
                elif self.session.master_addr:
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
            except Exception:
                pass
            self.session.stop()
            self.session = None
