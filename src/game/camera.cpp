#include "game/camera.hpp"

Camera::Camera(unsigned w, unsigned h) : width(w), height(h) {}

void Camera::follow(Point head) {
    offsetX = -head.x + width * 0.5f;
    offsetY = -head.y + height * 0.5f;
}

sf::Vector2f Camera::toScreen(Point p) const {
    return { p.x + offsetX, p.y + offsetY };
}