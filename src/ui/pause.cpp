#include "ui/pause.hpp"
#include "ui/widgets.hpp"
#include <optional>

PauseMenu::PauseMenu(sf::RenderWindow &w, const Fonts &f) : window(w), fonts(f) {}

std::string PauseMenu::run(const std::string &pauseType, Game &currentGame) {
    sf::FloatRect btnResume({cfg::WIDTH / 2.f - 120.f, cfg::HEIGHT / 2.f - 40.f}, {240.f, 50.f});
    sf::FloatRect btnAction({cfg::WIDTH / 2.f - 120.f, cfg::HEIGHT / 2.f + 30.f}, {240.f, 50.f});
    std::string actionText = (pauseType == "esc") ? "MENU" : "EXIT";

    while (window.isOpen()) {
        sf::Vector2i mouse = sf::Mouse::getPosition(window);
        bool hoverResume = btnResume.contains({(float)mouse.x, (float)mouse.y});
        bool hoverAction = btnAction.contains({(float)mouse.x, (float)mouse.y});

        while (const std::optional event = window.pollEvent()) {
            if (event->is<sf::Event::Closed>()) window.close();
            
            if (const auto *key = event->getIf<sf::Event::KeyPressed>()) {
                if (key->code == sf::Keyboard::Key::Escape && pauseType == "esc") return "resume";
            }
            
            if (const auto *mouseBtn = event->getIf<sf::Event::MouseButtonPressed>()) {
                if (mouseBtn->button == sf::Mouse::Button::Left) {
                    if (hoverResume) return "resume";
                    if (hoverAction) return (pauseType == "esc") ? "menu" : "exit";
                }
            }
        }

        currentGame.draw();
        
        sf::RectangleShape overlay({(float)cfg::WIDTH, (float)cfg::HEIGHT});
        overlay.setFillColor(sf::Color(0, 0, 0, 150));
        window.draw(overlay);

        sf::RectangleShape panel({320.f, 250.f});
        panel.setPosition({cfg::WIDTH / 2.f - 160.f, cfg::HEIGHT / 2.f - 130.f});
        panel.setFillColor(cfg::COLOR_PANEL);
        window.draw(panel);

        sf::Text title(fonts.title, pauseType == "esc" ? "PAUSE" : "EXIT?", 36);
        title.setFillColor(cfg::COLOR_TEXT);
        auto tb = title.getLocalBounds();
        title.setPosition({cfg::WIDTH / 2.f - tb.size.x / 2.f, panel.getPosition().y + 20.f});
        window.draw(title);

        drawRoundedButton(window, btnResume, "RESUME", hoverResume, fonts.ui);
        drawRoundedButton(window, btnAction, actionText, hoverAction, fonts.ui);
        window.display();
    }
    return "exit";
}