import random
import math
import pygame

class ParticlePool:
    def __init__(self, color, screen):
        self.color = color
        self.screen = screen
        self.items = []

    def spawn(self, source_points, per_point=2):
        for pt in source_points:
            for _ in range(per_point):
                angle = random.uniform(0, math.pi * 2)
                speed = random.uniform(0.8, 4.0)
                self.items.append({
                    "x": pt[0], "y": pt[1],
                    "vx": math.cos(angle) * speed,
                    "vy": math.sin(angle) * speed,
                    "radius": random.randint(2, 6),
                    "alpha": 255,
                })

    def update(self):
        for p in self.items:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["alpha"] = max(0, p["alpha"] - 2)
        self.items = [p for p in self.items if p["alpha"] > 0]

    def draw(self, camera):
        for p in self.items:
            surf = pygame.Surface((p["radius"] * 2, p["radius"] * 2), pygame.SRCALPHA)
            pygame.draw.circle(
                surf,
                (self.color[0], self.color[1], self.color[2], p["alpha"]),
                (p["radius"], p["radius"]),
                p["radius"],
            )
            sx = int(p["x"] + camera.offset_x - p["radius"])
            sy = int(p["y"] + camera.offset_y - p["radius"])
            self.screen.blit(surf, (sx, sy))


class ParticleManager:
    def __init__(self, screen):
        self.screen = screen
        self._pools = {}

    def for_player(self, player):
        key = id(player)
        if key not in self._pools:
            self._pools[key] = ParticlePool(player.color, self.screen)
        return self._pools[key]

    def spawn_for(self, player, source_points, per_point=2):
        self.for_player(player).spawn(source_points, per_point)

    def update(self):
        for pool in self._pools.values():
            pool.update()

    def draw(self, camera):
        for pool in self._pools.values():
            pool.draw(camera)