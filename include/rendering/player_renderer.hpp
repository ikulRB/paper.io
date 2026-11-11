#pragma once
#include <SFML/Graphics.hpp>
#include <vector>
#include <memory>
#include "game/player.hpp"
#include "game/camera.hpp"

class PlayerRenderer {
public:
    PlayerRenderer(const sf::Font &font, int volumeShift = 6) : font(font), volumeShift(volumeShift) {}
    void drawPlayers(sf::RenderTarget &t, const Camera &cam, const std::vector<std::unique_ptr<Player>> &players, const Player *mainPlayer);
private:
    const sf::Font &font;
    int volumeShift;
    void drawShip(sf::RenderTarget &t, const Camera &cam, const Player &p, bool leader, float time);
    void drawName(sf::RenderTarget &t, const Camera &cam, const Player &p, bool isMain);
};