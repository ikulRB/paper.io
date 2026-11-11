#include <SFML/Graphics.hpp>
#include "config.hpp"
#include "ui/menu.hpp"
#include "ui/pause.hpp"
#include "states/play_state.hpp"

int main() {
    sf::RenderWindow window(sf::VideoMode({cfg::WIDTH, cfg::HEIGHT}), cfg::CAPTION);
    window.setFramerateLimit(cfg::FPS);

    Fonts fonts = initFonts("assets/fonts/");

    Menu menu(window, fonts);
    PauseMenu pauseMenu(window, fonts);
    PlayState playState(window, fonts, pauseMenu);

    std::string savedName = "Player";
    sf::Color savedColor = cfg::AVAILABLE_COLORS[0];

    while (window.isOpen()) {
        auto res = menu.run(savedName, savedColor);
        if (!window.isOpen()) break;
        savedName = res.first;
        savedColor = res.second;
        playState.run(savedName, savedColor);
    }

    return 0;
}