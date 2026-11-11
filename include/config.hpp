#pragma once
#include <SFML/Graphics.hpp>
#include <vector>
#include <string>

namespace cfg {
    constexpr unsigned WIDTH  = 800;
    constexpr unsigned HEIGHT = 800;
    constexpr const char *CAPTION = "Paper.io";

    inline const sf::Color COLOR_BG           (240, 240, 240);
    inline const sf::Color COLOR_PANEL        (255, 255, 255);
    inline const sf::Color COLOR_TEXT         ( 40,  40,  40);
    inline const sf::Color COLOR_BTN          ( 70, 130, 180);
    inline const sf::Color COLOR_BTN_HOVER    (100, 149, 237);
    inline const sf::Color COLOR_PLACEHOLDER  (160, 160, 160);
    inline const sf::Color COLOR_LINE         ( 80,  80,  80);

    inline const std::vector<sf::Color> AVAILABLE_COLORS = {
        sf::Color( 50, 220,  50), sf::Color(220,  50,  50), sf::Color( 50,  50, 220),
        sf::Color(220, 180,  50), sf::Color(180,  50, 220), sf::Color(255, 140,   0),
        sf::Color(  0, 206, 209), sf::Color(255, 105, 180), sf::Color(128, 128, 128),
        sf::Color(124, 252,   0),
    };

    constexpr int MAX_NAME_LEN = 12;
    constexpr int FPS = 60;

    constexpr float MAP_RADIUS = 2000.f;
    constexpr float MINI_RADIUS = 80.f;
    constexpr float DELTA_ANGLE = 0.06f;
    constexpr float BOUNDARY_MARGIN = 10.f;
    constexpr float WIN_PERCENT = 70.f;
    constexpr int   VOLUME_SHIFTY = 6;
}

struct Fonts {
    sf::Font title, ui, vs, name, leaderboard, gameover;
};

Fonts initFonts(const std::string &dir = "assets/fonts/");