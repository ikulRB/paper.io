#pragma once
#include <SFML/Graphics.hpp>
#include <vector>
#include <memory>
#include "game/player.hpp"

class Leaderboard {
public:
    Leaderboard(const sf::Font &font, unsigned screenW);
    void draw(sf::RenderTarget &t, const std::vector<std::unique_ptr<Player>> &players);
private:
    const sf::Font &font;
    float startX, startY = 20.f, barWidth = 220.f, barHeight = 24.f, spacing = 35.f;
    void drawRow(sf::RenderTarget &t, const Player &p, float y);
};