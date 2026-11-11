# Occlusion queries, step 2: a query whose draws were not all counted (one left out by the
# emulator, or past the per-query limit) answers "visible" with the old made-up count instead of
# a too-small sum, so nothing is hidden because the emulator dropped a draw.
import sys

root = sys.argv[1]


def patch(rel, make_pairs):
    p = root + '/' + rel
    s = open(p, encoding='utf-8', newline='').read()
    nl = '\r\n' if '\r\n' in s else '\n'

    def L(*lines):
        return nl.join(lines)

    for old, new in make_pairs(L):
        n = s.count(old)
        if n != 1:
            sys.exit(f'{rel}: expected 1 match, found {n}: {old[:80]!r}')
        s = s.replace(old, new)
    open(p, 'w', encoding='utf-8', newline='').write(s)
    print('patched', rel)


patch('src/video_core/renderer_vulkan/vk_occlusion.h', lambda L: [
    (L('    /// Around a draw while a query is open (inside its rendering). The slot counted in, or -1.'),
     L('    /// A draw has come (before anything decides whether it is made): one the open query expects',
       '    /// to count.',
       '    void NoteDraw() {',
       '        if (open) {',
       '            ++open->draws_seen;',
       '        }',
       '    }',
       '',
       '    /// Around a draw while a query is open (inside its rendering). The slot counted in, or -1.')),
    (L('        u32 num_pairs{};',
       '        boost::container::small_vector<u32, 4> slots;'),
     L('        u32 num_pairs{};',
       '        u32 draws_seen{};',
       '        boost::container::small_vector<u32, 4> slots;')),
    (L('    u64 draws_counted{};'),
     L('    u64 draws_counted{};',
       '    u64 incomplete{};')),
])

patch('src/video_core/renderer_vulkan/vk_occlusion.cpp', lambda L: [
    (L('    Query query = std::move(*open);',
       '    open.reset();'),
     L('    Query query = std::move(*open);',
       '    open.reset();',
       "    // A draw the emulator left out would have counted: rather than a sum that is too small (the",
       '    // sun or a model hidden that is not), the query sees everything, as all of them used to.',
       '    const bool complete = query.draws_seen <= query.slots.size();',
       '    if (!complete) {',
       '        ++incomplete;',
       '    }')),
    (L('    scheduler.DeferPriorityOperation([this, query = std::move(query)] {'),
     L('    scheduler.DeferPriorityOperation([this, complete, query = std::move(query)] {')),
    (L('        if (!ok) {'),
     L('        if (!ok || !complete) {')),
    (L('            failed.fetch_add(1, std::memory_order_relaxed);'),
     L('            if (!ok) {',
       '                failed.fetch_add(1, std::memory_order_relaxed);',
       '            }')),
    (L('             "{} saw nothing, the others {:.0f} samples on average; {} left open, {} draws past "',
       '             "the limit, {} unreadable",',
       '             opened, n, draws_counted, none, n > none ? double(total) / double(n - none) : 0.0,',
       '             unclosed, too_many_draws, bad);',
       '    opened = unclosed = too_many_draws = draws_counted = 0;'),
     L('             "{} saw nothing, the others {:.0f} samples on average; {} left open, {} draws past "',
       '             "the limit, {} with a draw left out (seen as visible), {} unreadable",',
       '             opened, n, draws_counted, none, n > none ? double(total) / double(n - none) : 0.0,',
       '             unclosed, too_many_draws, incomplete, bad);',
       '    opened = unclosed = too_many_draws = draws_counted = incomplete = 0;')),
])

patch('src/video_core/renderer_vulkan/vk_rasterizer.cpp', lambda L: [
    (L('void Rasterizer::Draw(bool is_indexed, u32 index_offset) {',
       '    RENDERER_TRACE;'),
     L('void Rasterizer::Draw(bool is_indexed, u32 index_offset) {',
       '    RENDERER_TRACE;',
       '    if (occlusion && !in_target_passes) {',
       '        occlusion->NoteDraw();',
       '    }')),
    (L('                              u32 max_count, VAddr count_address) {',
       '    RENDERER_TRACE;'),
     L('                              u32 max_count, VAddr count_address) {',
       '    RENDERER_TRACE;',
       '    if (occlusion) {',
       '        occlusion->NoteDraw();',
       '    }')),
])
