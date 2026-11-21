import pygame
import sys

from config import (
    WIDTH as width, HEIGHT as height,
    COLOR_PANEL, COLOR_TEXT
)
from ui.widgets import draw_rounded_button

class PauseMenu:
    def __init__(self, screen, clock, fonts):
        self.screen = screen
        self.clock = clock
        self.fonts = fonts

    def run(self, pause_type, current_game):
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        btn_resume = pygame.Rect(width // 2 - 120, height // 2 - 40, 240, 50)
        btn_action = pygame.Rect(width // 2 - 120, height // 2 + 30, 240, 50)
        action_text = "В МЕНЮ" if pause_type == "esc" else "ВЫЙТИ"

        while True:
            mx, my = pygame.mouse.get_pos()
            hover_resume = btn_resume.collidepoint(mx, my)
            hover_action = btn_action.collidepoint(mx, my)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    if pause_type == "esc":
                        pause_type, action_text = "cross", "ВЫЙТИ"
                    else:
                        pygame.quit()
                        sys.exit()
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and pause_type == "esc":
                    return "resume"
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if hover_resume:
                        return "resume"
                    if hover_action:
                        return "menu" if pause_type == "esc" else "exit"

            current_game.draw()
            self.screen.blit(overlay, (0, 0))
            self._draw_panel(pause_type, action_text, hover_resume, hover_action, btn_resume, btn_action)
            pygame.display.flip()
            self.clock.tick(60)

    def _draw_panel(self, pause_type, action_text, hover_resume, hover_action, btn_resume, btn_action):
        s = self.screen
        panel_rect = pygame.Rect(width // 2 - 160, height // 2 - 130, 320, 250)
        pygame.draw.rect(s, COLOR_PANEL, panel_rect, border_radius=12)
        pygame.draw.rect(s, (0, 0, 0), panel_rect, width=3, border_radius=12)

        title = self.fonts["title"].render("ПАУЗА" if pause_type == "esc" else "ВЫХОД?", True, COLOR_TEXT)
        s.blit(title, (width // 2 - title.get_width() // 2, panel_rect.y + 20))

        draw_rounded_button(s, btn_resume, "ПРОДОЛЖИТЬ", hover_resume, self.fonts["ui"])
        draw_rounded_button(s, btn_action, action_text, hover_action, self.fonts["ui"])