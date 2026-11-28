import math
import pygame
from shapely.geometry import Point, LineString, Polygon

from config import AVAILABLE_COLORS
from game.player import Player
from game.camera import Camera
from game.geometry import merge_trail_into_base, carve_out
from game.leaderboard import Leaderboard
from game.controllers import BotController
from rendering.board_renderer import BoardRenderer
from rendering.player_renderer import PlayerRenderer
from rendering.minimap_renderer import MinimapRenderer
from rendering.particles import ParticleManager


MAP_RADIUS = 2000
MINI_RADIUS = 80
VOLUME_SHIFTY = 6
DELTA_ANGLE = 0.06
BOUNDARY_MARGIN = 10
SELF_TRAIL_SAFE = 15
OTHER_TRAIL_SAFE = 2
COLLISION_DISTANCE = 5.0
MIN_TRAIL_FOR_COLLISION = 6
WIN_PERCENT = 70.0

BOT_NAMES = ["Bot Alpha", "Bot Beta", "Bot Gamma", "Bot Delta", "Bot Epsilon"]


class Game:
    def __init__(self, screen, player_name, player_color, num_bots=5, bot_colors=None, is_network=False):
        self.screen = screen
        self.width = screen.get_width()
        self.height = screen.get_height()

        self.MAP_RADIUS = MAP_RADIUS
        self.MINI_RADIUS = MINI_RADIUS
        self.TOTAL_MAP_AREA = math.pi * ((self.MAP_RADIUS - BOUNDARY_MARGIN) ** 2)
        self.VOLUME_SHIFTY = VOLUME_SHIFTY
        self.delta_angle = DELTA_ANGLE
        self.win_percent = WIN_PERCENT

        self.is_network = is_network
        self.network_steer_dirs = {}

        self.font_name = pygame.font.SysFont("Arial", 18, bold=True)
        self.font_leaderboard = pygame.font.SysFont("Arial", 16, bold=True)
        self.font_gameover = pygame.font.SysFont("Arial", 38, bold=True)

        first_player = Player(player_name, player_color, self.MAP_RADIUS)
        self.players = [first_player]
        self.main_player = first_player

        if not is_network:
            self._spawn_bots(num_bots, bot_colors)
        # В сетевом режиме main_player сохраняет валидную стартовую территорию
        # из Player.__init__ — её разошлёт мастер (если это хост) или
        # перезапишет первый StateMsg (если это клиент).

        self.final_territory_points = []
        self.final_player_color = player_color
        self.final_territory_color = self.main_player.territory_color

        self.result = None

        self.particles = ParticleManager(screen)

        self.camera = Camera(self.width, self.height)
        self.board_renderer = BoardRenderer(screen, VOLUME_SHIFTY)
        self.player_renderer = PlayerRenderer(screen, self.font_name, VOLUME_SHIFTY)
        self.minimap_renderer = MinimapRenderer(screen, MINI_RADIUS, MAP_RADIUS)
        self.leaderboard = Leaderboard(screen, self.font_leaderboard)

    def _spawn_bots(self, count, bot_colors):
        palette = bot_colors or [
            (220, 50, 50), (50, 50, 220), (220, 180, 50),
            (180, 50, 220), (0, 206, 209), (255, 140, 0),
            (255, 105, 180), (124, 252, 0),
        ]
        for i in range(count):
            color = palette[i % len(palette)]
            name = BOT_NAMES[i % len(BOT_NAMES)]
            bot = Player(name, color, self.MAP_RADIUS, controller=BotController())
            self.players.append(bot)

    def update(self):
        self.particles.update()

        if self.main_player.is_dead:
            self.result = "lose"
            for p in self.players:
                if not p.is_dead:
                    self._apply_control(p)
                    self._move_player(p)
            self._resolve_collisions()
            return False

        for p in self.players:
            if not p.is_dead:
                self._apply_control(p)
                self._move_player(p)
        self._resolve_collisions()

        if self._check_victory():
            self.result = "win"
            return False

        return True

    def apply_steer(self, player_id, steer_dir):
        if steer_dir < -0.5:
            self.network_steer_dirs[player_id] = -1
        elif steer_dir > 0.5:
            self.network_steer_dirs[player_id] = 1
        else:
            self.network_steer_dirs[player_id] = 0

    def update_network(self, skip_collisions=False):
        self.particles.update()

        for p in self.players:
            if p.is_dead:
                continue
            pid = getattr(p, "player_id", 0)
            steer = self.network_steer_dirs.get(pid, 0)
            if steer < 0:
                p.angle -= self.delta_angle
            elif steer > 0:
                p.angle += self.delta_angle
            self._move_player(p)

        if not skip_collisions:
            self._resolve_collisions()

        if self.main_player.is_dead:
            self.result = "lose"
        elif self._check_victory():
            self.result = "win"

    def step_client_local(self, my_steer_dir):
        self.particles.update()

        if self.main_player and not self.main_player.is_dead:
            self.main_player._is_turning_locally = (my_steer_dir != 0)
            if my_steer_dir < 0:
                self.main_player.angle -= self.delta_angle
            elif my_steer_dir > 0:
                self.main_player.angle += self.delta_angle

        for p in self.players:
            if not p.is_dead:
                p.predict_step(is_local_player=(p is self.main_player))

    def sync_players(self, net_players, my_id=0):
        net_ids = [np.get("player_id") for np in net_players]

        for p in self.players:
            pid = getattr(p, "player_id", 0)
            if pid != 0 and pid not in net_ids and not p.is_dead:
                self._kill_player(p)

        self.players = [p for p in self.players if getattr(p, "player_id", 0) in net_ids]

        for np in net_players:
            pid = np.get("player_id")
            color_idx = np.get("color_idx")
            if pid == my_id and my_id != 0:
                color = self.final_player_color
            elif color_idx is not None and 0 <= color_idx < len(AVAILABLE_COLORS):
                color = AVAILABLE_COLORS[color_idx]
            else:
                color = AVAILABLE_COLORS[(pid - 1) % len(AVAILABLE_COLORS)]

            player = next((p for p in self.players if getattr(p, "player_id", 0) == pid), None)
            if not player:
                player = Player(np.get("name", "Player"), color, self.MAP_RADIUS)
                player.player_id = pid
                hx, hy = np.get("head", (0.0, 0.0))
                player.last_head = (hx, hy)
                player.points = [(hx, hy)]
                player.base_trail_points = [(hx, hy)]
                player.angle = np.get("angle", 0.0)
                self.players.append(player)
            else:
                player.name = np.get("name", player.name)
                if player.color != color:
                    player.set_color(color)

            if my_id != 0 and pid == my_id:
                self.main_player = player

            was_dead = player.is_dead
            is_dead_now = np.get("is_dead", False)

            if not was_dead and is_dead_now:
                self._kill_player(player)

            hx, hy = np.get("head", (0.0, 0.0))
            player.apply_network_snapshot(
                hx,
                hy,
                np.get("angle", 0.0),
                in_base=np.get("in_base", True),
                territory=np.get("territory") or None,
                score=np.get("score", 0),
                is_dead=is_dead_now,
            )

        if self.main_player.is_dead:
            self.result = "lose"
        elif len(self.players) > 1 and self._check_victory():
            self.result = "win"

    def _check_victory(self):
        if self.main_player.is_dead:
            return False
        if self.main_player.area_percentage >= self.win_percent:
            return True
        others_alive = [p for p in self.players if p is not self.main_player and not p.is_dead]
        return len(others_alive) == 0

    def _apply_control(self, p):
        if p.controller is None:
            return
        steer = p.controller.get_steer(p, self)
        if steer < 0:
            p.angle -= self.delta_angle
        elif steer > 0:
            p.angle += self.delta_angle

    def _move_player(self, p):
        head = p.get_head()
        new_head = self._clamp_to_map(p, head)
        head_point = Point(new_head)
        in_base = p.base_polygon.intersects(head_point)

        if p.in_base:
            if in_base:
                p.walk_in_base(new_head)
            else:
                p.enter_trail(head, new_head)
        else:
            p.points.append(new_head)
            if in_base and len(p.points) > 5:
                self._close_trail(p, new_head)

        p.refresh_territory()
        p.area_percentage = min(100.0, (p.base_polygon.area / self.TOTAL_MAP_AREA) * 100)

    def _clamp_to_map(self, p, head):
        hx, hy = head
        next_x = hx + math.cos(p.angle) * p.speed
        next_y = hy + math.sin(p.angle) * p.speed

        if math.hypot(next_x, next_y) < self.MAP_RADIUS - BOUNDARY_MARGIN:
            return next_x, next_y

        boundary_angle = math.atan2(hy, hx)
        angle_diff = (p.angle - boundary_angle + math.pi) % (math.pi * 2) - math.pi
        if math.cos(p.angle - boundary_angle) > 0:
            if angle_diff > 0:
                p.angle = boundary_angle + math.pi / 2
            else:
                p.angle = boundary_angle - math.pi / 2
        return (hx + math.cos(p.angle) * p.speed,
                hy + math.sin(p.angle) * p.speed)

    def _close_trail(self, p, new_head):
        p.in_base = True
        p.base_polygon = merge_trail_into_base(p.base_polygon, p.points)
        p.territory_version += 1

        for victim in self.players:
            if victim is p or victim.is_dead or victim.base_polygon.is_empty:
                continue
            new_attacker, new_victim = carve_out(p.base_polygon, victim.base_polygon)
            p.base_polygon = new_attacker
            victim.base_polygon = new_victim
            victim.territory_version += 1
            if new_victim.is_empty:
                victim.territory_points = []
            else:
                victim.refresh_territory()
            victim.area_percentage = min(
                100.0, (victim.base_polygon.area / self.TOTAL_MAP_AREA) * 100
            )

        p.base_trail_points = [new_head]
        p.points = [new_head]

        p.refresh_territory()
        p.area_percentage = min(100.0, (p.base_polygon.area / self.TOTAL_MAP_AREA) * 100)

    def _resolve_collisions(self):
        for predator in self.players:
            if predator.is_dead:
                continue
            predator_head = Point(predator.get_head())
            for victim in self.players:
                if victim.is_dead or victim.in_base or len(victim.points) <= MIN_TRAIL_FOR_COLLISION:
                    continue
                self._check_collision(predator, victim, predator_head)

    def _check_collision(self, predator, victim, predator_head):
        try:
            safe = SELF_TRAIL_SAFE if predator is victim else OTHER_TRAIL_SAFE
            trail_points = victim.points[:-safe]
            if len(trail_points) < 2:
                return
            trail_line = LineString(trail_points)
            if predator_head.distance(trail_line) < COLLISION_DISTANCE:
                self._kill_player(victim)
        except Exception as e:
            print(f"Ошибка коллизии: {e}")

    def _kill_player(self, victim):
        victim.is_dead = True
        sources = [victim.get_head()] + list(victim.points) + list(victim.territory_points)
        self.particles.spawn_for(victim, sources, per_point=2)

        if victim is self.main_player:
            victim.last_head = victim.get_head()
            self.final_territory_points = list(victim.territory_points)
            victim.territory_points = []
            victim.base_polygon = Polygon()
            victim.base_trail_points = []
            victim.points = []

    def draw(self):
        self.camera.follow(self.main_player.get_head())
        self.board_renderer.draw_background(self.camera, self.MAP_RADIUS)

        for p in self.players:
            self.board_renderer.draw_territory(self.camera, p)

        for p in self.players:
            self.board_renderer.draw_trail(self.camera, p)
            self.board_renderer.draw_territory(self.camera, p)

        self.particles.draw(self.camera)
        self.player_renderer.draw_players(self.camera, self.players, self.main_player)

        if not self.main_player.is_dead:
            self.minimap_renderer.draw(self.players)
        self.leaderboard.draw(self.players)