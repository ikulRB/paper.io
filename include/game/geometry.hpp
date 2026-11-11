#pragma once
#include <SFML/Graphics.hpp>
#include <vector>

using Point = sf::Vector2f;
using Points = std::vector<Point>;

class Poly {
public:
    Points exterior;

    Poly() = default;
    explicit Poly(Points pts);

    bool empty() const { return exterior.size() < 3; }
    float area() const;
    sf::FloatRect bounds() const;
    
    // Operations
    static Poly unite(const Poly &a, const Poly &b);
    static Poly intersect(const Poly &a, const Poly &b);
    static Poly difference(const Poly &a, const Poly &b);
    static Poly lineBuffer(const Points &trail, float radius);
};

Poly makeTerritoryPolygon(const Points &points);
Poly normalize(const Poly &p);
Poly mergeTrailIntoBase(const Poly &base, const Points &trail);
std::pair<Poly, Poly> carveOut(const Poly &attacker, const Poly &victim);
Points exteriorPoints(const Poly &p);