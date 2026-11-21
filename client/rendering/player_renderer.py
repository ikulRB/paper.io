import math
import pygame

HEAD_VERTICES = [(18, 0), (-12, -12), (-6, 0), (-12, 12)]

class PlayerRenderer:
    def __init__(self, screen, font, volume_shift=6):
        self.screen = screen
        self.font = font
        self.volume_shift = volume_shift
        self.center_x = screen.get_width() // 2
        self.center_y = screen.get_height() // 2

    def draw_players(self, camera, players, main_player):
        now = pygame.time.get_ticks()
        for p in players:
            if p.is_dead:
                continue
            self._draw_ship(camera, p, is_leader=(p is main_player), now=now)
            self._draw_name(camera, p, main_player)

    def _draw_ship(self, camera, p, is_leader, now):
        head = p.get_head()
        scr_x, scr_y = head[0] + camera.offset_x, head[1] + camera.offset_y
        base = []
        for vx, vy in HEAD_VERTICES:
            rx = vx * math.cos(p.angle) - vy * math.sin(p.angle)
            ry = vx * math.sin(p.angle) + vy * math.cos(p.angle)
            base.append((scr_x + rx, scr_y + ry))

        if is_leader:
            pulse = (math.sin(now * 0.005) + 1) / 2.0
            
            light_color = (
                int(p.color[0] + (255 - p.color[0]) * pulse * 0.4),
                int(p.color[1] + (255 - p.color[1]) * pulse * 0.4),
                int(p.color[2] + (255 - p.color[2]) * pulse * 0.4)
            )
            dark_color = (
                int(p.color[0] * (0.6 + 0.4 * pulse)),
                int(p.color[1] * (0.6 + 0.4 * pulse)),
                int(p.color[2] * (0.6 + 0.4 * pulse))
            )
            
            volume = [(x, y + self.volume_shift - 2) for x, y in base]
            pygame.draw.polygon(self.screen, dark_color, volume)
            
            pygame.draw.polygon(self.screen, light_color, base)
            pygame.draw.polygon(self.screen, (0, 0, 0), base, 2)
        else:
            volume = [(x, y + self.volume_shift - 2) for x, y in base]
            pygame.draw.polygon(self.screen, (30, 30, 30), volume)
            pygame.draw.polygon(self.screen, p.color, base)
            pygame.draw.polygon(self.screen, (0, 0, 0), base, 2)

    def _draw_name(self, camera, p, main_player):
        head = p.get_head()
        scr_x, scr_y = head[0] + camera.offset_x, head[1] + camera.offset_y
        surf = self.font.render(p.name, True, (0, 0, 0))
        if p is main_player:
            pos = (self.center_x - surf.get_width() // 2, self.center_y - 45)
        else:
            pos = (int(scr_x) - surf.get_width() // 2, int(scr_y) - 45)
        self.screen.blit(surf, pos)