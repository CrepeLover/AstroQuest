// SPDX-FileCopyrightText: Copyright 2026 shadPS4 Emulator Project
// SPDX-License-Identifier: GPL-2.0-or-later

#include <cstdlib>
#include <cstring>

#include "common/logging/log.h"
#include "core/memory.h"
#include "video_core/renderer_vulkan/vk_instance.h"
#include "video_core/renderer_vulkan/vk_occlusion.h"
#include "video_core/renderer_vulkan/vk_scheduler.h"

namespace Vulkan {

namespace {

/// Slots are used in turn; a slot comes round again only after this many draws have been
/// counted (~100 a frame in Astro Bot, so well over a second), long after its answer is read.
constexpr u32 NumSlots = 16384;
/// Draws counted for one query at most (Astro Bot's have one each).
constexpr u32 MaxDrawsPerQuery = 64;
/// The counter's bit that says the render backend has written it.
constexpr u64 ValidBit = 0x8000000000000000ULL;

void WriteGuest(VAddr address, u64 value) {
    auto* memory = Core::Memory::Instance();
    void* at = reinterpret_cast<void*>(address);
    if (!memory->TryWriteBacking(at, &value, sizeof(value))) {
        std::memcpy(at, &value, sizeof(value));
    }
}

} // namespace

bool OcclusionQueries::Enabled() {
    static const bool enabled = [] {
        const char* value = std::getenv("SHADPS4_OCCLUSION_QUERIES");
        return value == nullptr || value[0] != '0';
    }();
    return enabled;
}

OcclusionQueries::OcclusionQueries(const Instance& instance_, Scheduler& scheduler_)
    : instance{instance_}, scheduler{scheduler_} {
    const auto features = instance.GetPhysicalDevice()
                              .getFeatures2<vk::PhysicalDeviceFeatures2,
                                            vk::PhysicalDeviceVulkan12Features>();
    const bool host_reset = features.get<vk::PhysicalDeviceVulkan12Features>().hostQueryReset;
    const bool precise =
        features.get<vk::PhysicalDeviceFeatures2>().features.occlusionQueryPrecise;
    if (!host_reset) {
        LOG_WARNING(Render_Vulkan, "Occlusion queries: the GPU cannot reset queries from the "
                                   "host here, so their counts stay made up");
        return;
    }
    const auto device = instance.GetDevice();
    auto [result, created] = device.createQueryPool({
        .queryType = vk::QueryType::eOcclusion,
        .queryCount = NumSlots,
    });
    if (result != vk::Result::eSuccess) {
        LOG_WARNING(Render_Vulkan, "Occlusion queries: no query pool ({}), counts stay made up",
                    vk::to_string(result));
        return;
    }
    pool = created;
    device.resetQueryPool(pool, 0, NumSlots);
    if (precise) {
        control = vk::QueryControlFlagBits::ePrecise;
    }
    reported = std::chrono::steady_clock::now();
    LOG_INFO(Render_Vulkan,
             "Occlusion queries: answered with the GPU's own counts of the samples that pass "
             "({}; SHADPS4_OCCLUSION_QUERIES=0 makes them up)",
             precise ? "exact" : "not necessarily exact");
}

OcclusionQueries::~OcclusionQueries() {
    if (pool) {
        instance.GetDevice().destroyQueryPool(pool);
    }
}

void OcclusionQueries::Dump(VAddr address, u32 num_pairs) {
    if (open && address == open->address + 8) {
        Close();
        Report();
        return;
    }
    if (open) {
        // A second query opened before the first closed: the first ends here.
        ++unclosed;
        Close();
    }
    open = Query{.address = address, .num_pairs = num_pairs};
    ++opened;
}

s32 OcclusionQueries::BeginDraw(vk::CommandBuffer cmdbuf) {
    if (!open || !pool) {
        return -1;
    }
    if (open->slots.size() >= MaxDrawsPerQuery) {
        ++too_many_draws;
        return -1;
    }
    const u32 slot = next_slot;
    next_slot = (next_slot + 1) % NumSlots;
    instance.GetDevice().resetQueryPool(pool, slot, 1);
    cmdbuf.beginQuery(pool, slot, control);
    open->slots.push_back(slot);
    ++draws_counted;
    return static_cast<s32>(slot);
}

void OcclusionQueries::EndDraw(vk::CommandBuffer cmdbuf, s32 slot) {
    if (slot >= 0) {
        cmdbuf.endQuery(pool, static_cast<u32>(slot));
    }
}

void OcclusionQueries::Close() {
    Query query = std::move(*open);
    open.reset();
    // A draw the emulator left out would have counted: rather than a sum that is too small (the
    // sun or a model hidden that is not), the query sees everything, as all of them used to.
    const bool complete = query.draws_seen <= query.slots.size();
    if (!complete) {
        ++incomplete;
    }
    scheduler.DeferPriorityOperation([this, complete, query = std::move(query)] {
        const auto device = instance.GetDevice();
        u64 sum = 0;
        bool ok = true;
        for (const u32 slot : query.slots) {
            u64 value = 0;
            const vk::Result result = device.getQueryPoolResults(
                pool, slot, 1, sizeof(value), &value, sizeof(value),
                vk::QueryResultFlagBits::e64 | vk::QueryResultFlagBits::eWait);
            if (result == vk::Result::eSuccess) {
                sum += value;
            } else {
                ok = false;
            }
        }
        if (!ok || !complete) {
            // Seen as all visible, as before, rather than as hidden.
            sum = 0x2FFFFFFULL;
            if (!ok) {
                failed.fetch_add(1, std::memory_order_relaxed);
            }
        }
        for (u32 i = 0; i < query.num_pairs; ++i) {
            const VAddr begin = query.address + VAddr{i} * 16;
            WriteGuest(begin, ValidBit);
            WriteGuest(begin + 8, ValidBit | (i == 0 ? sum : 0));
        }
        answered.fetch_add(1, std::memory_order_relaxed);
        samples.fetch_add(sum, std::memory_order_relaxed);
        if (sum == 0) {
            saw_nothing.fetch_add(1, std::memory_order_relaxed);
        }
    });
}

void OcclusionQueries::Report() {
    const auto now = std::chrono::steady_clock::now();
    if (now - reported < std::chrono::seconds{10}) {
        return;
    }
    reported = now;
    const u64 n = answered.exchange(0, std::memory_order_relaxed);
    const u64 none = saw_nothing.exchange(0, std::memory_order_relaxed);
    const u64 total = samples.exchange(0, std::memory_order_relaxed);
    const u64 bad = failed.exchange(0, std::memory_order_relaxed);
    LOG_INFO(Render_Vulkan,
             "Occlusion queries: {} asked in the last 10 s, {} answered from {} counted draws; "
             "{} saw nothing, the others {:.0f} samples on average; {} left open, {} draws past "
             "the limit, {} with a draw left out (seen as visible), {} unreadable",
             opened, n, draws_counted, none, n > none ? double(total) / double(n - none) : 0.0,
             unclosed, too_many_draws, incomplete, bad);
    opened = unclosed = too_many_draws = draws_counted = incomplete = 0;
}

} // namespace Vulkan
