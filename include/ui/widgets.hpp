#pragma once
#include <SFML/Graphics.hpp>
#include <string>
#include "config.hpp"

void drawRoundedButton(sf::RenderTarget &target, const sf::FloatRect &rect, const std::string &text, bool isHovered, const sf::Font &font);
void drawGameButton(sf::RenderTarget &target, const std::string &text, const sf::FloatRect &rect, bool isHovered, const std::string &type, const sf::Font &font);
void drawTextInput(sf::RenderTarget &target, const sf::FloatRect &rect, const std::string &text, bool isActive, const sf::Font &font, bool cursorVisible, const std::string &placeholder, float errorAlpha = 0.f);

class ColorPicker {
public:
    ColorPicker(float centerX, float topY, const std::vector<sf::Color> &colors);
    void draw(sf::RenderTarget &target);
    int hitTest(float mx, float my);
    int selectedIdx = 0;
private:
    float centerX, topY, radius = 18.f, stepX = 50.f, stepY = 45.f;
    int cols = 5;
    const std::vector<sf::Color> &colors;
    sf::Vector2f getCenter(int i);
};