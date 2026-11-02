// SPDX-FileCopyrightText: Copyright 2024 shadPS4 Emulator Project
// SPDX-License-Identifier: GPL-2.0-or-later

#version 450

layout (location = 0) in vec2 uv;
layout (location = 0) out vec4 color;

layout (binding = 0) uniform sampler2D texSampler;

layout (push_constant) uniform settings {
    float gamma;
    bool hdr;
    // Above 0, the picture is sharpened by so much (up to 1): for one that is shown larger
    // than it was drawn, which blurs it.
    float sharpen;
    // The target encodes what it is given for display by itself (an sRGB image): it has to be
    // given linear light, or the picture would be encoded twice.
    bool linear_out;
    // The texture gives back what it holds, already encoded for display (an sRGB image read
    // through a UNORM view, gamma 1): nothing to encode.
    bool encoded_in;
    // Within centre_radius of the middle (a share of the way to the edge, on both axes) the
    // picture is sharpened by sharpen_centre instead: where FSR 1 enlarged the title's scene.
    float sharpen_centre;
    float centre_radius;
    // Above 0, edges are smoothed first by morphological anti-aliasing (MLAA), at that
    // strength (up to 1); a pixel smoothed so is then not sharpened.
    float mlaa;
} pp;

const float cutoff = 0.0031308, a = 1.055, b = 0.055, d = 12.92;
vec3 gamma(vec3 rgb) {
    return mix(
        a * pow(rgb, vec3(1.0 / (2.4 + 1.0 - pp.gamma))) - b,
        d * rgb / pp.gamma,
        lessThan(rgb, vec3(cutoff))
    );
}

// What goes to the display for the picture at a place.
vec3 shown(vec2 at) {
    vec3 rgb = textureLod(texSampler, at, 0.0).rgb;
    return pp.hdr || pp.encoded_in ? rgb : gamma(rgb);
}

// Morphological anti-aliasing (MLAA), on the picture as it is shown: a pixel on an edge is
// found by its contrast with its neighbours; the edge is followed both ways to where it ends,
// and the shape it makes there (which end is nearer, and whether this pixel is on the side that
// sticks out) says how much of the pixel a straight line along the edge would leave to the
// other side: that much of the neighbour across the edge is mixed in.
const float EdgeShare = 0.125;  // The least contrast that makes an edge, of the brightest pixel,
const float EdgeLeast = 0.05;   // and as such.
const float Speck = 0.375;      // How much a pixel unlike all its neighbours is evened out.
const int Steps = 8;            // How far an edge is followed, in pixels a step.
const float StepLength[Steps] = float[Steps](1.0, 1.0, 1.5, 2.0, 2.0, 4.0, 8.0, 12.0);

float Luma(vec3 rgb) {
    const float light = dot(max(rgb, vec3(0.0)), vec3(0.299, 0.587, 0.114));
    return pp.hdr ? sqrt(light / (1.0 + light)) : light;
}

float LumaAt(vec2 at) {
    return Luma(shown(at));
}

