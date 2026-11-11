#pragma once
#include <SFML/Graphics.hpp>
#include <string>
#include "config.hpp"
#include "ui/widgets.hpp"

class Menu {
public:
    Menu(sf::RenderWindow &window, const Fonts &fonts);
    std::pair<std::string, sf::Color> run(const std::string &currentName = "", sf::Color currentColor = cfg::AVAILABLE_COLORS[0]);
private:
    sf::RenderWindow &window;
    Fonts fonts;
    sf::FloatRect inputRect, botsBtn, netBtn;
    ColorPicker picker;
    
    void draw(const std::string &playerName, bool inputActive, bool hoverBots, bool hoverNet, float errorAlpha, float time);
    bool handleKey(sf::Keyboard::Key key, char32_t unicode, std::string &name);
};