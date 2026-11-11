#include "rendering/player_renderer.hpp"
#include <cmath>
#include <cstdint>

static const std::vector<sf::Vector2f> HEAD_VERTS = { { 18, 0 }, { -12, -12 }, { -6, 0 }, { -12, 12 } };

void PlayerRenderer::drawPlayers(sf::RenderTarget &t, const Camera &cam, const std::vector<std::unique_ptr<Player>> &players, const Player *mainPlayer) {
    float time = 0.f;
    for (const auto &p : players) {
        if (p->isDead) continue;
        drawShip(t, cam, *p, p.get() == mainPlayer, time);
        drawName(t, cam, *p, p.get() == mainPlayer);
    }
}

void PlayerRenderer::drawShip(sf::RenderTarget &t, const Camera &cam, const Player &p, bool leader, float time) {
    auto head = const_cast<Player &>(p).getHead();
    auto s = cam.toScreen(head);

    std::vector<sf::Vector2f> base;
    base.reserve(4);
    float c = std::cos(p.angle), sn = std::sin(p.angle);
    for (const auto &v : HEAD_VERTS) {
        float rx = v.x * c - v.y * sn;
        float ry = v.x * sn + v.y * c;
        base.emplace_back(s.x + rx, s.y + ry);
    }

    sf::ConvexShape poly(4);
    auto setShape = [&](sf::Color color, float yOff) {
        for (int i = 0; i < 4; ++i) poly.setPoint(i, { base[i].x, base[i].y + yOff });
        poly.setFillColor(color);
        t.draw(poly);
    };

    if (leader) {
        float pulse = (std::sin(time * 0.005f) + 1.f) / 2.f;
        auto mix = [pulse](sf::Color c1, sf::Color c2, float k) {
            return sf::Color(
                static_cast<std::uint8_t>(c1.r + (c2.r - c1.r) * pulse * k),
                static_cast<std::uint8_t>(c1.g + (c2.g - c1.g) * pulse * k),
                static_cast<std::uint8_t>(c1.b + (c2.b - c1.b) * pulse * k)
            );
        };
        sf::Color light = mix(p.color, sf::Color::White, 0.4f);
        sf::Color dark = sf::Color(
            static_cast<std::uint8_t>(p.color.r * (0.6f + 0.4f * pulse)),
            static_cast<std::uint8_t>(p.color.g * (0.6f + 0.4f * pulse)),
            static_cast<std::uint8_t>(p.color.b * (0.6f + 0.4f * pulse))
        );
        setShape(dark, volumeShift - 2);
        setShape(light, 0);
        poly.setOutlineColor(sf::Color::Black);
        poly.setOutlineThickness(2.f);
        t.draw(poly);
    } else {
        setShape(sf::Color(30, 30, 30), volumeShift - 2);
        setShape(p.color, 0);
        poly.setOutlineColor(sf::Color::Black);
        poly.setOutlineThickness(2.f);
        t.draw(poly);
    }
}

void PlayerRenderer::drawName(sf::RenderTarget &t, const Camera &cam, const Player &p, bool isMain) {
    auto head = const_cast<Player &>(p).getHead();
    auto s = cam.toScreen(head);
    
    sf::Text text(font, p.name, 18);
    text.setFillColor(sf::Color::Black);
    auto b = text.getLocalBounds();
    
    text.setOrigin({b.size.x / 2.f, b.size.y + 20.f});
    if (isMain) {
        auto size = t.getSize();
        text.setPosition({static_cast<float>(size.x) / 2.f, static_cast<float>(size.y) / 2.f - 25.f});
    } else {
        text.setPosition({s.x, s.y - 25.f});
    }
    t.draw(text);
}