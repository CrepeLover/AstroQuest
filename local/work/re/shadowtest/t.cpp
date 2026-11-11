// Checks Builds::SunShadowChanges against the game's own eboot (image = file from 0x4000).
#include <cstdio>
#include <fstream>
#include <iterator>
#include <vector>
#include "core/known_title_builds.h"
using namespace Core::KnownTitle::Builds;
int main(int argc, char** argv) {
    std::ifstream f(argv[1], std::ios::binary);
    std::vector<u8> file((std::istreambuf_iterator<char>(f)), {});
    for (u32 size : {4096u, 8192u, 2048u}) {
        std::vector<u8> image(file.begin() + 0x4000, file.end());
        image.resize(0x165c000 + 0x1a0fe98);
        const Build* b = Recognise(image);
        if (!b) { std::printf("build: none\n"); return 1; }
        auto c = SunShadowChanges(*b, size);
        std::printf("size %u (%s): %zu changes, unexpected %s, pool %u MB\n", size, b->name, c.size(),
                    FirstUnexpected(image, c) ? "YES" : "none", ShadowPoolFor(size) >> 20);
        if (c.empty()) continue;
        const Change* u = Apply(image, c);
        std::printf("  applied: %s\n", u ? "no" : "yes");
        for (auto& x : c) { u64 v = 0; std::memcpy(&v, image.data() + x.at, x.bytes); std::printf("  %#llx now %#llx\n", (unsigned long long)x.at, (unsigned long long)v); }
    }
    std::printf("1.04 changes: %zu\n", SunShadowChanges(Known[1], 8192).size());
    return 0;
}