// The share of the neighbour across the edge that belongs into this pixel (0: no edge here),
// and that neighbour.
float Morphological(vec3 here, vec2 texel, out vec3 other) {
    other = here;
    const float m = Luma(here);
    const float n = LumaAt(uv - vec2(0.0, texel.y));
    const float s = LumaAt(uv + vec2(0.0, texel.y));
    const float w = LumaAt(uv - vec2(texel.x, 0.0));
    const float e = LumaAt(uv + vec2(texel.x, 0.0));
    const float brightest = max(max(max(n, s), max(w, e)), m);
    const float darkest = min(min(min(n, s), min(w, e)), m);
    const float contrast = brightest - darkest;
    if (contrast < max(EdgeLeast, brightest * EdgeShare)) {
        return 0.0;
    }
    const float nw = LumaAt(uv + vec2(-texel.x, -texel.y));
    const float ne = LumaAt(uv + vec2(texel.x, -texel.y));
    const float sw = LumaAt(uv + vec2(-texel.x, texel.y));
    const float se = LumaAt(uv + vec2(texel.x, texel.y));

    // Which way the edge runs: along the rows if brightness changes more from row to row.
    const float across_rows = abs(nw + sw - 2.0 * w) + 2.0 * abs(n + s - 2.0 * m) +
                              abs(ne + se - 2.0 * e);
    const float across_columns = abs(nw + ne - 2.0 * n) + 2.0 * abs(w + e - 2.0 * m) +
                                 abs(sw + se - 2.0 * s);
    const bool along_rows = across_rows >= across_columns;
    const float before = along_rows ? n : w;
    const float after = along_rows ? s : e;
    const bool steeper_before = abs(before - m) >= abs(after - m);
    const float rise = max(abs(before - m), abs(after - m)) * 0.25;
    const float side = steeper_before ? -1.0 : 1.0;
    const float middle = 0.5 * ((steeper_before ? before : after) + m);
    const bool centre_below = m < middle;

    // From half a pixel towards that neighbour, where both sides of the edge are read at once,
    // along the edge to where it stops being one.
    const vec2 across = along_rows ? vec2(0.0, texel.y) : vec2(texel.x, 0.0);
    const vec2 along = along_rows ? vec2(texel.x, 0.0) : vec2(0.0, texel.y);
    const vec2 start = uv + across * (side * 0.5);
    float back = 0.0;
    float forth = 0.0;
    float end_back = 0.0;
    float end_forth = 0.0;
    bool done_back = false;
    bool done_forth = false;
    for (int i = 0; i < Steps; ++i) {
        if (!done_back) {
            back += StepLength[i];
            end_back = LumaAt(start - along * back) - middle;
            done_back = abs(end_back) >= rise;
        }
        if (!done_forth) {
            forth += StepLength[i];
            end_forth = LumaAt(start + along * forth) - middle;
            done_forth = abs(end_forth) >= rise;
        }
        if (done_back && done_forth) {
            break;
        }
    }
    // The nearer end decides, if the edge turns there the way that makes this pixel the one
    // that sticks out: the line from that end leaves this much of the pixel to the other side.
    const bool nearer_back = back < forth;
    const float nearer = min(back, forth);
    const bool sticks_out = ((nearer_back ? end_back : end_forth) < 0.0) != centre_below;
    const float by_edge = sticks_out ? 0.5 - nearer / (back + forth) : 0.0;

    // A pixel unlike everything around it is evened out a little whatever the edge says.
    const float around = (2.0 * (n + s + w + e) + nw + ne + sw + se) / 12.0;
    float speck = clamp(abs(around - m) / contrast, 0.0, 1.0);
    speck = speck * speck * (3.0 - 2.0 * speck);
    other = shown(uv + across * side);
    return clamp(max(by_edge, speck * speck * Speck) * pp.mlaa, 0.0, 1.0);
}

void main() {
    vec4 color_linear = textureLod(texSampler, uv, 0.0);
    vec3 here = pp.hdr || pp.encoded_in ? color_linear.rgb : gamma(color_linear.rgb);
    vec2 from_middle = uv * 2.0 - 1.0;
    float sharpen = dot(from_middle, from_middle) < pp.centre_radius * pp.centre_radius
                        ? pp.sharpen_centre
                        : pp.sharpen;
    if (pp.mlaa > 0.0) {
        vec3 other;
        const float share = Morphological(here, 1.0 / vec2(textureSize(texSampler, 0)), other);
        if (share > 0.0) {
            here = mix(here, other, share);
            sharpen = 0.0;
        }
    }
    if (sharpen > 0.0) {
        // Contrast adaptive sharpening: a pixel is pushed away from the four next to it, the
        // more the less they differ already, and never beyond black or white.
        vec2 texel = 1.0 / vec2(textureSize(texSampler, 0));
        vec3 above = shown(uv - vec2(0.0, texel.y));
        vec3 below = shown(uv + vec2(0.0, texel.y));
        vec3 left = shown(uv - vec2(texel.x, 0.0));
        vec3 right = shown(uv + vec2(texel.x, 0.0));
        vec3 darkest = min(min(min(above, below), min(left, right)), here);
        vec3 brightest = max(max(max(above, below), max(left, right)), here);
        vec3 room = sqrt(clamp(min(darkest, 1.0 - brightest) / max(brightest, vec3(1e-5)),
                               0.0, 1.0));
        vec3 weight = room * (-1.0 / mix(8.0, 5.0, clamp(sharpen, 0.0, 1.0)));
        here = clamp(((above + below + left + right) * weight + here) / (1.0 + 4.0 * weight),
                     0.0, 1.0);
    }
    if (pp.linear_out && !pp.hdr) {
        // Back to linear light, by the curve the target encodes with.
        here = mix(pow((here + 0.055) / 1.055, vec3(2.4)), here / 12.92,
                   lessThanEqual(here, vec3(0.04045)));
    }
    color = vec4(here, color_linear.a);
}
