#pragma once
#include <memory>
#include <random>
#include "game/geometry.hpp"

class Player;
class Game;

class Controller {
public:
    virtual ~Controller() = default;
    virtual int getSteer(Player &p, Game &g) = 0; // -1 / 0 / +1
};

class HumanController : public Controller {
public:
    int getSteer(Player &p, Game &g) override;
};

class BotController : public Controller {
public:
    BotController();
    int getSteer(Player &p, Game &g) override;

private:
    std::mt19937 rng;
    int wander = 0;
    int steerAvoidBoundary(Player &p, Game &g, Point head);
    int steerOutsideBase(Player &p, Game &g, Point head);
    int steerInsideBase(Player &p, Game &g, Point head);
    int steerAttackTrail(Player &p, Game &g, Point head, bool &found);
    int steerTowards(Player &p, Point target);
    int avoidSelfTrail(Player &p);
    int wanderStep();
};