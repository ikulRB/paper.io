#include "states/play_state.hpp"
#include "ui/widgets.hpp"
#include <cmath>
#include <string>
#include <cstdint>

PlayState::PlayState(sf::RenderWindow &w, const Fonts &f, PauseMenu &pm) : window(w), fonts(f), pauseMenu(pm) {
    okBtn = sf::FloatRect({cfg::WIDTH / 2.f - 60.f, 0.f}, {120.f, 40.f});
}

void PlayState::run(const std::string &name, sf::Color color) {
    Game game(window, name, color, NUM_BOTS, fonts);
    game.mainPlayer->controller = std::make_unique<HumanController>();

    bool isAlive = true;
    float deathAnimTime = 0.f;
    sf::Clock frameClock;

    while (window.isOpen()) {
        sf::Vector2i mouse = sf::Mouse::getPosition(window);
        std::string pauseTrigger;

        while (const std::optional event = window.pollEvent()) {
            if (event->is<sf::Event::Closed>()) pauseTrigger = "cross";
            if (event->is<sf::Event::KeyPressed>() && event->getIf<sf::Event::KeyPressed>()->code == sf::Keyboard::Key::Escape) pauseTrigger = "esc";
            if (!isAlive && event->is<sf::Event::MouseButtonPressed>() && deathAnimTime > 1500.f) {
                auto mouseEvent = event->getIf<sf::Event::MouseButtonPressed>();
                if (mouseEvent->button == sf::Mouse::Button::Left) {
                    if (okBtn.contains({(float)mouseEvent->position.x, (float)mouseEvent->position.y})) return;
                }
            }
        }

        if (!pauseTrigger.empty() && isAlive) {
            std::string result = pauseMenu.run(pauseTrigger, game);
            if (result == "menu") return;
            if (result == "exit") { window.close(); return; }
        }

        bool newIsAlive = game.update();
        isAlive = newIsAlive;

        game.draw();

        if (!isAlive) {
            deathAnimTime += 16.67f;
            drawEndOverlay(game, deathAnimTime, mouse);
        }

        window.display();
        sf::Time elapsed = frameClock.restart();
        if (elapsed.asMilliseconds() < 16) sf::sleep(sf::milliseconds(16 - elapsed.asMilliseconds()));
    }
}

void PlayState::drawEndOverlay(Game &game, float time, sf::Vector2i mouse) {
    bool win = (game.result == "win");
    
    if (time > 900.f) {
        float alpha = std::min(110.f, (time - 900.f) * 0.18f);
        sf::RectangleShape overlay({(float)cfg::WIDTH, (float)cfg::HEIGHT});
        overlay.setFillColor(win ? sf::Color(30, 120, 40, static_cast<std::uint8_t>(alpha)) : sf::Color(160, 20, 20, static_cast<std::uint8_t>(alpha)));
        window.draw(overlay);
    }

    if (time >= 1000.f) {
        float panelY = computePanelY(time);
        drawPanel(game, panelY, win);
        if (time > 1500.f) drawOkButton(panelY, mouse);
    }
}

float PlayState::computePanelY(float time) {
    float progress = std::min(1.f, (time - 1000.f) / 500.f);
    float elasticOffset = std::sin(progress * 3.14159265f) * 30.f * (1.f - progress);
    return -420.f + (cfg::HEIGHT / 2.f - 420.f / 2.f + 420.f) * progress - elasticOffset;
}

void PlayState::drawPanel(Game &game, float panelY, bool win) {
    sf::RectangleShape panel({440.f, 420.f});
    panel.setPosition({cfg::WIDTH / 2.f - 220.f, panelY});
    panel.setFillColor(cfg::COLOR_PANEL);
    panel.setOutlineColor(sf::Color::Black);
    panel.setOutlineThickness(3.f);
    window.draw(panel);

    sf::Text title(fonts.gameover, win ? "VICTORY!" : "DEFEAT", 38);
    title.setFillColor(win ? sf::Color(40, 160, 60) : sf::Color(200, 30, 30));
    auto tb = title.getLocalBounds();
    title.setPosition({cfg::WIDTH / 2.f - tb.size.x / 2.f, panelY + 20.f});
    window.draw(title);

    std::string scoreStr = "Your share: " + std::to_string(game.mainPlayer->areaPercentage).substr(0, 4) + " %";
    sf::Text score(fonts.name, scoreStr, 18);
    score.setFillColor(cfg::COLOR_TEXT);
    auto sb = score.getLocalBounds();
    score.setPosition({cfg::WIDTH / 2.f - sb.size.x / 2.f, panelY + 75.f});
    window.draw(score);

    drawEndMinimap(game, panelY);
}

void PlayState::drawEndMinimap(Game &game, float panelY) {
    float radius = 110.f;
    float mCx = cfg::WIDTH / 2.f, mCy = panelY + 220.f;
    float scale = radius / game.MAP_RADIUS;

    sf::CircleShape bg(radius);
    bg.setOrigin({radius, radius});
    bg.setPosition({mCx, mCy});
    bg.setFillColor(sf::Color(230, 230, 230));
    bg.setOutlineColor(sf::Color(40, 40, 40));
    bg.setOutlineThickness(2.f);
    window.draw(bg);

    for (const auto &p : game.players) {
        if (p->isDead || p->territoryPoints.size() <= 2) continue;
        sf::ConvexShape poly(p->territoryPoints.size());
        for (size_t i = 0; i < p->territoryPoints.size(); ++i) {
            poly.setPoint(i, sf::Vector2f(p->territoryPoints[i].x * scale + mCx, p->territoryPoints[i].y * scale + mCy));
        }
        poly.setFillColor(p->territoryColor);
        window.draw(poly);
    }

    if (game.mainPlayer->isDead && game.finalTerritoryPoints.size() > 2) {
        sf::ConvexShape poly(game.finalTerritoryPoints.size());
        for (size_t i = 0; i < game.finalTerritoryPoints.size(); ++i) {
            poly.setPoint(i, sf::Vector2f(game.finalTerritoryPoints[i].x * scale + mCx, game.finalTerritoryPoints[i].y * scale + mCy));
        }
        poly.setFillColor(game.finalTerritoryColor);
        window.draw(poly);
    }
}

void PlayState::drawOkButton(float panelY, sf::Vector2i mouse) {
    okBtn.position = {okBtn.position.x, panelY + 355.f};
    bool hover = okBtn.contains({(float)mouse.x, (float)mouse.y});
    drawRoundedButton(window, okBtn, "OK", hover, fonts.ui);
}