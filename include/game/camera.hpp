#pragma once
#include <SFML/Graphics.hpp>
#include "game/geometry.hpp"

class Camera {
public:
    float offsetX = 0.f, offsetY = 0.f;
    unsigned width, height;

    Camera(unsigned w, unsigned h);
    void follow(Point head);
    sf::Vector2f toScreen(Point p) const;
};