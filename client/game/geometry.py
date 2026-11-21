import shapely.errors
from shapely.geometry import Polygon, LineString
from shapely.ops import unary_union


def make_territory_polygon(points):
    return Polygon(points).buffer(0)


def merge_trail_into_base(base_polygon, trail_points):
    try:
        trail_line = LineString(trail_points)
        trail_polygon = trail_line.buffer(1.5, cap_style=1, join_style=1)
        combined = unary_union([base_polygon, trail_polygon])
        return _normalize(combined)
    except shapely.errors.GEOSException as e:
        print(f"Геометрия проигнорирована: {e}")
        return base_polygon


def exterior_points(polygon):
    if polygon is None or polygon.is_empty:
        return []
    if polygon.exterior:
        return list(polygon.exterior.coords)
    return []


def carve_out(attacker_polygon, victim_polygon):
    try:
        if attacker_polygon.is_empty or victim_polygon.is_empty:
            return attacker_polygon, victim_polygon
        if not attacker_polygon.intersects(victim_polygon):
            return attacker_polygon, victim_polygon

        overlap = attacker_polygon.intersection(victim_polygon)
        if overlap.is_empty:
            return attacker_polygon, victim_polygon

        new_attacker = unary_union([attacker_polygon, overlap])
        remaining = victim_polygon.difference(overlap)

        return _normalize(new_attacker), _normalize(remaining)
    except shapely.errors.GEOSException as e:
        print(f"Перекраска проигнорирована: {e}")
        return attacker_polygon, victim_polygon


def _normalize(poly):
    if poly is None or poly.is_empty:
        return Polygon()

    geom = poly
    if geom.geom_type == "GeometryCollection":
        polys = [g for g in geom.geoms if g.geom_type in ("Polygon", "MultiPolygon")]
        if not polys:
            return Polygon()
        geom = unary_union(polys)

    if geom.is_empty:
        return Polygon()

    if geom.geom_type == "MultiPolygon":
        geom = max(geom.geoms, key=lambda a: a.area)
    elif geom.geom_type != "Polygon":
        return Polygon()

    if geom.is_empty or not geom.exterior or len(geom.exterior.coords) < 4:
        return Polygon()

    return Polygon(geom.exterior).simplify(1.0, preserve_topology=True).buffer(0)