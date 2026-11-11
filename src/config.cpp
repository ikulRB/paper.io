#include "config.hpp"
#include <iostream>

Fonts initFonts(const std::string &dir) {
    Fonts f;
    std::string path = dir + "V5 prophit non.ttf";
    
    if (!f.title.openFromFile(path)) std::cerr << "Failed to load " << path << "std::endl";
    if (!f.ui.openFromFile(path)) std::cerr << "Failed to load " << path << "std::endl";
    if (!f.vs.openFromFile(path)) std::cerr << "Failed to load " << path << "std::endl";
    if (!f.name.openFromFile(path)) std::cerr << "Failed to load " << path << "std::endl";
    if (!f.leaderboard.openFromFile(path)) std::cerr << "Failed to load " << path << "std::endl";
    if (!f.gameover.openFromFile(path)) std::cerr << "Failed to load " << path << "std::endl";
    return f;
}