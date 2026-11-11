#include "ui/menu.hpp"
#include <cmath>
#include <optional>

Menu::Menu(sf::RenderWindow &w, const Fonts &f) : window(w), fonts(f),
    picker(cfg::WIDTH / 2.f, cfg::HEIGHT / 2.f + 125.f, cfg::AVAILABLE_COLORS) 
{
    inputRect = sf::FloatRect({cfg::WIDTH / 2.f - 175.f, cfg::HEIGHT / 2.f - 130.f}, {350.f, 40.f});
    botsBtn = sf::FloatRect({cfg::WIDTH / 2.f - 175.f, cfg::HEIGHT / 2.f - 22.f}, {165.f, 45.f});
    netBtn = sf::FloatRect({cfg::WIDTH / 2.f + 10.f, cfg::HEIGHT / 2.f - 22.f}, {165.f, 45.f});
}

std::pair<std::string, sf::Color> Menu::run(const std::string &currentName, sf::Color currentColor) {
    std::string playerName = currentName;
    int colorIdx = 0;
    for (size_t i = 0; i < cfg::AVAILABLE_COLORS.size(); ++i) {
        if (cfg::AVAILABLE_COLORS[i] == currentColor) { colorIdx = (int)i; break; }
    }
    picker.selectedIdx = colorIdx;
    bool inputActive = false;
    sf::Clock clock;
    float errorAlpha = 0.f;

    while (window.isOpen()) {
        float time = clock.getElapsedTime().asSeconds();
        sf::Vector2i mouse = sf::Mouse::getPosition(window);
        bool hoverBots = botsBtn.contains({(float)mouse.x, (float)mouse.y});
        bool hoverNet = netBtn.contains({(float)mouse.x, (float)mouse.y});

        while (const std::optional event = window.pollEvent()) {
            if (event->is<sf::Event::Closed>()) window.close();
            
            if (const auto *mouseBtn = event->getIf<sf::Event::MouseButtonPressed>()) {
                if (mouseBtn->button == sf::Mouse::Button::Left) {
                    inputActive = inputRect.contains({(float)mouseBtn->position.x, (float)mouseBtn->position.y});
                    int idx = picker.hitTest((float)mouseBtn->position.x, (float)mouseBtn->position.y);
                    if (idx != -1) picker.selectedIdx = idx;
                    if (hoverBots) {
                        if (playerName.empty()) errorAlpha = 100.f;
                        else return { playerName, cfg::AVAILABLE_COLORS[picker.selectedIdx] };
                    }
                }
            }
            
            if (const auto *textEntered = event->getIf<sf::Event::TextEntered>()) {
                if (inputActive) {
                    if (textEntered->unicode == 8) {
                        if (!playerName.empty()) playerName.pop_back();
                    } else if (textEntered->unicode == 13) {
                        if (playerName.empty()) errorAlpha = 100.f;
                        else return { playerName, cfg::AVAILABLE_COLORS[picker.selectedIdx] };
                    } else if (textEntered->unicode < 128 && playerName.size() < cfg::MAX_NAME_LEN) {
                        char c = (char)textEntered->unicode;
                        if (c >= 32 && c < 127) playerName += c;
                    }
                }
            }
        }

        if (errorAlpha > 0.f) errorAlpha = std::max(0.f, errorAlpha - 2.f);
        draw(playerName, inputActive, hoverBots, hoverNet, errorAlpha, time);
        window.display();
    }
    return { "", sf::Color::Black };
}

void Menu::draw(const std::string &playerName, bool inputActive, bool hoverBots, bool hoverNet, float errorAlpha, float time) {
    window.clear(cfg::COLOR_BG);

    sf::Text title(fonts.title, "PAPER.IO 3D", 36);
    title.setFillColor(cfg::COLOR_TEXT);
    auto b = title.getLocalBounds();
    title.setPosition({cfg::WIDTH / 2.f - b.size.x / 2.f, cfg::HEIGHT / 2.f - 200.f});
    window.draw(title);

    bool cursorVisible = (int)(time * 2.5f) % 2 == 0;
    drawTextInput(window, inputRect, playerName, inputActive, fonts.ui, cursorVisible, "Enter name", errorAlpha);

    drawGameButton(window, "AI BOTS", botsBtn, hoverBots, "bots", fonts.ui);
    drawGameButton(window, "ONLINE", netBtn, hoverNet, "net", fonts.ui);

    sf::Text colorLbl(fonts.ui, "Choose color:", 20);
    colorLbl.setFillColor(cfg::COLOR_TEXT);
    auto cb = colorLbl.getLocalBounds();
    colorLbl.setPosition({cfg::WIDTH / 2.f - cb.size.x / 2.f, cfg::HEIGHT / 2.f + 75.f});
    window.draw(colorLbl);

    picker.draw(window);
}