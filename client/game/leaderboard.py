import pygame

class Leaderboard:
    def __init__(self, screen, font):
        self.screen = screen
        self.font = font
        self.start_x = screen.get_width() - 240
        self.start_y = 20
        self.bar_width = 220
        self.bar_height = 24
        self.spacing = 35

    def draw(self, players):
        alive = [p for p in players if not p.is_dead]
        sorted_players = sorted(alive, key=lambda p: p.area_percentage, reverse=True)
        
        for i, p in enumerate(sorted_players):
            self._draw_row(p, self.start_y + i * self.spacing)

    def _draw_row(self, p, y):
        s = self.screen
        pygame.draw.rect(s, (200, 200, 200), (self.start_x, y, self.bar_width, self.bar_height), border_radius=4)

        fill_width = int(self.bar_width * (p.area_percentage / 100.0))
        if fill_width == 0 and p.area_percentage > 0:
            fill_width = 2
        if fill_width > 0:
            dark = (int(p.color[0] * 0.7), int(p.color[1] * 0.7), int(p.color[2] * 0.7))
            pygame.draw.rect(s, dark, (self.start_x, y + 4, fill_width, self.bar_height - 4), border_radius=4)
            pygame.draw.rect(s, p.color, (self.start_x, y, fill_width, self.bar_height - 4), border_radius=4)

        pygame.draw.rect(s, (40, 40, 40), (self.start_x, y, self.bar_width, self.bar_height), width=2, border_radius=4)

        text = self.font.render(f"{p.name}: {p.area_percentage:.2f}%", True, (0, 0, 0))
        s.blit(text, (self.start_x + 8, y + self.bar_height // 2 - text.get_height() // 2))