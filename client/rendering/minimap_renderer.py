import math
import pygame

class MinimapRenderer:
    def __init__(self, screen, mini_radius=80, map_radius=2000, margin=20):
        self.screen = screen
        self.mini_radius = mini_radius
        self.map_radius = map_radius
        self.scale = mini_radius / map_radius
        self.cx = margin + mini_radius
        self.cy = margin + mini_radius

    def draw(self, players):
        s = self.screen
        pygame.draw.circle(s, (240, 240, 240), (self.cx, self.cy), self.mini_radius)
        for p in players:
            if p.is_dead:
                continue
            self._draw_territory(p)
            self._draw_trail(p)
            self._draw_head(p)
        pygame.draw.circle(s, (0, 0, 0), (self.cx, self.cy), self.mini_radius, 2)

    def _to_mini(self, pt):
        return int(pt[0] * self.scale + self.cx), int(pt[1] * self.scale + self.cy)

    def _draw_territory(self, p):
        if len(p.territory_points) <= 2:
            return
        mini = [self._to_mini(pt) for pt in p.territory_points]
        pygame.draw.polygon(self.screen, p.territory_color, mini)

    def _draw_trail(self, p):
        if p.in_base or len(p.points) <= 1:
            return
        mini = [self._to_mini(pt) for pt in p.points]
        pygame.draw.lines(self.screen, p.trail_color, False, mini, 2)

    def _draw_head(self, p):
        hx, hy = self._to_mini(p.get_head())
        local = [(6, 0), (-4, -4), (-2, 0), (-4, 4)]
        rotated = []
        for vx, vy in local:
            rx = vx * math.cos(p.angle) - vy * math.sin(p.angle)
            ry = vx * math.sin(p.angle) + vy * math.cos(p.angle)
            rotated.append((hx + rx, hy + ry))
        pygame.draw.polygon(self.screen, p.color, rotated)
        pygame.draw.polygon(self.screen, (0, 0, 0), rotated, 1)