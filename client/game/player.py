import math
import random
from shapely.geometry import Point

from game.geometry import make_territory_polygon, exterior_points

START_TERRITORY_RADIUS = 70
START_TERRITORY_SEGMENTS = 40
BASE_TRAIL_MAX = 40


class Player:
    def __init__(self, name, color, map_radius, controller=None):
        self.name = name
        self.color = color
        self.map_radius = map_radius
        self.speed = 3
        self.in_base = True
        self.is_dead = False
        self.controller = controller
        self.player_id = 0
        self.territory_version = 1
        self._net_target_head = None
        self._net_target_angle = None
        self._is_turning_locally = False

        start_pos = self._spawn_position(map_radius)
        sx, sy = start_pos
        self.last_head = start_pos

        self.points = [start_pos]
        self.base_trail_points = [start_pos]

        self.territory_points = self._generate_start_territory(sx, sy)
        self.base_polygon = make_territory_polygon(self.territory_points)
        self.area_percentage = 0.0

        self.angle = math.atan2(sy, sx) + math.pi

        self.set_color(color)

    def set_color(self, color):
        self.color = color
        self.territory_color = color
        self.volume_color = self._darken(color, 0.6)
        self.trail_color = self._light_trail(color)
        self.trail_volume_color = self._darken(self.trail_color, 0.6)

    @staticmethod
    def _spawn_position(map_radius):
        dist = random.randint(0, int(map_radius) - 200)
        ang = random.uniform(0, math.pi * 2)
        return (dist * math.cos(ang), dist * math.sin(ang))

    @staticmethod
    def _generate_start_territory(x, y):
        territory = []
        angle = 0.0
        for _ in range(START_TERRITORY_SEGMENTS):
            territory.append((math.cos(angle) * START_TERRITORY_RADIUS + x,
                              math.sin(angle) * START_TERRITORY_RADIUS + y))
            angle += math.pi / (START_TERRITORY_SEGMENTS // 2)
        return territory

    @staticmethod
    def _darken(color, k):
        r, g, b = color
        return (int(r * k), int(g * k), int(b * k))

    @staticmethod
    def _light_trail(color):
        r, g, b = color
        return (
            int(255 - (2 / 3) * (255 - r)),
            int(255 - (2 / 3) * (255 - g)),
            int(255 - (2 / 3) * (255 - b)),
        )
    def get_head(self):
        if self.is_dead:
            return self.last_head
        if self.in_base:
            if self.base_trail_points:
                self.last_head = self.base_trail_points[-1]
            return self.last_head
        if self.points:
            self.last_head = self.points[-1]
        return self.last_head

    def enter_trail(self, head, new_head):
        self.in_base = False
        self.points = [head, new_head]
        self.base_trail_points = [new_head]

    def walk_in_base(self, new_head):
        self.base_trail_points.append(new_head)
        if len(self.base_trail_points) > BASE_TRAIL_MAX:
            self.base_trail_points.pop(0)

    def refresh_territory(self):
        pts = exterior_points(self.base_polygon)
        if pts:
            self.territory_points = pts

    def predict_step(self, is_local_player=False):
        if self.is_dead:
            return

        if self._net_target_angle is not None:
            if not (is_local_player and self._is_turning_locally):
                diff = (self._net_target_angle - self.angle + math.pi) % (2 * math.pi) - math.pi
                self.angle += diff * (0.25 if is_local_player else 0.5)

        hx, hy = self.last_head
        nx = hx + math.cos(self.angle) * self.speed
        ny = hy + math.sin(self.angle) * self.speed

        if self._net_target_head is not None:
            tx, ty = self._net_target_head
            err = math.hypot(tx - nx, ty - ny)
            if err > 80.0:
                nx, ny = tx, ty
            else:
                blend = 0.25 if is_local_player else 0.45
                nx += (tx - nx) * blend
                ny += (ty - ny) * blend

        if math.hypot(nx, ny) >= self.map_radius - 10:
            return

        self.last_head = (nx, ny)
        if self.in_base:
            self.base_trail_points = [(nx, ny)]
        else:
            self.points.append((nx, ny))

    def apply_network_snapshot(self, head_x, head_y, angle, in_base, territory=None, score=0, is_dead=False):
        self.is_dead = is_dead
        self.area_percentage = score / 100.0
        self._net_target_head = (head_x, head_y)
        self._net_target_angle = angle

        if territory:
            self.territory_points = list(territory)
            self.base_polygon = make_territory_polygon(self.territory_points)

        if in_base:
            self.in_base = True
            self.points = [(head_x, head_y)]
            self.base_trail_points = [(head_x, head_y)]
        else:
            if self.in_base:
                self.in_base = False
                self.points = [(head_x, head_y)]
            else:
                self.points.append((head_x, head_y))
            self.base_trail_points = [(head_x, head_y)]
