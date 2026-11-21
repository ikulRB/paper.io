import pygame

WIDTH, HEIGHT = 800, 800
CAPTION = "Paper.io Network"

COLOR_BG = (240, 240, 240)
COLOR_PANEL = (255, 255, 255)
COLOR_TEXT = (40, 40, 40)
COLOR_BTN = (70, 130, 180)
COLOR_BTN_HOVER = (100, 149, 237)
COLOR_PLACEHOLDER = (160, 160, 160)
COLOR_LINE = (80, 80, 80)

COLOR_BTN_DANGER = (180, 60, 60)
COLOR_BTN_DANGER_HOVER = (210, 90, 90)
COLOR_BTN_OK = (60, 150, 80)
COLOR_BTN_OK_HOVER = (90, 190, 110)

AVAILABLE_COLORS = [
    (50, 220, 50), (220, 50, 50), (50, 50, 220), (220, 180, 50), (180, 50, 220),
    (255, 140, 0), (0, 206, 209), (255, 105, 180), (128, 128, 128), (124, 252, 0),
]

MAX_NAME_LEN = 12
FPS = 60

# --- сеть ---
CATALOG_ADDR = ("159.200.243.235", 9193)
MULTICAST_GROUP = ("239.192.0.4", 9193)
MIN_PLAYERS_PER_GAME = 3
MAX_PLAYERS_PER_GAME = 10
DEFAULT_PLAYERS_PER_GAME = 4
DEFAULT_STATE_DELAY_MS = 100
DEFAULT_MAP_RADIUS = 2000.0
JOIN_TIMEOUT_S = 5.0
ANNOUNCE_TTL_MS = 3000


def init_fonts():
    return {
        "title": pygame.font.SysFont("Arial", 36, bold=True),
        "ui": pygame.font.SysFont("Arial", 20, bold=True),
        "small": pygame.font.SysFont("Arial", 15),
        "vs": pygame.font.SysFont("Arial", 24, bold=True, italic=True),
    }
