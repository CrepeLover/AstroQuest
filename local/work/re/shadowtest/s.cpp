// Checks Scenes::Adjust's near cascade split on the title's own scene files.
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <regex>
#include "core/known_title_scenes.h"
using namespace Core::KnownTitle::Scenes;
int main() {
    const std::string dir = "C:/Games/AstroQuest/games/CUSA12392/data/multi_platformer/spx/";
    Detail d; d.lod_scale = 2.0; d.shadow_map_min = 2048; d.spot_shadow_map_min = 1024; d.near_split = 6.0;
    int changed = 0, files = 0;
    for (auto& e : std::filesystem::directory_iterator(dir)) {
        const std::string name = e.path().filename().string();
        std::ifstream f(e.path(), std::ios::binary);
        std::string t((std::istreambuf_iterator<char>(f)), {});
        std::string a = Adjust(t, d, name == "default_hmd.spx", name);
        ++files;
        std::smatch m; std::string far = "-", r0 = "-", r1 = "-";
        if (std::regex_search(t, m, std::regex("<DirShadowFar>([^<]*)"))) far = m[1];
        if (std::regex_search(t, m, std::regex("<DirShadowSplitLogRatio>([^<]*)"))) r0 = m[1];
        if (std::regex_search(a, m, std::regex("<DirShadowSplitLogRatio>([^<]*)"))) r1 = m[1];
        if (r0 != r1) {
            ++changed;
            const double fr = std::atof(far.c_str());
            std::printf("%-34s far %-6s ratio %-6s -> %-6s near cascade %.2f -> %.2f m\n", name.c_str(), far.c_str(), r0.c_str(), r1.c_str(),
                        NearCascadeEnd(fr, r0 == "-" ? 0.2 : std::atof(r0.c_str())), NearCascadeEnd(fr, std::atof(r1.c_str())));
        }
        // the result must still be well formed around the inserted element
        if (a.find("<DirShadowSplitLogRatio>") != std::string::npos && a.find("</DirShadowSplitLogRatio>") == std::string::npos) std::printf("BROKEN %s\n", name.c_str());
    }
    std::printf("%d of %d files get a new ratio\n", changed, files);
    for (double fr : {10.0, 15.0, 20.0, 25.0, 40.0, 50.0}) std::printf("far %4.0f: title %.2f m\n", fr, NearCascadeEnd(fr, 0.2));
    // one file shown whole where an element was added
    std::ifstream f(dir + "canyon_highfog_01.spx", std::ios::binary);
    std::string t((std::istreambuf_iterator<char>(f)), {});
    std::string a = Adjust(t, d, false, "canyon_highfog_01.spx");
    std::printf("---- canyon_highfog_01.spx head:\n%s\n", a.substr(0, 260).c_str());
}
