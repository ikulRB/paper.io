#include "game/game.hpp"
#include <cmath>
#include <algorithm>

static const std::vector<std::string> BOT_NAMES = {
    "Bot Alpha", "Bot Beta", "Bot Gamma", "Bot Delta", "Bot Epsilon"
};

static const float SELF_TRAIL_SAFE = 15.f;
static const float OTHER_TRAIL_SAFE = 2.f;
static const float COLLISION_DISTANCE = 5.0f;
static const int MIN_TRAIL_FOR_COLLISION = 6;

Game::Game(sf::RenderTarget &target, const std::string &name, sf::Color color, int numBots, const Fonts &f)
    : screen(target), camera(cfg::WIDTH, cfg::HEIGHT),
      boardRenderer(cfg::VOLUME_SHIFTY), playerRenderer(f.name, cfg::VOLUME_SHIFTY),
      minimapRenderer(cfg::MINI_RADIUS, cfg::MAP_RADIUS),
      leaderboard(f.leaderboard, cfg::WIDTH),
      fonts(f) 
{
    TOTAL_MAP_AREA = 3.14159265f * std::pow(MAP_RADIUS - cfg::BOUNDARY_MARGIN, 2);

    players.push_back(std::make_unique<Player>(name, color, MAP_RADIUS));
    mainPlayer = players[0].get();

    std::vector<sf::Color> botColors = {
        sf::Color(220, 50, 50), sf::Color(50, 50, 220), sf::Color(220, 180, 50),
        sf::Color(180, 50, 220), sf::Color(0, 206, 209), sf::Color(255, 140, 0),
        sf::Color(255, 105, 180), sf::Color(124, 252, 0),
    };
    spawnBots(numBots, botColors);

    finalTerritoryColor = mainPlayer->territoryColor;
}

void Game::spawnBots(int count, const std::vector<sf::Color> &palette) {
    for (int i = 0; i < count; ++i) {
        sf::Color color = palette[i % palette.size()];
        std::string name = BOT_NAMES[i % BOT_NAMES.size()];
        players.push_back(std::make_unique<Player>(name, color, MAP_RADIUS, std::make_unique<BotController>()));
    }
}

bool Game::update() {
    particles.update();

    if (mainPlayer->isDead) {
        result = "lose";
        for (auto &p : players) {
            if (!p->isDead) {
                applyControl(*p);
                movePlayer(*p);
            }
        }
        resolveCollisions();
        return false;
    }

    for (auto &p : players) {
        if (!p->isDead) {
            applyControl(*p);
            movePlayer(*p);
        }
    }
    resolveCollisions();

    if (checkVictory()) {
        result = "win";
        return false;
    }
    return true;
}

bool Game::checkVictory() {
    if (mainPlayer->isDead) return false;
    if (mainPlayer->areaPercentage >= winPercent) return true;
    int othersAlive = 0;
    for (const auto &p : players) {
        if (p.get() != mainPlayer && !p->isDead) othersAlive++;
    }
    return othersAlive == 0;
}

void Game::applyControl(Player &p) {
    if (!p.controller) return;
    int steer = p.controller->getSteer(p, *this);
    if (steer < 0) p.angle -= deltaAngle;
    else if (steer > 0) p.angle += deltaAngle;
}

void Game::movePlayer(Player &p) {
    Point head = p.getHead();
    Point newHead = clampToMap(p, head);
    
    bool inBase = false;
    if (!p.basePolygon.empty()) {
        sf::Vector2f pt(newHead.x, newHead.y);
        bool inside = false;
        const auto &ext = p.basePolygon.exterior;
        for (size_t i = 0, j = ext.size() - 1; i < ext.size(); j = i++) {
            if (((ext[i].y > pt.y) != (ext[j].y > pt.y)) &&
                (pt.x < (ext[j].x - ext[i].x) * (pt.y - ext[i].y) / (ext[j].y - ext[i].y) + ext[i].x)) {
                inside = !inside;
            }
        }
        inBase = inside;
    }

    if (p.inBase) {
        if (inBase) p.walkInBase(newHead);
        else p.enterTrail(head, newHead);
    } else {
        p.points.push_back(newHead);
        if (inBase && p.points.size() > 5) closeTrail(p, newHead);
    }

    p.refreshTerritory();
    p.areaPercentage = std::min(100.0f, (p.basePolygon.area() / TOTAL_MAP_AREA) * 100.f);
}

