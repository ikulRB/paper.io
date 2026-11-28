import time
import pygame

from config import (
    WIDTH, HEIGHT, COLOR_BG, COLOR_TEXT, COLOR_PANEL,
    COLOR_BTN, COLOR_BTN_HOVER, COLOR_PLACEHOLDER,
    JOIN_TIMEOUT_S, MIN_PLAYERS_PER_GAME, MAX_PLAYERS_PER_GAME,
    DEFAULT_PLAYERS_PER_GAME, AVAILABLE_COLORS,
)
from ui.widgets import (
    draw_rounded_button, draw_rounded_button_colored,
    draw_text_input, draw_vertical_scroll_list,
)
from net.discovery import DiscoverySource
from net.session import GameSession
try:
    from net import paper_pb2 as pb
except ImportError:
    import paper_pb2 as pb  # type: ignore


def _llog(msg):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}][LOBBY] {msg}", flush=True)


class LobbyState:
    ITEM_H = 56
    LIST_RECT = pygame.Rect(60, 140, WIDTH - 120, 480)

    def __init__(self, screen, clock, fonts, player_name, player_color):
        self.screen = screen
        self.clock = clock
        self.fonts = fonts
        self.player_name = player_name
        self.color = player_color

        self.discovery = DiscoverySource()
        self.games = []
        self.selected_idx = -1
        self.scroll = 0

        self.creating = False
        self.game_name_input = ""
        self.input_active = False
        self.max_players_selected = DEFAULT_PLAYERS_PER_GAME
        self.dragging_slider = False
        self._pending_master = None

        self.joining = None
        self.status_line = ""

        self.btn_back = pygame.Rect(30, 30, 120, 40)
        self.btn_create = pygame.Rect(WIDTH - 300, 30, 270, 40)
        self.btn_join = pygame.Rect(WIDTH - 300, 700, 270, 40)

        self.input_rect = pygame.Rect(WIDTH // 2 - 220, 290, 440, 40)
        self.slider_rect = pygame.Rect(WIDTH // 2 - 220, 385, 440, 12)
        self.btn_confirm_create = pygame.Rect(WIDTH // 2 - 120, 435, 240, 40)
        self.btn_cancel_create = pygame.Rect(WIDTH // 2 - 120, 490, 240, 40)

    def run(self):
        while True:
            if self._pending_master is not None:
                result = self._pending_master
                self._pending_master = None
                self._cancel_joining()
                self.discovery.close()
                return result

            join_res = self._poll_joining()
            if join_res is not None:
                self.discovery.close()
                return join_res

            self.games = self.discovery.poll()
            self._clamp_scroll()

            mx, my = pygame.mouse.get_pos()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._cancel_joining()
                    self.discovery.close()
                    return None

                if event.type == pygame.KEYDOWN and self.creating and self.input_active:
                    self._handle_create_key(event)

                if event.type == pygame.MOUSEWHEEL:
                    self.scroll -= event.y * 40
                    self._clamp_scroll()

                if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self.dragging_slider = False

                if event.type == pygame.MOUSEMOTION and self.creating and self.dragging_slider:
                    self._update_slider_from_pos(event.pos)

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    result = self._click(event.pos)
                    if result is None:
                        continue
                    if result.get("action") == "back":
                        self._cancel_joining()
                        self.discovery.close()
                        return None
                    if "mode" in result:
                        self._cancel_joining()
                        self.discovery.close()
                        return result

            self._draw(mx, my)
            pygame.display.flip()
            self.clock.tick(30)

    def _update_slider_from_pos(self, pos):
        px, _ = pos
        rel = (px - self.slider_rect.x) / float(self.slider_rect.width)
        rel = max(0.0, min(1.0, rel))
        span = MAX_PLAYERS_PER_GAME - MIN_PLAYERS_PER_GAME
        self.max_players_selected = MIN_PLAYERS_PER_GAME + round(rel * span)

    def _click(self, pos):
        if self.creating:
            slider_hit = self.slider_rect.inflate(20, 24)
            if slider_hit.collidepoint(pos):
                self.dragging_slider = True
                self._update_slider_from_pos(pos)
                return None
            if self.btn_confirm_create.collidepoint(pos):
                name = self.game_name_input.strip()
                if not name:
                    self.status_line = "Введите имя игры"
                    return None
                return self._make_master(name)
            if self.btn_cancel_create.collidepoint(pos):
                self.creating = False
                self.dragging_slider = False
                self.game_name_input = ""
                return None
            if self.input_rect.collidepoint(pos):
                self.input_active = True
            return None

        if self.btn_back.collidepoint(pos):
            return {"action": "back"}
        if self.btn_create.collidepoint(pos):
            self._cancel_joining()
            self.creating = True
            self.input_active = True
            return None
        if self.btn_join.collidepoint(pos):
            if self.joining is not None:
                return None
            if 0 <= self.selected_idx < len(self.games):
                self._start_join(self.games[self.selected_idx])
                return None
            self.status_line = "Выберите игру"
            return None

        if self.LIST_RECT.collidepoint(pos):
            idx = self._index_at(pos)
            if idx is not None:
                self.selected_idx = idx
        return None

    def _handle_create_key(self, event):
        if event.key == pygame.K_RETURN:
            name = self.game_name_input.strip()
            if name:
                self._pending_master = self._make_master(name)
            else:
                self.status_line = "Имя не может быть пустым"
        elif event.key == pygame.K_ESCAPE:
            self.creating = False
            self.dragging_slider = False
        elif event.key == pygame.K_BACKSPACE:
            self.game_name_input = self.game_name_input[:-1]
        elif event.unicode and event.unicode.isprintable():
            if len(self.game_name_input) < 32:
                self.game_name_input += event.unicode

    def _make_master(self, name):
        return {
            "mode": "master",
            "game_name": name,
            "player_name": self.player_name,
            "color": self.color,
            "max_players": self.max_players_selected,
        }

    def _cancel_joining(self):
        if self.joining is not None:
            try:
                self.joining["session"].stop()
            except Exception:
                pass
            self.joining = None

    def _start_join(self, g):
        master = tuple(g["master"])
        master_pub = tuple(g["master_pub"]) if g.get("master_pub") else master
        self.status_line = f"Подключение к {g['name']}…"

        state_received = {"state": None}
        error_msg = {"text": None}

        def on_state(state):
            state_received["state"] = state

        def on_error(addr, err):
            msg_txt = err.message if err is not None else "disconnected"
            error_msg["text"] = msg_txt

        color_idx = AVAILABLE_COLORS.index(self.color) if self.color in AVAILABLE_COLORS else 0
        encoded_player_name = f"{self.player_name}#{color_idx}"

        session = GameSession(
            game_name=g["name"],
            player_name=encoded_player_name,
            status=pb.PLAYING,
            max_players=g.get("max_players", DEFAULT_PLAYERS_PER_GAME),
            on_state=on_state,
            on_error=on_error,
        )
        session.join(master, master_pub=master_pub)

        self.joining = {
            "game": g,
            "master": master,
            "master_pub": master_pub,
            "session": session,
            "state_received": state_received,
            "error_msg": error_msg,
            "t0": time.monotonic(),
        }

    def _poll_joining(self):
        j = self.joining
        if j is None:
            return None

        if j["state_received"]["state"] is not None:
            self.joining = None
            g = j["game"]
            return {
                "mode": "join",
                "game_name": g["name"],
                "player_name": self.player_name,
                "color": self.color,
                "master_addr": j["master"],
                "master_pub": j.get("master_pub", j["master"]),
                "status": pb.PLAYING,
                "max_players": g.get("max_players", DEFAULT_PLAYERS_PER_GAME),
                "state": j["state_received"]["state"],
                "session": j["session"],
            }

        if j["error_msg"]["text"] is not None:
            err_text = j["error_msg"]["text"]
            g = j["game"]
            self._cancel_joining()
            if err_text == "game full":
                return self._make_master(g["name"])
            self.status_line = f"Ошибка: {err_text}"
            return None

        elapsed = time.monotonic() - j["t0"]
        if elapsed >= JOIN_TIMEOUT_S:
            self._cancel_joining()
            self.status_line = "Таймаут подключения"
            return None

        dots = "." * (int(elapsed * 3) % 4)
        g = j["game"]
        self.status_line = f"Подключение к {g['name']}{dots}"
        return None

    def _index_at(self, pos):
        _, py = pos
        if not self.LIST_RECT.collidepoint(self.LIST_RECT.x + 1, py):
            return None
        i = (py - self.LIST_RECT.y - 4 + self.scroll) // self.ITEM_H
        if 0 <= i < len(self.games):
            return int(i)
        return None

    def _clamp_scroll(self):
        max_scroll = max(0, len(self.games) * self.ITEM_H - (self.LIST_RECT.height - 8))
        self.scroll = max(0, min(self.scroll, max_scroll))

    def _draw(self, mx, my):
        s = self.screen
        s.fill(COLOR_BG)

        title = self.fonts["title"].render("ОНЛАЙН-ИГРЫ", True, COLOR_TEXT)
        s.blit(title, (WIDTH // 2 - title.get_width() // 2, 70))

        name_line = self.fonts["ui"].render(
            f"Игрок: {self.player_name}",
            True, COLOR_TEXT,
        )
        s.blit(name_line, (60, 110))

        def draw_item(surf, rect, item, idx):
            if idx == self.selected_idx:
                pygame.draw.rect(surf, COLOR_BTN, rect, border_radius=6)
                text_color = (255, 255, 255)
            else:
                pygame.draw.rect(surf, (245, 245, 245), rect, border_radius=6)
                pygame.draw.rect(surf, (200, 200, 200), rect, width=1, border_radius=6)
                text_color = COLOR_TEXT
            name = self.fonts["ui"].render(item["name"], True, text_color)
            surf.blit(name, (rect.x + 12, rect.y + 6))
            info = f"Игроков: {item['players']}/{item['max_players']}"
            info_s = self.fonts["small"].render(info, True, text_color)
            surf.blit(info_s, (rect.x + 12, rect.y + 30))
            can = "открыта" if item["can_join"] else "заполнена"
            can_s = self.fonts["small"].render(can, True, text_color)
            surf.blit(can_s, (rect.right - 105, rect.y + 18))

        draw_vertical_scroll_list(
            s, self.LIST_RECT, self.games, self.ITEM_H,
            self.scroll, draw_item, self.fonts["ui"],
        )

        if not self.games:
            empty = self.fonts["ui"].render("Нет игр в сети", True, COLOR_PLACEHOLDER)
            s.blit(empty, (self.LIST_RECT.centerx - empty.get_width() // 2,
                           self.LIST_RECT.centery - empty.get_height() // 2))

        draw_rounded_button(s, self.btn_back, "Назад",
                            self.btn_back.collidepoint(mx, my), self.fonts["ui"])
        draw_rounded_button_colored(
            s, self.btn_create, "+ Создать игру",
            self.btn_create.collidepoint(mx, my), self.fonts["ui"],
            (60, 150, 80), (90, 190, 110),
        )
        join_label = "Подключение..." if self.joining is not None else "Присоединиться"
        draw_rounded_button_colored(
            s, self.btn_join, join_label,
            self.btn_join.collidepoint(mx, my) and self.joining is None, self.fonts["ui"],
            COLOR_BTN, COLOR_BTN_HOVER,
        )

        if self.status_line:
            st = self.fonts["small"].render(self.status_line, True, (120, 40, 40))
            s.blit(st, (60, HEIGHT - 30))

        if self.creating:
            self._draw_create_overlay(mx, my)

    def _draw_create_overlay(self, mx, my):
        s = self.screen
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        s.blit(overlay, (0, 0))

        panel = pygame.Rect(WIDTH // 2 - 260, 195, 520, 365)
        pygame.draw.rect(s, COLOR_PANEL, panel, border_radius=12)
        pygame.draw.rect(s, (0, 0, 0), panel, width=3, border_radius=12)

        t = self.fonts["title"].render("Создать игру", True, COLOR_TEXT)
        s.blit(t, (panel.centerx - t.get_width() // 2, panel.y + 20))

        label = self.fonts["ui"].render("Имя игры:", True, COLOR_TEXT)
        s.blit(label, (self.input_rect.x, self.input_rect.y - 26))

        draw_text_input(
            s, self.input_rect, self.game_name_input, self.input_active,
            self.fonts["ui"], cursor_visible=(pygame.time.get_ticks() // 400) % 2 == 0,
            placeholder="например, room1", placeholder_color=COLOR_PLACEHOLDER,
        )

        slider_lbl = self.fonts["ui"].render(
            f"Макс. игроков: {self.max_players_selected}", True, COLOR_TEXT
        )
        s.blit(slider_lbl, (self.slider_rect.x, self.slider_rect.y - 32))

        pygame.draw.rect(s, (210, 210, 210), self.slider_rect, border_radius=6)
        span = MAX_PLAYERS_PER_GAME - MIN_PLAYERS_PER_GAME
        ratio = (self.max_players_selected - MIN_PLAYERS_PER_GAME) / float(span)
        fill_w = int(self.slider_rect.width * ratio)
        if fill_w > 0:
            pygame.draw.rect(
                s, COLOR_BTN,
                pygame.Rect(self.slider_rect.x, self.slider_rect.y, fill_w, self.slider_rect.height),
                border_radius=6,
            )
        knob_x = self.slider_rect.x + fill_w
        knob_y = self.slider_rect.centery
        pygame.draw.circle(s, COLOR_BTN_HOVER, (knob_x, knob_y), 11)
        pygame.draw.circle(s, (40, 40, 40), (knob_x, knob_y), 11, width=2)

        min_s = self.fonts["small"].render(str(MIN_PLAYERS_PER_GAME), True, COLOR_TEXT)
        max_s = self.fonts["small"].render(str(MAX_PLAYERS_PER_GAME), True, COLOR_TEXT)
        s.blit(min_s, (self.slider_rect.x, self.slider_rect.bottom + 6))
        s.blit(max_s, (self.slider_rect.right - max_s.get_width(), self.slider_rect.bottom + 6))

        draw_rounded_button_colored(
            s, self.btn_confirm_create, "Создать",
            self.btn_confirm_create.collidepoint(mx, my), self.fonts["ui"],
            (60, 150, 80), (90, 190, 110),
        )
        draw_rounded_button_colored(
            s, self.btn_cancel_create, "Отмена",
            self.btn_cancel_create.collidepoint(mx, my), self.fonts["ui"],
            (160, 60, 60), (200, 90, 90),
        )