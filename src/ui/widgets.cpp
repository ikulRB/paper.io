#include "ui/widgets.hpp"
#include <cmath>
#include <cstdint>

void drawRoundedButton(sf::RenderTarget &target, const sf::FloatRect &rect, const std::string &text, bool isHovered, const sf::Font &font) {
    sf::RectangleShape r(rect.size);
    r.setPosition(rect.position);
    r.setFillColor(isHovered ? cfg::COLOR_BTN_HOVER : cfg::COLOR_BTN);
    target.draw(r);

    sf::RectangleShape border(rect.size);
    border.setPosition(rect.position);
    border.setFillColor(sf::Color::Transparent);
    border.setOutlineColor(sf::Color::Black);
    border.setOutlineThickness(2.f);
    target.draw(border);

    sf::Text t(font, text, 20);
    t.setFillColor(sf::Color::White);
    auto b = t.getLocalBounds();
    t.setPosition({
        rect.position.x + rect.size.x / 2.f - b.size.x / 2.f - b.position.x, 
        rect.position.y + rect.size.y / 2.f - b.size.y / 2.f - b.position.y
    });
    target.draw(t);
}

void drawGameButton(sf::RenderTarget &target, const std::string &text, const sf::FloatRect &rect, bool isHovered, const std::string &type, const sf::Font &font) {
    drawRoundedButton(target, rect, text, isHovered, font);
}

void drawTextInput(sf::RenderTarget &target, const sf::FloatRect &rect, const std::string &text, bool isActive, const sf::Font &font, bool cursorVisible, const std::string &placeholder, float errorAlpha) {
    sf::RectangleShape bg(rect.size);
    bg.setPosition(rect.position);
    bg.setFillColor(isActive ? sf::Color::White : sf::Color(230, 230, 230));
    target.draw(bg);

    if (errorAlpha > 0.f) {
        sf::RectangleShape err(rect.size);
        err.setPosition(rect.position);
        err.setFillColor(sf::Color(255, 100, 100, static_cast<std::uint8_t>(errorAlpha)));
        target.draw(err);
    }

    sf::RectangleShape border(rect.size);
    border.setPosition(rect.position);
    border.setFillColor(sf::Color::Transparent);
    border.setOutlineColor(isActive ? cfg::COLOR_BTN : sf::Color(150, 150, 150));
    border.setOutlineThickness(2.f);
    target.draw(border);

    float midY = rect.position.y + rect.size.y / 2.f;
    if (text.empty()) {
        sf::Text t(font, placeholder, 20);
        t.setFillColor(cfg::COLOR_PLACEHOLDER);
        auto b = t.getLocalBounds();
        t.setPosition({rect.position.x + 10.f, midY - b.size.y / 2.f - b.position.y});
        target.draw(t);
    } else {
        sf::Text t(font, text, 20);
        t.setFillColor(cfg::COLOR_TEXT);
        auto b = t.getLocalBounds();
        t.setPosition({rect.position.x + 10.f, midY - b.size.y / 2.f - b.position.y});
        target.draw(t);

        if (isActive && cursorVisible) {
            sf::RectangleShape cursor({2.f, 24.f});
            cursor.setPosition({rect.position.x + 12.f + b.size.x, midY - 12.f});
            cursor.setFillColor(cfg::COLOR_TEXT);
            target.draw(cursor);
        }
    }
}

ColorPicker::ColorPicker(float cX, float tY, const std::vector<sf::Color> &c) : centerX(cX), topY(tY), colors(c) {}

sf::Vector2f ColorPicker::getCenter(int i) {
    float cx = centerX - 100.f + (i % cols) * stepX;
    float cy = topY + (i / cols) * stepY;
    return { cx, cy };
}

int ColorPicker::hitTest(float mx, float my) {
    for (size_t i = 0; i < colors.size(); ++i) {
        auto c = getCenter(i);
        if (std::hypot(mx - c.x, my - c.y) < radius) return (int)i;
    }
    return -1;
}

void ColorPicker::draw(sf::RenderTarget &target) {
    for (size_t i = 0; i < colors.size(); ++i) {
        auto c = getCenter(i);
        sf::CircleShape circle(radius);
        circle.setOrigin({radius, radius});
        circle.setPosition(c);
        circle.setFillColor(colors[i]);
        target.draw(circle);

        if ((int)i == selectedIdx) {
            sf::CircleShape border(radius + 3.f);
            border.setOrigin({radius + 3.f, radius + 3.f});
            border.setPosition(c);
            border.setFillColor(sf::Color::Transparent);
            border.setOutlineColor(sf::Color::Black);
            border.setOutlineThickness(3.f);
            target.draw(border);
        }
    }
}