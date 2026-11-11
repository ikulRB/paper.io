#pragma once
#include <SFML/Graphics.hpp>
#include "game/game.hpp"
#include "ui/pause.hpp"

class PlayState {
public:
    PlayState(sf::RenderWindow &window, const Fonts &fonts, PauseMenu &pauseMenu);
    void run(const std::string &name, sf::Color color);
private:
    sf::RenderWindow &window;
    Fonts fonts;
    PauseMenu &pauseMenu;
    const int NUM_BOTS = 20;
    sf::FloatRect okBtn;
    
    void drawEndOverlay(Game &game, float time, sf::Vector2i mousePos);
    float computePanelY(float time);
    void drawPanel(Game &game, float panelY, bool win);
    void drawEndMinimap(Game &game, float panelY);
    void drawOkButton(float panelY, sf::Vector2i mousePos);
};