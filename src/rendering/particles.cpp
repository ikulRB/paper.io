#include "rendering/particles.hpp"
#include "game/player.hpp"
#include <random>
#include <cmath>
#include <algorithm>
#include <cstdint>

static std::mt19937 &rng() {
    static std::mt19937 r(std::random_device{}());
    return r;
}

void ParticlePool::spawn(const Points &source, int perPoint) {
    std::uniform_real_distribution<float> ang(0.f, 6.2831853f);
    std::uniform_real_distribution<float> spd(0.8f, 4.f);
    std::uniform_int_distribution<int> rad(2, 6);
    for (const auto &pt : source) {
        for (int i = 0; i < perPoint; ++i) {
            float a = ang(rng());
            float s = spd(rng());
            int r = rad(rng());
            items.push_back({ { pt.x, pt.y }, { std::cos(a) * s, std::sin(a) * s }, (float)r, 255.f });
        }
    }
}

void ParticlePool::update() {
    for (auto &p : items) {
        p.pos += p.vel;
        p.alpha = std::max(0.f, p.alpha - 2.f);
    }
    items.erase(std::remove_if(items.begin(), items.end(), [](const Particle &p) {
        return p.alpha <= 0.f;
    }), items.end());
}

void ParticlePool::draw(sf::RenderTarget &target, const Camera &cam) {
    sf::CircleShape shape(1.f);
    for (const auto &p : items) {
        shape.setRadius(p.radius);
        shape.setOrigin({p.radius, p.radius});
        shape.setPosition(cam.toScreen(p.pos));
        auto c = color;
        c.a = static_cast<std::uint8_t>(p.alpha);
        shape.setFillColor(c);
        target.draw(shape);
    }
}

ParticlePool &ParticleManager::forPlayer(const Player &p) {
    auto it = pools.find(&p);
    if (it == pools.end()) it = pools.emplace(&p, ParticlePool(p.color)).first;
    return it->second;
}

void ParticleManager::spawnFor(const Player &p, const Points &source, int perPoint) {
    forPlayer(p).spawn(source, perPoint);
}

void ParticleManager::update() {
    for (auto &[k, v] : pools) v.update();
}

void ParticleManager::draw(sf::RenderTarget &t, const Camera &c) {
    for (auto &[k, v] : pools) v.draw(t, c);
}