Point Game::clampToMap(Player &p, Point head) {
    float nextX = head.x + std::cos(p.angle) * p.speed;
    float nextY = head.y + std::sin(p.angle) * p.speed;

    if (std::hypot(nextX, nextY) < MAP_RADIUS - cfg::BOUNDARY_MARGIN) return { nextX, nextY };

    float boundaryAngle = std::atan2(head.y, head.x);
    float angleDiff = std::fmod(p.angle - boundaryAngle + 3.14159265f, 6.2831853f) - 3.14159265f;
    
    if (std::cos(p.angle - boundaryAngle) > 0) {
        if (angleDiff > 0) p.angle = boundaryAngle + 3.14159265f / 2.f;
        else p.angle = boundaryAngle - 3.14159265f / 2.f;
    }
    return { head.x + std::cos(p.angle) * p.speed, head.y + std::sin(p.angle) * p.speed };
}

void Game::closeTrail(Player &p, Point newHead) {
    p.inBase = true;
    p.basePolygon = mergeTrailIntoBase(p.basePolygon, p.points);

    for (auto &victim : players) {
        if (victim.get() == &p || victim->isDead || victim->basePolygon.empty()) continue;
        auto resultPoly = carveOut(p.basePolygon, victim->basePolygon);
        p.basePolygon = resultPoly.first;
        victim->basePolygon = resultPoly.second;
        if (victim->basePolygon.empty()) victim->territoryPoints.clear();
        else victim->refreshTerritory();
        
        victim->areaPercentage = std::min(100.0f, (victim->basePolygon.area() / TOTAL_MAP_AREA) * 100.f);
    }

    p.baseTrailPoints = { newHead };
    p.points = { newHead };

    p.refreshTerritory();
    p.areaPercentage = std::min(100.0f, (p.basePolygon.area() / TOTAL_MAP_AREA) * 100.f);
}

void Game::resolveCollisions() {
    for (auto &predator : players) {
        if (predator->isDead) continue;
        Point predatorHead = predator->getHead();
        for (auto &victim : players) {
            if (victim->isDead || victim->inBase || victim->points.size() <= MIN_TRAIL_FOR_COLLISION) continue;
            checkCollision(*predator, *victim, predatorHead);
        }
    }
}

void Game::checkCollision(Player &predator, Player &victim, Point predatorHead) {
    float safe = (&predator == &victim) ? SELF_TRAIL_SAFE : OTHER_TRAIL_SAFE;
    size_t count = victim.points.size();
    if (count <= safe) return;

    size_t limit = count - (size_t)safe;
    for (size_t i = 0; i + 1 < limit; ++i) {
        Point a = victim.points[i], b = victim.points[i + 1];
        float dx = b.x - a.x, dy = b.y - a.y;
        float l2 = dx * dx + dy * dy;
        if (l2 == 0.f) continue;
        float t = std::max(0.f, std::min(1.f, ((predatorHead.x - a.x) * dx + (predatorHead.y - a.y) * dy) / l2));
        float projX = a.x + t * dx, projY = a.y + t * dy;
        if (std::hypot(predatorHead.x - projX, predatorHead.y - projY) < COLLISION_DISTANCE) {
            killPlayer(victim);
            return;
        }
    }
}

void Game::killPlayer(Player &victim) {
    victim.isDead = true;
    Points sources;
    sources.push_back(victim.getHead());
    sources.insert(sources.end(), victim.points.begin(), victim.points.end());
    sources.insert(sources.end(), victim.territoryPoints.begin(), victim.territoryPoints.end());
    
    particles.spawnFor(victim, sources, 2);

    if (&victim == mainPlayer) {
        victim.lastHead = victim.getHead();
        finalTerritoryPoints = victim.territoryPoints;
        victim.territoryPoints.clear();
        victim.basePolygon = Poly();
        victim.baseTrailPoints.clear();
        victim.points.clear();
    }
}

void Game::draw() {
    camera.follow(mainPlayer->getHead());
    boardRenderer.drawBackground(screen, camera, MAP_RADIUS);

    for (const auto &p : players) boardRenderer.drawTerritory(screen, camera, *p);
    for (const auto &p : players) {
        boardRenderer.drawTrail(screen, camera, *p);
        boardRenderer.drawTerritory(screen, camera, *p);
    }

    particles.draw(screen, camera);
    playerRenderer.drawPlayers(screen, camera, players, mainPlayer);

    if (!mainPlayer->isDead) minimapRenderer.draw(screen, players);
    leaderboard.draw(screen, players);
}