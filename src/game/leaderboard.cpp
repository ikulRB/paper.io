#include "game/leaderboard.hpp"
#include <algorithm>
#include <string>
#include <cstdint>

Leaderboard::Leaderboard(const sf::Font &f, unsigned screenW) : font(f), startX((float)screenW - 240.f) {}

void Leaderboard::draw(sf::RenderTarget &t, const std::vector<std::unique_ptr<Player>> &players) {
    std::vector<const Player *> alive;
    for (const auto &p : players) {
        if (!p->isDead) alive.push_back(p.get());
    }
    std::sort(alive.begin(), alive.end(), [](const Player *a, const Player *b) {
        return a->areaPercentage > b->areaPercentage;
    });
    for (size_t i = 0; i < alive.size(); ++i) {
        drawRow(t, *alive[i], startY + i * spacing);
    }
}

void Leaderboard::drawRow(sf::RenderTarget &t, const Player &p, float y) {
    sf::RectangleShape bg({ barWidth, barHeight });
    bg.setPosition({startX, y});
    bg.setFillColor(sf::Color(200, 200, 200));
    t.draw(bg);

    float fw = barWidth * (p.areaPercentage / 100.f);
    if (fw == 0.f && p.areaPercentage > 0.f) fw = 2.f;
    if (fw > 0.f) {
        sf::RectangleShape fill({ fw, barHeight - 4 });
        fill.setPosition({startX, y + 4});
        fill.setFillColor(sf::Color(
            static_cast<std::uint8_t>(p.color.r * 0.7f), 
            static_cast<std::uint8_t>(p.color.g * 0.7f), 
            static_cast<std::uint8_t>(p.color.b * 0.7f)
        ));
        t.draw(fill);
        
        sf::RectangleShape top({ fw, barHeight - 4 });
        top.setPosition({startX, y});
        top.setFillColor(p.color);
        t.draw(top);
    }

    sf::RectangleShape border({ barWidth, barHeight });
    border.setPosition({startX, y});
    border.setFillColor(sf::Color::Transparent);
    border.setOutlineColor(sf::Color(40, 40, 40));
    border.setOutlineThickness(2.f);
    t.draw(border);

    std::string textStr = p.name + ": " + std::to_string(p.areaPercentage).substr(0, 4) + "%";
    
    sf::Text txt(font, textStr, 16);
    txt.setFillColor(sf::Color::Black);
    txt.setPosition({startX + 8, y + barHeight / 2.f - txt.getLocalBounds().size.y - 2});
    t.draw(txt);
}