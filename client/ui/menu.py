import math
import pygame
import sys

from config import (
    WIDTH as width, HEIGHT as height,
    COLOR_BG, COLOR_TEXT, COLOR_LINE, COLOR_PLACEHOLDER,
    AVAILABLE_COLORS, MAX_NAME_LEN,
)
from ui.widgets import draw_game_button, draw_text_input, ColorPicker


class Menu:
    def __init__(self, screen, clock, fonts):
        self.screen = screen
        self.clock = clock
        self.fonts = fonts

        self.input_base_x = width // 2 - 175
        self.input_rect = pygame.Rect(self.input_base_x, height // 2 - 130, 350, 40)
        self.bots_btn = pygame.Rect(width // 2 - 175, height // 2 - 22, 165, 45)
        self.net_btn = pygame.Rect(width // 2 + 10, height // 2 - 22, 165, 45)
        self.color_picker = ColorPicker(width // 2, height // 2 + 125, AVAILABLE_COLORS)

        self.shake_duration = 400
        self.error_start_time = -self.shake_duration 

    def _compute_shake(self, now):
        elapsed = now - self.error_start_time
        if elapsed < self.shake_duration:
            offset = int(math.sin(elapsed * 0.08) * 10)
            alpha = int(100 * (1.0 - (elapsed / self.shake_duration)))
            return offset, alpha
        return 0, 0

    def _trigger_error(self):
        self.error_start_time = pygame.time.get_ticks()

    def run(self, current_name="", current_color=None):
        player_name = current_name
        self.color_picker.selected_idx = (
            AVAILABLE_COLORS.index(current_color) if current_color in AVAILABLE_COLORS else 0
        )
        input_active = False

        while True:
            now = pygame.time.get_ticks()
            mx, my = pygame.mouse.get_pos()
            hover_bots = self.bots_btn.collidepoint(mx, my)
            hover_net = self.net_btn.collidepoint(mx, my)
            shake_offset, error_alpha = self._compute_shake(now)
            self.input_rect.x = self.input_base_x + shake_offset

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    input_active = self.input_rect.collidepoint(event.pos)
                    idx = self.color_picker.hit_test(event.pos[0], event.pos[1])
                    if idx is not None:
                        self.color_picker.selected_idx = idx
                    if hover_bots:
                        if player_name.strip() == "":
                            self._trigger_error()
                        else:
                            return ("local", {
                                "name": player_name.strip(),
                                "color": AVAILABLE_COLORS[self.color_picker.selected_idx],
                            })
                    if hover_net:
                        if player_name.strip() == "":
                            self._trigger_error()
                        else:
                            return ("online", {
                                "name": player_name.strip(),
                                "color": AVAILABLE_COLORS[self.color_picker.selected_idx],
                            })
                if event.type == pygame.KEYDOWN and input_active:
                    result = self._handle_key(event, player_name)
                    if result is not None:
                        if isinstance(result, tuple) and result[0] == "__submit__":
                            if player_name.strip() == "":
                                self._trigger_error()
                            else:
                                # Enter = локальная игра по умолчанию
                                return ("local", {
                                    "name": player_name.strip(),
                                    "color": AVAILABLE_COLORS[self.color_picker.selected_idx],
                                })
                        else:
                            player_name = result

            self._draw(player_name, input_active, hover_bots, hover_net, error_alpha, now)
            pygame.display.flip()
            self.clock.tick(60)

    def _handle_key(self, event, player_name):
        if event.key == pygame.K_RETURN:
            return ("__submit__",)
        if event.key == pygame.K_BACKSPACE:
            return player_name[:-1]
        if len(player_name) < MAX_NAME_LEN and (event.unicode.isprintable() or event.key == pygame.K_SPACE):
            return player_name + event.unicode
        return None

    def _draw(self, player_name, input_active, hover_bots, hover_net, error_alpha, now):
        s = self.screen
        s.fill(COLOR_BG)

        title_surf = self.fonts["title"].render("PAPER.IO 3D", True, COLOR_TEXT)
        s.blit(title_surf, (width // 2 - title_surf.get_width() // 2, height // 2 - 200))

        cursor_visible = (now // 400) % 2 == 0
        draw_text_input(
            s, self.input_rect, player_name, input_active, self.fonts["ui"],
            cursor_visible=cursor_visible, placeholder="Введите ник",
            placeholder_color=COLOR_PLACEHOLDER, text_color=COLOR_TEXT,
            error_alpha=error_alpha,
        )

        self._draw_vs_and_lines()
        draw_game_button(s, "AI БОТЫ", self.bots_btn, hover_bots, "bots", self.fonts["ui"])
        draw_game_button(s, "ONLINE", self.net_btn, hover_net, "net", self.fonts["ui"])

        color_label = self.fonts["ui"].render("Выберите цвет:", True, COLOR_TEXT)
        s.blit(color_label, (width // 2 - color_label.get_width() // 2, height // 2 + 75))
        self.color_picker.draw(s)

    def _draw_vs_and_lines(self):
        s = self.screen
        vs_surf = self.fonts["vs"].render("vs", True, COLOR_TEXT)
        vs_x = width // 2 - vs_surf.get_width() // 2
        vs_y = height // 2 - 58
        s.blit(vs_surf, (vs_x, vs_y))
        pygame.draw.line(s, COLOR_LINE, (vs_x - 5, vs_y + 13), (width // 2 - 92, vs_y + 13), 2)
        pygame.draw.line(s, COLOR_LINE, (width // 2 - 92, vs_y + 13), (width // 2 - 92, self.bots_btn.y), 2)
        pygame.draw.line(s, COLOR_LINE, (vs_x + vs_surf.get_width() + 5, vs_y + 13), (width // 2 + 92, vs_y + 13), 2)
        pygame.draw.line(s, COLOR_LINE, (width // 2 + 92, vs_y + 13), (width // 2 + 92, self.net_btn.y), 2)