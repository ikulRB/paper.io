import pygame
import sys

from config import (
    WIDTH as width, HEIGHT as height,
    COLOR_PANEL, COLOR_TEXT
)
from game.game import Game
from game.controllers import HumanController
from ui.widgets import draw_rounded_button
from ui.end_screen import EndScreen


class PlayState:
    NUM_BOTS = 20

    def __init__(self, screen, clock, fonts, pause_menu):
        self.screen = screen
        self.clock = clock
        self.fonts = fonts
        self.pause_menu = pause_menu
        self.end_screen = EndScreen(screen, fonts)

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
                        and event.button == 1
                        and self.end_screen.ok_clicked(event.pos, death_anim_time)):
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
                self.end_screen.draw(game, death_anim_time, mx, my)

            pygame.display.flip()
            self.clock.tick(60)