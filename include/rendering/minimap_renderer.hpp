#pragma once
#include <SFML/Graphics.hpp>
#include <vector>
#include <memory>
#include "game/player.hpp"

class MinimapRenderer {
public:
    MinimapRenderer(float miniRadius, float mapRadius, float margin = 20.f);
    void draw(sf::RenderTarget &target, const std::vector<std::unique_ptr<Player>> &players);
private:
    float miniRadius, mapRadius, scale, cx, cy;
    sf::Vector2f toMini(Point p) const;
};