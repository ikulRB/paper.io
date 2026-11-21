import pygame
from shapely.geometry import box


class BoardRenderer:
    def __init__(self, screen, volume_shift=6):
        self.screen = screen
        self.width = screen.get_width()
        self.height = screen.get_height()
        self.volume_shift = volume_shift

    def draw_background(self, camera, map_radius):
        s = self.screen
        s.fill((140, 140, 140))
        pygame.draw.circle(s, (235, 235, 235), (int(camera.offset_x), int(camera.offset_y)), map_radius)
        pygame.draw.circle(s, (40, 40, 40), (int(camera.offset_x), int(camera.offset_y)), map_radius, 3)

    def draw_trail(self, camera, player):
        """Хвост одного игрока."""
        if player.is_dead or player.in_base or len(player.points) <= 1:
            return
        s = self.screen
        for point in player.points[:-1]:
            pygame.draw.circle(
                s, player.trail_volume_color,
                (int(point[0] + camera.offset_x), int(point[1] + camera.offset_y + self.volume_shift)),
                7,
            )
        for point in player.points[:-1]:
            pygame.draw.circle(
                s, player.trail_color,
                (int(point[0] + camera.offset_x), int(point[1] + camera.offset_y)),
                7,
            )

    def draw_territory(self, camera, player):
        if player.is_dead or len(player.territory_points) <= 2:
            return
        s = self.screen
        screen_box = box(
            -camera.offset_x - 50, -camera.offset_y - 50,
            -camera.offset_x + self.width + 50, -camera.offset_y + self.height + 50,
        )
        visible = player.base_polygon.intersection(screen_box)
        if visible.is_empty:
            return

        if visible.geom_type == "Polygon":
            polys = [visible]
        elif visible.geom_type == "MultiPolygon":
            polys = list(visible.geoms)
        elif visible.geom_type == "GeometryCollection":
            polys = [g for g in visible.geoms if g.geom_type in ("Polygon", "MultiPolygon")]
        else:
            polys = []

        for poly in polys:
            if poly.geom_type == "MultiPolygon":
                sub_polys = list(poly.geoms)
            else:
                sub_polys = [poly]

            for p in sub_polys:
                if not p.exterior or len(p.exterior.coords) <= 2:
                    continue
                coords = list(p.exterior.coords)
                sub_vol = [(pt[0] + camera.offset_x, pt[1] + camera.offset_y + self.volume_shift) for pt in coords]
                pygame.draw.polygon(s, player.volume_color, sub_vol)
                sub_terr = [(pt[0] + camera.offset_x, pt[1] + camera.offset_y) for pt in coords]
                pygame.draw.polygon(s, player.territory_color, sub_terr)