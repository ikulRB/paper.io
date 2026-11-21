import math
import pygame
from config import COLOR_BTN, COLOR_BTN_HOVER


def draw_icon_bots(surface, rect):
    ic_cx = rect.x + 28
    ic_cy = rect.y + rect.height // 2
    for offset in (-6, 0, 6):
        pygame.draw.line(surface, (230, 190, 50),
                         (ic_cx + offset, ic_cy - 12),
                         (ic_cx + offset, ic_cy + 12), 2)
        pygame.draw.line(surface, (230, 190, 50),
                         (ic_cx - 12, ic_cy + offset),
                         (ic_cx + 12, ic_cy + offset), 2)
    pygame.draw.rect(surface, (50, 50, 50),
                     (ic_cx - 8, ic_cy - 8, 16, 16), border_radius=2)
    pygame.draw.rect(surface, (255, 255, 255),
                     (ic_cx - 8, ic_cy - 8, 16, 16), width=1, border_radius=2)
    pygame.draw.circle(surface, (100, 255, 100), (ic_cx, ic_cy), 2)


def draw_icon_net(surface, rect):
    ic_cx = rect.x + 28
    ic_cy = rect.y + rect.height // 2
    pygame.draw.rect(surface, (255, 255, 255), (ic_cx - 4, ic_cy - 12, 8, 8))
    pygame.draw.rect(surface, (255, 255, 255), (ic_cx - 12, ic_cy + 4, 8, 8))
    pygame.draw.rect(surface, (255, 255, 255), (ic_cx + 4, ic_cy + 4, 8, 8))
    pygame.draw.line(surface, (255, 255, 255),
                     (ic_cx, ic_cy - 4), (ic_cx, ic_cy), 2)
    pygame.draw.line(surface, (255, 255, 255),
                     (ic_cx - 8, ic_cy), (ic_cx + 8, ic_cy), 2)
    pygame.draw.line(surface, (255, 255, 255),
                     (ic_cx - 8, ic_cy), (ic_cx - 8, ic_cy + 4), 2)
    pygame.draw.line(surface, (255, 255, 255),
                     (ic_cx + 8, ic_cy), (ic_cx + 8, ic_cy + 4), 2)


def draw_game_button(surface, text, rect, is_hovered, btn_type, font):
    color = COLOR_BTN_HOVER if is_hovered else COLOR_BTN
    pygame.draw.rect(surface, color, rect, border_radius=8)
    pygame.draw.rect(surface, (0, 0, 0), rect, width=2, border_radius=8)

    if btn_type == "bots":
        draw_icon_bots(surface, rect)
    else:
        draw_icon_net(surface, rect)

    txt_surf = font.render(text, True, (255, 255, 255))
    txt_x = rect.x + (rect.width // 2) - (txt_surf.get_width() // 2) + 12
    txt_y = rect.y + (rect.height // 2) - (txt_surf.get_height() // 2)
    surface.blit(txt_surf, (txt_x, txt_y))


def draw_rounded_button(surface, rect, text, is_hovered, font,
                        text_color=(255, 255, 255)):
    color = COLOR_BTN_HOVER if is_hovered else COLOR_BTN
    pygame.draw.rect(surface, color, rect, border_radius=8)
    pygame.draw.rect(surface, (0, 0, 0), rect, width=2, border_radius=8)
    t_surf = font.render(text, True, text_color)
    surface.blit(t_surf, (
        rect.x + rect.width // 2 - t_surf.get_width() // 2,
        rect.y + rect.height // 2 - t_surf.get_height() // 2,
    ))


def draw_text_input(surface, rect, text, is_active, font, cursor_visible,
                    placeholder="", placeholder_color=(160, 160, 160),
                    text_color=(40, 40, 40), border_active_color=COLOR_BTN,
                    error_alpha=0):
    from config import COLOR_PLACEHOLDER  # noqa: F401 (сохранено как было)

    bg = (255, 255, 255) if is_active else (230, 230, 230)
    pygame.draw.rect(surface, bg, rect, border_radius=5)

    if error_alpha > 0:
        err = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        err.fill((255, 100, 100, error_alpha))
        surface.blit(err, (rect.x, rect.y))

    border = border_active_color if is_active else (150, 150, 150)
    pygame.draw.rect(surface, border, rect, width=2, border_radius=5)

    mid_y = rect.y + rect.height // 2
    if text == "":
        surf = font.render(placeholder, True, placeholder_color)
        surface.blit(surf, (rect.x + 10, mid_y - surf.get_height() // 2))
        text_width = 0
    else:
        surf = font.render(text, True, text_color)
        surface.blit(surf, (rect.x + 10, mid_y - surf.get_height() // 2))
        text_width = surf.get_width()

    if is_active and cursor_visible:
        cx = rect.x + 12 + text_width
        pygame.draw.line(surface, text_color, (cx, mid_y - 12), (cx, mid_y + 12), 2)


class ColorPicker:
    """Палитра выбора цвета."""

    def __init__(self, center_x, top_y, colors, radius=18, step_x=50,
                 step_y=45, cols=5):
        self.center_x = center_x
        self.top_y = top_y
        self.colors = colors
        self.radius = radius
        self.step_x = step_x
        self.step_y = step_y
        self.cols = cols
        self.selected_idx = 0

    def get_center(self, i):
        cx = self.center_x - 100 + (i % self.cols) * self.step_x
        cy = self.top_y + (i // self.cols) * self.step_y
        return cx, cy

    def hit_test(self, mx, my):
        for i in range(len(self.colors)):
            cx, cy = self.get_center(i)
            if math.hypot(mx - cx, my - cy) < self.radius:
                return i
        return None

    def draw(self, surface):
        for i, color in enumerate(self.colors):
            cx, cy = self.get_center(i)
            pygame.draw.circle(surface, color, (cx, cy), self.radius)
            if i == self.selected_idx:
                pygame.draw.circle(surface, (0, 0, 0), (cx, cy),
                                   self.radius + 3, width=3)


def draw_rounded_button_colored(surface, rect, text, is_hovered, font,
                                base_color, hover_color, text_color=(255, 255, 255)):
    color = hover_color if is_hovered else base_color
    pygame.draw.rect(surface, color, rect, border_radius=8)
    pygame.draw.rect(surface, (0, 0, 0), rect, width=2, border_radius=8)
    t = font.render(text, True, text_color)
    surface.blit(t, (
        rect.x + rect.width // 2 - t.get_width() // 2,
        rect.y + rect.height // 2 - t.get_height() // 2,
    ))


def draw_vertical_scroll_list(surface, rect, items, item_height,
                              scroll_offset, draw_item, font,
                              bg_color=(250, 250, 250),
                              border_color=(0, 0, 0)):
    pygame.draw.rect(surface, bg_color, rect, border_radius=6)
    pygame.draw.rect(surface, border_color, rect, width=2, border_radius=6)

    clip = surface.get_clip()
    surface.set_clip(rect.inflate(-4, -4))
    for i, item in enumerate(items):
        y = rect.y + 4 + i * item_height - scroll_offset
        item_rect = pygame.Rect(rect.x + 4, y, rect.width - 8, item_height - 4)
        if item_rect.bottom < rect.y or item_rect.top > rect.bottom:
            continue
        draw_item(surface, item_rect, item, i)
    surface.set_clip(clip)


def wrap_text(font, text, max_width):
    words = text.split()
    lines, line = [], ""
    for w in words:
        test = (line + " " + w).strip()
        if font.size(test)[0] <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines