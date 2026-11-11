#include "game/geometry.hpp"
#include <cmath>
#include <algorithm>
#include "clipper2/clipper.h"

using namespace Clipper2Lib;

static PathD toPath(const Points &pts) {
    PathD p;
    p.reserve(pts.size());
    for (auto &v : pts) p.emplace_back((double)v.x, (double)v.y);
    return p;
}

static Points fromPath(const PathD &path) {
    Points out;
    out.reserve(path.size());
    for (auto &p : path) out.emplace_back((float)p.x, (float)p.y);
    return out;
}

static Poly fromPaths(const PathsD &paths) {
    if (paths.empty()) return {};
    size_t best = 0; double bestArea = -1;
    for (size_t i = 0; i < paths.size(); ++i) {
        double a = std::abs(Area(paths[i]));
        if (a > bestArea) { bestArea = a; best = i; }
    }
    Poly out;
    out.exterior = fromPath(paths[best]);
    return out;
}

Poly::Poly(Points pts) : exterior(std::move(pts)) {}

float Poly::area() const {
    if (exterior.size() < 3) return 0.f;
    return (float)std::abs(Area(toPath(exterior)));
}

sf::FloatRect Poly::bounds() const {
    if (exterior.empty()) return {};
    
    float minx = exterior[0].x, maxx = minx;
    float miny = exterior[0].y, maxy = miny;
    
    for (const auto &p : exterior) {
        minx = std::min(minx, p.x); maxx = std::max(maxx, p.x);
        miny = std::min(miny, p.y); maxy = std::max(maxy, p.y);
    }
    
    return sf::FloatRect({minx, miny}, {maxx - minx, maxy - miny});
}

static PathsD clipOp(ClipType t, const Points &a, const Points &b) {
    ClipperD c;
    c.AddSubject({ toPath(a) });
    c.AddClip({ toPath(b) });
    PathsD out;
    c.Execute(t, FillRule::NonZero, out);
    return out;
}

Poly Poly::unite(const Poly &a, const Poly &b) {
    if (a.empty()) return b;
    if (b.empty()) return a;
    PathsD r;
    ClipperD c;
    c.AddSubject({ toPath(a.exterior) });
    c.AddSubject({ toPath(b.exterior) });
    c.Execute(ClipType::Union, FillRule::NonZero, r);
    return fromPaths(r);
}

Poly Poly::intersect(const Poly &a, const Poly &b) {
    if (a.empty() || b.empty()) return {};
    return fromPaths(clipOp(ClipType::Intersection, a.exterior, b.exterior));
}

Poly Poly::difference(const Poly &a, const Poly &b) {
    if (a.empty()) return {};
    if (b.empty()) return a;
    return fromPaths(clipOp(ClipType::Difference, a.exterior, b.exterior));
}

Poly Poly::lineBuffer(const Points &trail, float radius) {
    if (trail.size() < 2) return {};
    PathD line = toPath(trail);
    PathsD buffered = InflatePaths({ line }, radius, JoinType::Round, EndType::Round);
    return fromPaths(buffered);
}

Poly makeTerritoryPolygon(const Points &points) {
    return normalize(Poly(points));
}

Poly normalize(const Poly &p) {
    if (p.empty()) return {};
    PathD simplified = SimplifyPath(toPath(p.exterior), 1.0, false);
    if (simplified.size() < 3) return {};
    return Poly(fromPath(simplified));
}

Poly mergeTrailIntoBase(const Poly &base, const Points &trail) {
    Poly trailPoly = Poly::lineBuffer(trail, 1.5f);
    return normalize(Poly::unite(base, trailPoly));
}

std::pair<Poly, Poly> carveOut(const Poly &attacker, const Poly &victim) {
    Poly overlap = Poly::intersect(attacker, victim);
    if (overlap.empty()) return { attacker, victim };

    Poly newAttacker = Poly::unite(attacker, overlap);
    Poly remaining   = Poly::difference(victim, overlap);
    return { normalize(newAttacker), normalize(remaining) };
}

Points exteriorPoints(const Poly &p) { return p.exterior; }