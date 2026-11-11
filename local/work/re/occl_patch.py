# Wires Vulkan::OcclusionQueries (vk_occlusion.cpp/.h) into the AstroQuest shadPS4 source.
import re
import sys

root = sys.argv[1]


def patch(rel, make_pairs):
    p = root + '/' + rel
    s = open(p, encoding='utf-8', newline='').read()
    nl = '\r\n' if '\r\n' in s else '\n'

    def L(*lines):
        return nl.join(lines)

    for old, new in make_pairs(L, s, nl):
        n = s.count(old)
        if n != 1:
            sys.exit(f'{rel}: expected 1 match, found {n}: {old[:80]!r}')
        s = s.replace(old, new)
    open(p, 'w', encoding='utf-8', newline='').write(s)
    print('patched', rel)


patch('src/video_core/renderer_vulkan/vk_rasterizer.h', lambda L, s, nl: [
    ('#include "video_core/renderer_vulkan/vk_gpu_profile.h"',
     L('#include "video_core/renderer_vulkan/vk_gpu_profile.h"',
       '#include "video_core/renderer_vulkan/vk_occlusion.h"')),
    ('    bool InvalidateMemory(VAddr addr, u64 size);',
     L('    bool InvalidateMemory(VAddr addr, u64 size);',
       "    /// A ZPASS_DONE dump of the title's occlusion counters (OcclusionQueries): whether it is",
       "    /// answered with the GPU's own counts rather than made up.",
       '    bool OcclusionDump(VAddr address, u32 num_pairs);')),
    ('    std::unique_ptr<GpuProfile> gpu_profile;',
     L('    std::unique_ptr<GpuProfile> gpu_profile;',
       "    /// The title's occlusion queries (see OcclusionQueries); null when they are made up.",
       '    std::unique_ptr<OcclusionQueries> occlusion;')),
])

patch('src/video_core/renderer_vulkan/vk_rasterizer.cpp', lambda L, s, nl: [
    (L('    if (GpuProfile::Enabled()) {',
       '        gpu_profile = std::make_unique<GpuProfile>(instance, scheduler);',
       '    }'),
     L('    if (GpuProfile::Enabled()) {',
       '        gpu_profile = std::make_unique<GpuProfile>(instance, scheduler);',
       '    }',
       '    if (OcclusionQueries::Enabled()) {',
       '        occlusion = std::make_unique<OcclusionQueries>(instance, scheduler);',
       '        if (!occlusion->Ready()) {',
       '            occlusion.reset();',
       '        }',
       '    }')),
    ('Rasterizer::~Rasterizer() = default;',
     L('Rasterizer::~Rasterizer() = default;',
       '',
       'bool Rasterizer::OcclusionDump(VAddr address, u32 num_pairs) {',
       '    if (!occlusion) {',
       '        return false;',
       '    }',
       '    occlusion->Dump(address, num_pairs);',
       '    return true;',
       '}')),
    ('    if (skip_empty && !FrameStats::AbOff("skipempty") && DrawsNothing(pipeline)) {',
     L('    // (Not while an occlusion query is open: then what it lets through is what is asked.)',
       '    const bool counted = occlusion && occlusion->IsOpen();',
       '    if (skip_empty && !counted && !FrameStats::AbOff("skipempty") && DrawsNothing(pipeline)) {')),
    (L('        const FrameStats::CallTimer timer{FrameStats::Call::Draw};',
       '        if (is_indexed) {',
       '            cmdbuf.drawIndexed(num_vertices, num_instances, 0, s32(vertex_offset),',
       '                               instance_offset);',
       '        } else {',
       '            cmdbuf.draw(num_vertices, num_instances, vertex_offset, instance_offset);',
       '        }',
       '    }'),
     L('        const FrameStats::CallTimer timer{FrameStats::Call::Draw};',
       '        const s32 query = counted ? occlusion->BeginDraw(cmdbuf) : -1;',
       '        if (is_indexed) {',
       '            cmdbuf.drawIndexed(num_vertices, num_instances, 0, s32(vertex_offset),',
       '                               instance_offset);',
       '        } else {',
       '            cmdbuf.draw(num_vertices, num_instances, vertex_offset, instance_offset);',
       '        }',
       '        if (counted) {',
       '            occlusion->EndDraw(cmdbuf, query);',
       '        }',
       '    }',
       '    if (counted && trace) {',
       '        LOG_INFO(Render_Vulkan, "TRACE   counted for an occlusion query");',
       '    }')),
    (L('    const bool timed = gpu_profile && gpu_profile->Before(ProfileWork(pipeline), 0);',
       '    if (is_indexed) {',
       '        ASSERT(sizeof(VkDrawIndexedIndirectCommand) == stride);'),
     L('    const bool timed = gpu_profile && gpu_profile->Before(ProfileWork(pipeline), 0);',
       '    const bool counted = occlusion && occlusion->IsOpen();',
       '    const s32 query = counted ? occlusion->BeginDraw(cmdbuf) : -1;',
       '    if (is_indexed) {',
       '        ASSERT(sizeof(VkDrawIndexedIndirectCommand) == stride);')),
    (L('            cmdbuf.drawIndirect(buffer->Handle(), base, max_count, stride);',
       '        }',
       '    }',
       '    if (timed) {'),
     L('            cmdbuf.drawIndirect(buffer->Handle(), base, max_count, stride);',
       '        }',
       '    }',
       '    if (counted) {',
       '        occlusion->EndDraw(cmdbuf, query);',
       '    }',
       '    if (timed) {')),
])

patch('src/video_core/amdgpu/liverpool.cpp', lambda L, s, nl: [
    (L('                    if (event->event_type.Value() == EventType::PixelPipeStatDump) {',
       '                        static constexpr u64 OcclusionCounterValidMask = 0x8000000000000000ULL;'),
     L("                    // The GPU's own counts when it can (Vulkan::OcclusionQueries), else every",
       '                    // query sees the same made-up number of samples.',
       '                    if (event->event_type.Value() == EventType::PixelPipeStatDump &&',
       '                        rasterizer &&',
       '                        rasterizer->OcclusionDump(event->Address<VAddr>(), num_counter_pairs)) {',
       '                        // Answered once the GPU has done the draws.',
       '                    } else if (event->event_type.Value() == EventType::PixelPipeStatDump) {',
       '                        static constexpr u64 OcclusionCounterValidMask = 0x8000000000000000ULL;')),
])

patch('src/video_core/renderer_vulkan/vk_instance.cpp', lambda L, s, nl: [
    (L('                .samplerAnisotropy = features.samplerAnisotropy,',
       '                .vertexPipelineStoresAndAtomics = features.vertexPipelineStoresAndAtomics,'),
     L('                .samplerAnisotropy = features.samplerAnisotropy,',
       '                .occlusionQueryPrecise = features.occlusionQueryPrecise,',
       '                .vertexPipelineStoresAndAtomics = features.vertexPipelineStoresAndAtomics,')),
])


def cmake_pairs(L, s, nl):
    m = re.search(r'( *)src/video_core/renderer_vulkan/vk_gpu_profile\.h' + re.escape(nl), s)
    ind = m.group(1)
    return [(m.group(0), m.group(0) + ind + 'src/video_core/renderer_vulkan/vk_occlusion.cpp' + nl +
             ind + 'src/video_core/renderer_vulkan/vk_occlusion.h' + nl)]


patch('CMakeLists.txt', cmake_pairs)
