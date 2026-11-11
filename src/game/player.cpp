#include "game/player.hpp"
#include <cmath>
#include <random>
#include <cstdint>

static constexpr int START_TERRITORY_RADIUS = 70;
static constexpr int START_TERRITORY_SEGMENTS = 40;
static constexpr int BASE_TRAIL_MAX = 40;

Player::Player(const std::string &n, sf::Color c, float mapRadius, std::unique_ptr<Controller> ctrl)
    : name(n), color(c), controller(std::move(ctrl)) {
    Point start = spawnPosition(mapRadius);
    lastHead = start;
    points.push_back(start);
    baseTrailPoints.push_back(start);
    territoryPoints = generateStartTerritory(start.x, start.y);
    basePolygon = makeTerritoryPolygon(territoryPoints);

    angle = std::atan2(start.y, start.x) + 3.14159265f;
    territoryColor = color;
    volumeColor = darken(color, 0.6f);
    trailColor = lightTrail(color);
    trailVolumeColor = darken(trailColor, 0.6f);
}

Point Player::spawnPosition(float mapRadius) {
    static std::mt19937 rng(std::random_device{}());
    float maxDist = std::max(0.f, mapRadius - 200.f);
    std::uniform_real_distribution<float> distR(0.f, maxDist);
    std::uniform_real_distribution<float> distA(0.f, 6.2831853f);
    float d = distR(rng), a = distA(rng);
    return { d * std::cos(a), d * std::sin(a) };
}

Points Player::generateStartTerritory(float x, float y) {
    Points out;
    float a = 0.f;
    float step = 3.14159265f / (START_TERRITORY_SEGMENTS / 2);
    for (int i = 0; i < START_TERRITORY_SEGMENTS; ++i) {
        out.emplace_back(std::cos(a) * START_TERRITORY_RADIUS + x, std::sin(a) * START_TERRITORY_RADIUS + y);
        a += step;
    }
    return out;
}

sf::Color Player::darken(sf::Color c, float k) {
    return sf::Color(
        static_cast<std::uint8_t>(c.r * k),
        static_cast<std::uint8_t>(c.g * k),
        static_cast<std::uint8_t>(c.b * k)
    );
}

sf::Color Player::lightTrail(sf::Color c) {
    auto f = [](std::uint8_t v) -> std::uint8_t {
        return static_cast<std::uint8_t>(255 - (2.f / 3.f) * (255 - v));
    };
    return sf::Color(f(c.r), f(c.g), f(c.b));
}

Point Player::getHead() {
    if (isDead) return lastHead;
    if (inBase) {
        if (!baseTrailPoints.empty()) lastHead = baseTrailPoints.back();
        return lastHead;
    }
    if (!points.empty()) lastHead = points.back();
    return lastHead;
}

void Player::enterTrail(Point head, Point newHead) {
    inBase = false;
    points = { head, newHead };
    baseTrailPoints = { newHead };
}

void Player::walkInBase(Point newHead) {
    baseTrailPoints.push_back(newHead);
    if (baseTrailPoints.size() > BASE_TRAIL_MAX) baseTrailPoints.erase(baseTrailPoints.begin());
}

void Player::refreshTerritory() {
    Points p = exteriorPoints(basePolygon);
    if (!p.empty()) territoryPoints = p;
}