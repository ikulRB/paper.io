#pragma once
#include <SFML/Graphics.hpp>
#include <memory>
#include <string>
#include "game/geometry.hpp"
#include "game/controllers.hpp"

class Player {
public:
    std::string name;
    sf::Color color, territoryColor, volumeColor, trailColor, trailVolumeColor;
    float speed = 3.f;
    bool inBase = true;
    bool isDead = false;
    std::unique_ptr<Controller> controller;

    Point lastHead;
    float angle = 0.f;

    Points points;
    Points baseTrailPoints;
    Points territoryPoints;

    Poly basePolygon;
    float areaPercentage = 0.f;

    Player(const std::string &name, sf::Color color, float mapRadius, std::unique_ptr<Controller> ctrl = nullptr);

    Point getHead();
    void enterTrail(Point head, Point newHead);
    void walkInBase(Point newHead);
    void refreshTerritory();

private:
    static Point spawnPosition(float mapRadius);
    static Points generateStartTerritory(float x, float y);
    static sf::Color darken(sf::Color c, float k);
    static sf::Color lightTrail(sf::Color c);
};