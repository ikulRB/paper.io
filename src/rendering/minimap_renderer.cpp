#include "rendering/minimap_renderer.hpp"
#include <cmath>

MinimapRenderer::MinimapRenderer(float miniR, float mapR, float margin)
    : miniRadius(miniR), mapRadius(mapR) {
    scale = miniRadius / mapRadius;
    cx = margin + miniRadius;
    cy = margin + miniRadius;
}

sf::Vector2f MinimapRenderer::toMini(Point p) const {
    return { p.x * scale + cx, p.y * scale + cy };
}

void MinimapRenderer::draw(sf::RenderTarget &target, const std::vector<std::unique_ptr<Player>> &players) {
    sf::CircleShape bg(miniRadius);
    bg.setOrigin({miniRadius, miniRadius});
    bg.setPosition({cx, cy});
    bg.setFillColor(sf::Color(240, 240, 240));
    bg.setOutlineColor(sf::Color::Black);
    bg.setOutlineThickness(2.f);
    target.draw(bg);

    for (const auto &p : players) {
        if (p->isDead) continue;
        if (p->territoryPoints.size() > 2) {
            sf::ConvexShape poly(p->territoryPoints.size());
            for (size_t i = 0; i < p->territoryPoints.size(); ++i)
                poly.setPoint(i, toMini(p->territoryPoints[i]));
            poly.setFillColor(p->territoryColor);
            target.draw(poly);
        }
        if (!p->inBase && p->points.size() > 1) {
            sf::VertexArray lines(sf::PrimitiveType::LineStrip, p->points.size());
            for (size_t i = 0; i < p->points.size(); ++i) {
                lines[i].position = toMini(p->points[i]);
                lines[i].color = p->trailColor;
            }
            target.draw(lines);
        }
        auto h = toMini(const_cast<Player &>(*p).getHead());
        sf::ConvexShape tri(3);
        tri.setPoint(0, { h.x + 4, h.y });
        tri.setPoint(1, { h.x - 3, h.y - 3 });
        tri.setPoint(2, { h.x - 3, h.y + 3 });
        tri.setFillColor(p->color);
        tri.setOutlineColor(sf::Color::Black);
        tri.setOutlineThickness(1.f);
        target.draw(tri);
    }
}