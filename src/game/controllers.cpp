#include "game/controllers.hpp"
#include "game/player.hpp"
#include "game/game.hpp"
#include <SFML/Window/Keyboard.hpp>
#include <cmath>
#include <algorithm>

int HumanController::getSteer(Player &p, Game &g) {
    int steer = 0;
    if (sf::Keyboard::isKeyPressed(sf::Keyboard::Key::Left)) steer -= 1;
    if (sf::Keyboard::isKeyPressed(sf::Keyboard::Key::Right)) steer += 1;
    return steer;
}

BotController::BotController() : rng(std::random_device{}()) {}

int BotController::getSteer(Player &p, Game &g) {
    Point head = p.getHead();
    int steer = steerAvoidBoundary(p, g, head);
    if (steer != 0) return steer;
    if (!p.inBase) return steerOutsideBase(p, g, head);
    return steerInsideBase(p, g, head);
}

int BotController::steerAvoidBoundary(Player &p, Game &g, Point head) {
    float dist = std::hypot(head.x, head.y);
    if (dist < g.MAP_RADIUS - 0) return 0;
    float toCenter = std::atan2(-head.y, -head.x);
    float diff = std::fmod(toCenter - p.angle + 3.14159265f, 6.2831853f) - 3.14159265f;
    return diff > 0 ? 1 : -1;
}

int BotController::steerOutsideBase(Player &p, Game &g, Point head) {
    bool found = false;
    int attack = steerAttackTrail(p, g, head, found);
    if (found) return attack;

    if (p.territoryPoints.empty()) return wanderStep();
    auto target = *std::min_element(p.territoryPoints.begin(), p.territoryPoints.end(),
        [&](const Point &a, const Point &b) {
            return std::hypot(a.x - head.x, a.y - head.y) < std::hypot(b.x - head.x, b.y - head.y);
        });
    return steerTowards(p, target);
}

int BotController::steerInsideBase(Player &p, Game &g, Point head) {
    if (p.areaPercentage < 8.0f) return wanderStep();
    if (p.territoryPoints.empty()) return wanderStep();

    float cx = 0, cy = 0;
    for (const auto &pt : p.territoryPoints) {
        cx += pt.x;
        cy += pt.y;
    }
    cx /= p.territoryPoints.size();
    cy /= p.territoryPoints.size();

    float dx = head.x - cx, dy = head.y - cy;
    float d = std::hypot(dx, dy);
    if (d < 0.1f) d = 1.0f;
    Point outward = { head.x + dx / d * 200.f, head.y + dy / d * 200.f };
    return steerTowards(p, outward);
}

int BotController::steerAttackTrail(Player &p, Game &g, Point head, bool &found) {
    found = false;
    Point bestPoint;
    float bestD = 360.f;

    for (const auto &other : g.players) {
        if (other.get() == &p || other->isDead || other->inBase || other->points.size() < 4) continue;
        Point mid = other->points[other->points.size() / 2];
        float d = std::hypot(mid.x - head.x, mid.y - head.y);
        if (d < bestD) {
            bestD = d;
            bestPoint = mid;
            found = true;
        }
    }
    if (!found) return 0;
    return steerTowards(p, bestPoint);
}

int BotController::steerTowards(Player &p, Point target) {
    Point head = p.getHead();
    float desired = std::atan2(target.y - head.y, target.x - head.x);
    float diff = std::fmod(desired - p.angle + 3.14159265f, 6.2831853f) - 3.14159265f;
    if (std::abs(diff) < 0.08f) return avoidSelfTrail(p);
    return diff > 0 ? 1 : -1;
}

int BotController::avoidSelfTrail(Player &p) {
    if (p.inBase || p.points.size() < 6) return 0;
    Point head = p.getHead();
    for (size_t i = 0; i < p.points.size() - 10; ++i) {
        if (std::hypot(p.points[i].x - head.x, p.points[i].y - head.y) < 40.f) {
            return (rng() % 2 == 0) ? -1 : 1;
        }
    }
    return 0;
}

int BotController::wanderStep() {
    std::uniform_real_distribution<float> dist(0.f, 1.f);
    if (dist(rng) < 0.02f) {
        wander = (rng() % 3) - 1;
    }
    return wander;
}