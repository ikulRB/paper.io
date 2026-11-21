import math
import pygame
import sys

from config import (
    WIDTH as width, HEIGHT as height,
    COLOR_PANEL, COLOR_TEXT
)
from game.game import Game
from game.controllers import HumanController
from ui.widgets import draw_rounded_button


class PlayState:
    DEATH_RED_DELAY = 900
    DEATH_PANEL_DELAY = 1000
    DEATH_OK_DELAY = 1500
    NUM_BOTS = 20

    WIN_COLOR = (40, 160, 60)
    LOSE_COLOR = (200, 30, 30)

    def __init__(self, screen, clock, fonts, pause_menu):
        self.screen = screen
        self.clock = clock
        self.fonts = fonts
        self.pause_menu = pause_menu

        self.panel_w, self.panel_h = 440, 420
        self.panel_x = width // 2 - self.panel_w // 2
        self.ok_btn = pygame.Rect(width // 2 - 60, 0, 120, 40)

    def run(self, name, color):
        game = Game(self.screen, name, color, num_bots=self.NUM_BOTS)
        game.main_player.controller = HumanController(pygame)
        is_alive = True
        death_anim_time = 0

        while True:
            mx, my = pygame.mouse.get_pos()
            pause_trigger = None

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pause_trigger = "cross"
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    pause_trigger = "esc"
                if (not is_alive and event.type == pygame.MOUSEBUTTONDOWN
                        and death_anim_time > self.DEATH_OK_DELAY):
                    if self.ok_btn.collidepoint(event.pos):
                        return

            if pause_trigger and is_alive:
                result = self.pause_menu.run(pause_trigger, game)
                if result == "menu":
                    return
                if result == "exit":
                    pygame.quit()
                    sys.exit()

            new_is_alive = game.update()
            if new_is_alive is not None:
                is_alive = new_is_alive

            game.draw()

            if not is_alive:
                death_anim_time += 16.67
                self._draw_end_overlay(game, death_anim_time, mx, my)

            pygame.display.flip()
            self.clock.tick(60)

    def _draw_end_overlay(self, game, death_anim_time, mx, my):
        win = (game.result == "win")
        overlay_color = (30, 120, 40) if win else (160, 20, 20)
        
        if death_anim_time > self.DEATH_RED_DELAY:
            alpha = min(110, int((death_anim_time - self.DEATH_RED_DELAY) * 0.18))
            surf = pygame.Surface((width, height), pygame.SRCALPHA)
            surf.fill((*overlay_color, alpha))
            self.screen.blit(surf, (0, 0))

        if death_anim_time >= self.DEATH_PANEL_DELAY:
            panel_y = self._compute_panel_y(death_anim_time)
            self._draw_panel(game, panel_y, win)
            if death_anim_time > self.DEATH_OK_DELAY:
                self._draw_ok_button(panel_y, mx, my)

    def _compute_panel_y(self, death_anim_time):
        progress = min(1.0, (death_anim_time - self.DEATH_PANEL_DELAY) / 500.0)
        elastic_offset = math.sin(progress * math.pi) * 30 * (1.0 - progress)
        return int(-self.panel_h + (height // 2 - self.panel_h // 2 + self.panel_h) * progress - elastic_offset)

    def _draw_panel(self, game, panel_y, win):
        s = self.screen
        pygame.draw.rect(s, COLOR_PANEL, (self.panel_x, panel_y, self.panel_w, self.panel_h), border_radius=14)
        pygame.draw.rect(s, (0, 0, 0), (self.panel_x, panel_y, self.panel_w, self.panel_h), width=3, border_radius=14)

        title_text = "ПОБЕДА!" if win else "ПОРАЖЕНИЕ"
        title_color = self.WIN_COLOR if win else self.LOSE_COLOR
        go = game.font_gameover.render(title_text, True, title_color)
        s.blit(go, (width // 2 - go.get_width() // 2, panel_y + 20))

        score = game.font_name.render(
            f"Ваша доля: {game.main_player.area_percentage:.2f} %", True, COLOR_TEXT
        )
        s.blit(score, (width // 2 - score.get_width() // 2, panel_y + 75))

        self._draw_end_minimap(game, panel_y)

    def _draw_end_minimap(self, game, panel_y):
        s = self.screen
        radius = 110
        m_cx, m_cy = width // 2, panel_y + 220
        scale = radius / game.MAP_RADIUS

        pygame.draw.circle(s, (230, 230, 230), (m_cx, m_cy), radius)

        for p in game.players:
            if p.is_dead or len(p.territory_points) <= 2:
                continue
            mini = [(int(x * scale + m_cx), int(y * scale + m_cy)) for x, y in p.territory_points]
            pygame.draw.polygon(s, p.territory_color, mini)

        if game.main_player.is_dead and len(game.final_territory_points) > 2:
            mini = [(int(x * scale + m_cx), int(y * scale + m_cy)) for x, y in game.final_territory_points]
            pygame.draw.polygon(s, game.final_territory_color, mini)

        pygame.draw.circle(s, (40, 40, 40), (m_cx, m_cy), radius, 2)

    def _draw_ok_button(self, panel_y, mx, my):
        self.ok_btn.y = panel_y + 355
        hover = self.ok_btn.collidepoint(mx, my)
        draw_rounded_button(self.screen, self.ok_btn, "OK", hover, self.fonts["ui"])