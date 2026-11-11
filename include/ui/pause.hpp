#pragma once
#include <SFML/Graphics.hpp>
#include "config.hpp"
#include "game/game.hpp"

class PauseMenu {
public:
    PauseMenu(sf::RenderWindow &window, const Fonts &fonts);
    std::string run(const std::string &pauseType, Game &currentGame);
private:
    sf::RenderWindow &window;
    Fonts fonts;
};