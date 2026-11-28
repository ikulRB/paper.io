import math
import pygame

from config import WIDTH, HEIGHT, COLOR_PANEL, COLOR_TEXT
from ui.widgets import draw_rounded_button


class EndScreen:
    """Общая отрисовка экрана победы/поражения для локальной и онлайн-игры."""

    DEATH_RED_DELAY = 900
    DEATH_PANEL_DELAY = 1000
    DEATH_OK_DELAY = 1500

    WIN_COLOR = (40, 160, 60)
    LOSE_COLOR = (200, 30, 30)

    def __init__(self, screen, fonts):
        self.screen = screen
        self.fonts = fonts
        self.panel_w, self.panel_h = 440, 420
        self.panel_x = WIDTH // 2 - self.panel_w // 2
        self.ok_btn = pygame.Rect(WIDTH // 2 - 60, 0, 120, 40)

    def draw(self, game, anim_time, mx, my):
        """anim_time — мс с момента окончания игры."""
        win = (game.result == "win")
        overlay_color = (30, 120, 40) if win else (160, 20, 20)

        if anim_time > self.DEATH_RED_DELAY:
            alpha = min(110, int((anim_time - self.DEATH_RED_DELAY) * 0.18))
            surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            surf.fill((*overlay_color, alpha))
            self.screen.blit(surf, (0, 0))

        if anim_time >= self.DEATH_PANEL_DELAY:
            panel_y = self._compute_panel_y(anim_time)
            self._draw_panel(game, panel_y, win)
            if anim_time > self.DEATH_OK_DELAY:
                self._draw_ok_button(panel_y, mx, my)

    def ok_clicked(self, pos, anim_time):
        return anim_time > self.DEATH_OK_DELAY and self.ok_btn.collidepoint(pos)

    def _compute_panel_y(self, anim_time):
        progress = min(1.0, (anim_time - self.DEATH_PANEL_DELAY) / 500.0)
        elastic_offset = math.sin(progress * math.pi) * 30 * (1.0 - progress)
        return int(-self.panel_h + (HEIGHT // 2 - self.panel_h // 2 + self.panel_h) * progress - elastic_offset)

    def _draw_panel(self, game, panel_y, win):
        s = self.screen
        pygame.draw.rect(s, COLOR_PANEL, (self.panel_x, panel_y, self.panel_w, self.panel_h), border_radius=14)
        pygame.draw.rect(s, (0, 0, 0), (self.panel_x, panel_y, self.panel_w, self.panel_h), width=3, border_radius=14)

        title_text = "ПОБЕДА!" if win else "ПОРАЖЕНИЕ"
        title_color = self.WIN_COLOR if win else self.LOSE_COLOR
        go = game.font_gameover.render(title_text, True, title_color)
        s.blit(go, (WIDTH // 2 - go.get_width() // 2, panel_y + 20))

        score = game.font_name.render(
            f"Ваша доля: {game.main_player.area_percentage:.2f} %", True, COLOR_TEXT
        )
        s.blit(score, (WIDTH // 2 - score.get_width() // 2, panel_y + 75))

        self._draw_end_minimap(game, panel_y)

    def _draw_end_minimap(self, game, panel_y):
        s = self.screen
        radius = 110
        m_cx, m_cy = WIDTH // 2, panel_y + 220
        scale = radius / game.MAP_RADIUS

        pygame.draw.circle(s, (230, 230, 230), (m_cx, m_cy), radius)

        for p in game.players:
            if p.is_dead or len(p.territory_points) <= 2:
                continue
            mini = [(int(x * scale + m_cx), int(y * scale + m_cy)) for x, y in p.territory_points]
            pygame.draw.polygon(s, p.territory_color, mini)

        # Финальная территория main_player:
        # при смерти — из final_*, при победе — текущая (иначе миникарта пустая)
        if game.main_player.is_dead and len(game.final_territory_points) > 2:
            mini = [(int(x * scale + m_cx), int(y * scale + m_cy)) for x, y in game.final_territory_points]
            pygame.draw.polygon(s, game.final_territory_color, mini)
        elif not game.main_player.is_dead and len(game.main_player.territory_points) > 2:
            mini = [(int(x * scale + m_cx), int(y * scale + m_cy))
                    for x, y in game.main_player.territory_points]
            pygame.draw.polygon(s, game.main_player.territory_color, mini)

        pygame.draw.circle(s, (40, 40, 40), (m_cx, m_cy), radius, 2)

    def _draw_ok_button(self, panel_y, mx, my):
        self.ok_btn.y = panel_y + 355
        hover = self.ok_btn.collidepoint(mx, my)
        draw_rounded_button(self.screen, self.ok_btn, "OK", hover, self.fonts["ui"])