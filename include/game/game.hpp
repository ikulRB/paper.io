#pragma once
#include <SFML/Graphics.hpp>
#include <vector>
#include <memory>
#include "game/player.hpp"
#include "game/camera.hpp"
#include "rendering/particles.hpp"
#include "rendering/board_renderer.hpp"
#include "rendering/player_renderer.hpp"
#include "rendering/minimap_renderer.hpp"
#include "game/leaderboard.hpp"
#include "config.hpp"

class Game {
public:
    Game(sf::RenderTarget &screen, const std::string &name, sf::Color color,
         int numBots, const Fonts &fonts);

    bool update();
    void draw();

    float MAP_RADIUS = cfg::MAP_RADIUS;
    float MINI_RADIUS = cfg::MINI_RADIUS;
    float VOLUME_SHIFTY = cfg::VOLUME_SHIFTY;
    float deltaAngle = cfg::DELTA_ANGLE;
    float winPercent = cfg::WIN_PERCENT;
    float TOTAL_MAP_AREA;

    std::vector<std::unique_ptr<Player>> players;
    Player *mainPlayer = nullptr;
    std::string result;

    Points finalTerritoryPoints;
    sf::Color finalTerritoryColor;

    ParticleManager particles;
    Camera camera;
    BoardRenderer boardRenderer;
    PlayerRenderer playerRenderer;
    MinimapRenderer minimapRenderer;
    Leaderboard leaderboard;

    sf::RenderTarget &screen;

private:
    void spawnBots(int count, const std::vector<sf::Color> &palette);
    void applyControl(Player &p);
    void movePlayer(Player &p);
    Point clampToMap(Player &p, Point head);
    void closeTrail(Player &p, Point newHead);
    void resolveCollisions();
    void checkCollision(Player &predator, Player &victim, Point predatorHead);
    void killPlayer(Player &victim);
    bool checkVictory();

    Fonts fonts;
};