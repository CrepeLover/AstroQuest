// SPDX-FileCopyrightText: Copyright 2026 shadPS4 Emulator Project
// SPDX-License-Identifier: GPL-2.0-or-later

#pragma once

#include <atomic>
#include <chrono>
#include <optional>

#include <boost/container/small_vector.hpp>

#include "common/types.h"
#include "video_core/renderer_vulkan/vk_common.h"

namespace Vulkan {

class Instance;
class Scheduler;

/// The title's occlusion queries, answered with what the GPU counts.
///
/// A title asks the console's GPU how many samples of some draws pass the depth test by having
/// every render backend dump its pass counter (ZPASS_DONE) to memory before the draws and again
/// 8 bytes on after them. Astro Bot does this to judge how much of the sun its glare should show
/// and in the depth pass of each eye. Without this every query saw ~50 million samples, so the
/// sun's glare was drawn in full through walls.
///
/// Every draw made while a query is open is counted by a Vulkan occlusion query of its own. Once
/// the GPU has done them, their sum is written for the first render backend and 0 for the
/// others, each with the counter's valid bit, as the console would have.
///
/// SHADPS4_OCCLUSION_QUERIES=0 makes the counts up again.
class OcclusionQueries {
public:
    explicit OcclusionQueries(const Instance& instance, Scheduler& scheduler);
    ~OcclusionQueries();

    OcclusionQueries(const OcclusionQueries&) = delete;
    OcclusionQueries& operator=(const OcclusionQueries&) = delete;

    /// Whether the counts are to be the GPU's own (SHADPS4_OCCLUSION_QUERIES).
    static bool Enabled();

    /// Whether the GPU can count here (a query pool and resetting queries from the host).
    [[nodiscard]] bool Ready() const {
        return static_cast<bool>(pool);
    }

    /// A ZPASS_DONE dump to address for num_pairs render backends: the first of a pair opens a
    /// query, the one 8 bytes on closes it.
    void Dump(VAddr address, u32 num_pairs);

    /// Whether a query is open: draws are then counted and must not be left out.
    [[nodiscard]] bool IsOpen() const {
        return open.has_value();
    }

    /// A draw has come (before anything decides whether it is made): one the open query expects
    /// to count.
    void NoteDraw() {
        if (open) {
            ++open->draws_seen;
        }
    }

    /// Around a draw while a query is open (inside its rendering). The slot counted in, or -1.
    s32 BeginDraw(vk::CommandBuffer cmdbuf);
    void EndDraw(vk::CommandBuffer cmdbuf, s32 slot);

private:
    struct Query {
        VAddr address{};
        u32 num_pairs{};
        u32 draws_seen{};
        boost::container::small_vector<u32, 4> slots;
    };

    /// Ends the open query: its counts are read and written once the GPU has done its draws.
    void Close();
    void Report();

    const Instance& instance;
    Scheduler& scheduler;
    vk::QueryPool pool{};
    vk::QueryControlFlags control{};
    u32 next_slot{};
    std::optional<Query> open;

    // Over the last report's 10 s (the answers come in on the scheduler's other thread).
    u64 opened{};
    u64 unclosed{};
    u64 too_many_draws{};
    u64 draws_counted{};
    u64 incomplete{};
    std::atomic<u64> answered{};
    std::atomic<u64> saw_nothing{};
    std::atomic<u64> samples{};
    std::atomic<u64> failed{};
    std::chrono::steady_clock::time_point reported{};
};

} // namespace Vulkan
