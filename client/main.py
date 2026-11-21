import pygame

from config import (
    WIDTH, HEIGHT, CAPTION,
    AVAILABLE_COLORS, init_fonts,
)
from ui.menu import Menu
from ui.pause import PauseMenu
from states.play_state import PlayState
from states.lobby_state import LobbyState
from states.network_play_state import NetworkPlayState


def main():
    pygame.init()
    pygame.font.init()

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption(CAPTION)
    clock = pygame.time.Clock()
    pygame.key.set_repeat(400, 40)

    fonts = init_fonts()
    menu = Menu(screen, clock, fonts)
    pause_menu = PauseMenu(screen, clock, fonts)
    play_state = PlayState(screen, clock, fonts, pause_menu)

    saved_name = "Player"
    saved_color = AVAILABLE_COLORS[0]

    while True:
        result = menu.run(saved_name, saved_color)
        if result is None:
            break
        kind, payload = result
        saved_name = payload.get("name", saved_name)
        saved_color = payload.get("color", saved_color)

        if kind == "local":
            play_state.run(payload["name"], payload["color"])
        elif kind == "online":
            lobby = LobbyState(screen, clock, fonts, payload["name"], payload["color"])
            info = lobby.run()
            if info and "mode" in info:
                NetworkPlayState(screen, clock, fonts).run(info)
            # иначе — просто вернулись в меню


if __name__ == "__main__":
    main()