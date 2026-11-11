#pragma once
#include <SFML/Graphics.hpp>
#include <vector>
#include <unordered_map>
#include "game/geometry.hpp"
#include "game/camera.hpp"

class Player;

struct Particle {
    sf::Vector2f pos, vel;
    float radius;
    float alpha;
};

class ParticlePool {
public:
    explicit ParticlePool(sf::Color color) : color(color) {}
    void spawn(const Points &source, int perPoint = 2);
    void update();
    void draw(sf::RenderTarget &target, const Camera &cam);
private:
    sf::Color color;
    std::vector<Particle> items;
};

class ParticleManager {
public:
    ParticlePool &forPlayer(const Player &p);
    void spawnFor(const Player &p, const Points &source, int perPoint = 2);
    void update();
    void draw(sf::RenderTarget &target, const Camera &cam);
private:
    std::unordered_map<const Player *, ParticlePool> pools;
};