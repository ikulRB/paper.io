#include "rendering/board_renderer.hpp"

void BoardRenderer::drawBackground(sf::RenderTarget &t, const Camera &cam, float mapRadius) {
    t.clear(sf::Color(140, 140, 140));
    sf::CircleShape circle(mapRadius);
    circle.setOrigin({mapRadius, mapRadius});
    circle.setPosition({cam.offsetX, cam.offsetY});
    circle.setFillColor(sf::Color(235, 235, 235));
    circle.setOutlineColor(sf::Color(40, 40, 40));
    circle.setOutlineThickness(3.f);
    t.draw(circle);
}

void BoardRenderer::drawTrail(sf::RenderTarget &t, const Camera &cam, const Player &p) {
    if (p.isDead || p.inBase || p.points.size() <= 1) return;
    sf::CircleShape dot(7.f);
    dot.setOrigin({7.f, 7.f});
    dot.setFillColor(p.trailVolumeColor);
    for (size_t i = 0; i + 1 < p.points.size(); ++i) {
        auto s = cam.toScreen(p.points[i]);
        dot.setPosition({s.x, s.y + volumeShift});
        t.draw(dot);
    }
    dot.setFillColor(p.trailColor);
    for (size_t i = 0; i + 1 < p.points.size(); ++i) {
        auto s = cam.toScreen(p.points[i]);
        dot.setPosition({s.x, s.y});
        t.draw(dot);
    }
}

void BoardRenderer::drawTerritory(sf::RenderTarget &t, const Camera &cam, const Player &p) {
    if (p.isDead || p.territoryPoints.size() <= 2 || p.basePolygon.empty()) return;
    sf::ConvexShape shape;
    shape.setPointCount(p.territoryPoints.size());
    for (size_t i = 0; i < p.territoryPoints.size(); ++i) {
        auto s = cam.toScreen(p.territoryPoints[i]);
        shape.setPoint(i, { s.x, s.y + volumeShift });
    }
    shape.setFillColor(p.volumeColor);
    t.draw(shape);

    for (size_t i = 0; i < p.territoryPoints.size(); ++i) {
        auto s = cam.toScreen(p.territoryPoints[i]);
        shape.setPoint(i, s);
    }
    shape.setFillColor(p.territoryColor);
    t.draw(shape);
}