#pragma once
#include <SFML/Graphics.hpp>
#include "game/player.hpp"
#include "game/camera.hpp"

class BoardRenderer {
public:
    explicit BoardRenderer(int volumeShift = 6) : volumeShift(volumeShift) {}
    void drawBackground(sf::RenderTarget &t, const Camera &cam, float mapRadius);
    void drawTrail(sf::RenderTarget &t, const Camera &cam, const Player &p);
    void drawTerritory(sf::RenderTarget &t, const Camera &cam, const Player &p);
private:
    int volumeShift;
};