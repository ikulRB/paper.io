import math
import random

from abc import ABC, abstractmethod


class Controller(ABC):
    @abstractmethod
    def get_steer(self, player, game) -> int: #return -1 (left) / 1 (right) / 0
        ...


class HumanController(Controller):
    def __init__(self, pygame_module):
        self.pygame = pygame_module

    def get_steer(self, player, game):
        keys = self.pygame.key.get_pressed()
        steer = 0
        if keys[self.pygame.K_LEFT]:
            steer -= 1
        if keys[self.pygame.K_RIGHT]:
            steer += 1
        return steer


class ScriptedController(Controller):
    def __init__(self, steer_provider=None):
        self._provider = steer_provider
        self._steer = 0

    def set_steer(self, value: int):
        self._steer = max(-1, min(1, int(value)))

    def get_steer(self, player, game):
        if self._provider is not None:
            return max(-1, min(1, int(self._provider(player, game))))
        return self._steer


class BotController(Controller):
    TRAIL_TARGET_RADIUS = 360
    RETURN_AREA_PERCENT = 8.0
    BOUNDARY_AVOID_DIST = 0
    SELF_TRAIL_AVOID_DIST = 40
    WANDER_CHANCE = 0.02

    def __init__(self, rng=None):
        self.rng = rng or random.Random()
        self._wander = 0

    def get_steer(self, player, game):
        head = player.get_head()

        steer = self._steer_avoid_boundary(player, game, head)
        if steer != 0:
            return steer

        if not player.in_base:
            return self._steer_outside_base(player, game, head)

        return self._steer_inside_base(player, game, head)

    def _steer_avoid_boundary(self, player, game, head):
        dist = math.hypot(head[0], head[1])
        if dist < game.MAP_RADIUS - self.BOUNDARY_AVOID_DIST:
            return 0
        to_center = math.atan2(-head[1], -head[0])
        diff = (to_center - player.angle + math.pi) % (2 * math.pi) - math.pi
        return 1 if diff > 0 else -1

    def _steer_outside_base(self, player, game, head):
        attack = self._steer_attack_trail(player, game, head)
        if attack is not None:
            return attack

        target = self._nearest_point_on_base(player, head)
        if target is None:
            return self._wander_step()
        return self._steer_towards(player, target)

    def _steer_inside_base(self, player, game, head):
        if player.area_percentage < self.RETURN_AREA_PERCENT:
            return self._wander_step()

        outward = self._nearest_point_outside_base(player, head)
        if outward is None:
            return self._wander_step()
        return self._steer_towards(player, outward)

    def _steer_attack_trail(self, player, game, head):
        best_point, best_d = None, self.TRAIL_TARGET_RADIUS
        for other in game.players:
            if other is player or other.is_dead or other.in_base or len(other.points) < 4:
                continue

            mid = other.points[len(other.points) // 2]
            d = math.hypot(mid[0] - head[0], mid[1] - head[1])
            if d < best_d:
                best_d, best_point = d, mid
        if best_point is None:
            return None
        return self._steer_towards(player, best_point)

    def _nearest_point_on_base(self, player, head):
        pts = player.territory_points
        if not pts:
            return None
        return min(pts, key=lambda p: math.hypot(p[0] - head[0], p[1] - head[1]))

    def _nearest_point_outside_base(self, player, head):
        if not player.territory_points:
            return (head[0] + math.cos(player.angle) * 200,
                    head[1] + math.sin(player.angle) * 200)
        cx = sum(p[0] for p in player.territory_points) / len(player.territory_points)
        cy = sum(p[1] for p in player.territory_points) / len(player.territory_points)
        dx, dy = head[0] - cx, head[1] - cy
        d = math.hypot(dx, dy) or 1.0
        return (head[0] + dx / d * 200, head[1] + dy / d * 200)

    def _steer_towards(self, player, target):
        desired = math.atan2(target[1] - player.get_head()[1],
                             target[0] - player.get_head()[0])
        diff = (desired - player.angle + math.pi) % (2 * math.pi) - math.pi
        if abs(diff) < 0.08:
            return self._avoid_self_trail(player)
        return 1 if diff > 0 else -1

    def _avoid_self_trail(self, player):
        if player.in_base or len(player.points) < 6:
            return 0
        head = player.get_head()
        for pt in player.points[:-10]:
            if math.hypot(pt[0] - head[0], pt[1] - head[1]) < self.SELF_TRAIL_AVOID_DIST:
                return self.rng.choice([-1, 1])
        return 0

    def _wander_step(self):
        if self.rng.random() < self.WANDER_CHANCE:
            self._wander = self.rng.choice([-1, 0, 1])
        return self._wander