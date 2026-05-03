"""
GPU hue ring + saturation / value arc pickers for the sculpt wheel.

Shaders adapted from Blend-Wheel ``croma_rng_*.frag`` (point sprites → screen quads, ``v_uv``).
"""

from __future__ import annotations

import math
from typing import Tuple

import gpu
from gpu.shader import create_from_info
from gpu.types import GPUShader, GPUShaderCreateInfo, GPUStageInterfaceInfo
from gpu_extras.batch import batch_for_shader

from ..core.gpu.state_control import CM_GPU_BLEND
from ..core.gpu.imm_2d import draw_lines
from .utils import _quad_verts
from .utils import draw_circle_fill, draw_ring

# ---------------------------------------------------------------------------
# Vertex (shared with wheel quads)
# ---------------------------------------------------------------------------

_COLPK_VERT = """
void main() {
    v_uv = uv;
    gl_Position = ModelViewProjectionMatrix * vec4(pos, 0.0, 1.0);
}
"""

# Full hue ring — uniforms s, v (saturation / value driving the wheel colors)
_COLPK_H_FRAG = """
#define TWO_PI 6.28318530718
#define RAD_THRES 0.03

vec3 hsb2rgb(in vec3 c) {
    vec3 rgb = clamp(abs(mod(c.x * 6.0 + vec3(0.0, 4.0, 2.0), 6.0) - 3.0) - 1.0, 0.0, 1.0);
    rgb = rgb * rgb * (3.0 - 2.0 * rgb);
    return c.z * mix(vec3(1.0), rgb, c.y);
}

void main() {
    float r = 0.0;
    float delta = 0.0;
    float alpha = 0.0;
    vec2 cxy = 2.0 * v_uv - 1.0;
    r = dot(cxy, cxy);
    delta = fwidth(r);
    alpha = 1.0 - smoothstep(1.0 - delta, 1.0 + delta, r);
    if (alpha < 0.05) {
        discard;
    }

    vec2 toCenter = vec2(0.5) - v_uv.xy;
    float angle = atan(toCenter.y, toCenter.x);
    float radius = length(toCenter) * 2.0;
    float minRad = clamp(ring_inner_ratio, 0.0, 0.999);
    float maxRad = 1.0;
    float minRad2 = minRad + RAD_THRES;
    float maxRad2 = maxRad - RAD_THRES;

    if (radius < minRad || radius > maxRad) {
        discard;
    }

    if (radius < minRad2) {
        alpha = smoothstep(minRad, minRad2, radius);
    } else if (radius > maxRad2) {
        alpha = smoothstep(maxRad, maxRad2, radius);
    }

    vec3 co = hsb2rgb(vec3((angle / TWO_PI) + 0.5, s, v));
    fragColor.rgb = pow(co, vec3(2.2));
    fragColor.a = alpha;
}
"""

# Saturation arc (left half of quad), angles in degrees
_COLPK_S_FRAG = """
#define ALPHA_THRES 0.01
#define RAD_THRES 0.03

vec3 hsv2rgb(vec3 c) {
    vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

void main() {
    vec2 cxy = 2.0 * v_uv - 1.0;
    if (cxy.x > 0.0) {
        discard;
    }

    float r = dot(cxy, cxy);
    float delta = fwidth(r);
    float alpha = 1.0 - smoothstep(1.0 - delta, 1.0 + delta, r);
    if (alpha < ALPHA_THRES) {
        discard;
    }

    vec2 toCenter = vec2(0.5) - v_uv.xy;
    float radius = length(toCenter) * 2.0;
    float minRad = clamp(ring_inner_ratio, 0.0, 0.999);
    float maxRad = 1.0;
    float minRad2 = minRad + RAD_THRES;
    float maxRad2 = maxRad - RAD_THRES;
    float midRad = 0.5 * (minRad + maxRad);
    float capRad = 0.5 * (maxRad - minRad);
    if (radius < minRad || radius > maxRad) {
        discard;
    }

    float angle = degrees(atan(cxy.y, cxy.x));
    if (angle < 0.0) {
        angle = 360.0 + angle;
    }
    vec2 cap0 = vec2(cos(radians(angbot)), sin(radians(angbot))) * midRad;
    vec2 cap1 = vec2(cos(radians(angtop)), sin(radians(angtop))) * midRad;
    bool inSector = (angle >= angbot && angle <= angtop);
    float cap0Dist = distance(cxy, cap0);
    float cap1Dist = distance(cxy, cap1);
    float cap0Fw = max(1e-6, fwidth(cap0Dist));
    float cap1Fw = max(1e-6, fwidth(cap1Dist));
    float capAlpha0 = 1.0 - smoothstep(capRad - cap0Fw, capRad + cap0Fw, cap0Dist);
    float capAlpha1 = 1.0 - smoothstep(capRad - cap1Fw, capRad + cap1Fw, cap1Dist);
    float shapeAlpha = max(inSector ? 1.0 : 0.0, max(capAlpha0, capAlpha1));
    if (shapeAlpha < ALPHA_THRES) {
        discard;
    }

    if (radius < minRad2) {
        alpha = smoothstep(minRad, minRad2, radius);
    } else if (radius > maxRad2) {
        alpha = smoothstep(maxRad, maxRad2, radius);
    }
    fragColor.a = alpha * shapeAlpha;

    float sat = clamp((angle - angbot) / max(1e-6, (angtop - angbot)), 0.0, 1.0);
    float capMix0 = (1.0 - (inSector ? 1.0 : 0.0)) * capAlpha0;
    float capMix1 = (1.0 - (inSector ? 1.0 : 0.0)) * capAlpha1;
    sat = mix(sat, 0.0, clamp(capMix0, 0.0, 1.0));
    sat = mix(sat, 1.0, clamp(capMix1, 0.0, 1.0));
    vec3 co = hsv2rgb(vec3(h, sat, v));
    fragColor.rgb = pow(co, vec3(2.2));
}
"""

# Value arc (right half of quad)
_COLPK_V_FRAG = """
#define ALPHA_THRES 0.01
#define RAD_THRES 0.03

vec3 hsv2rgb(vec3 c) {
    vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

void main() {
    vec2 cxy = 2.0 * v_uv - 1.0;
    if (cxy.x < 0.0) {
        discard;
    }

    float r = dot(cxy, cxy);
    float delta = fwidth(r);
    float alpha = 1.0 - smoothstep(1.0 - delta, 1.0 + delta, r);
    if (alpha < ALPHA_THRES) {
        discard;
    }

    vec2 toCenter = vec2(0.5) - v_uv.xy;
    float radius = length(toCenter) * 2.0;
    float minRad = clamp(ring_inner_ratio, 0.0, 0.999);
    float maxRad = 1.0;
    float minRad2 = minRad + RAD_THRES;
    float maxRad2 = maxRad - RAD_THRES;
    float midRad = 0.5 * (minRad + maxRad);
    float capRad = 0.5 * (maxRad - minRad);
    if (radius < minRad || radius > maxRad) {
        discard;
    }

    float angle = degrees(atan(cxy.y, cxy.x));
    vec2 cap0 = vec2(cos(radians(angbot)), sin(radians(angbot))) * midRad;
    vec2 cap1 = vec2(cos(radians(angtop)), sin(radians(angtop))) * midRad;
    bool inSector = (angle <= angbot && angle >= angtop);
    float cap0Dist = distance(cxy, cap0);
    float cap1Dist = distance(cxy, cap1);
    float cap0Fw = max(1e-6, fwidth(cap0Dist));
    float cap1Fw = max(1e-6, fwidth(cap1Dist));
    float capAlpha0 = 1.0 - smoothstep(capRad - cap0Fw, capRad + cap0Fw, cap0Dist);
    float capAlpha1 = 1.0 - smoothstep(capRad - cap1Fw, capRad + cap1Fw, cap1Dist);
    float shapeAlpha = max(inSector ? 1.0 : 0.0, max(capAlpha0, capAlpha1));
    if (shapeAlpha < ALPHA_THRES) {
        discard;
    }

    if (radius < minRad2) {
        alpha = smoothstep(minRad, minRad2, radius);
    } else if (radius > maxRad2) {
        alpha = smoothstep(maxRad, maxRad2, radius);
    }
    fragColor.a = alpha * shapeAlpha;

    float val = clamp((angbot - angle) / max(1e-6, (angbot - angtop)), 0.0, 1.0);
    float capMix0 = (1.0 - (inSector ? 1.0 : 0.0)) * capAlpha0;
    float capMix1 = (1.0 - (inSector ? 1.0 : 0.0)) * capAlpha1;
    val = mix(val, 0.0, clamp(capMix0, 0.0, 1.0));
    val = mix(val, 1.0, clamp(capMix1, 0.0, 1.0));
    vec3 co = hsv2rgb(vec3(h, s, val));
    fragColor.rgb = pow(co, vec3(2.2));
}
"""

_shader_h: GPUShader | None = None
_shader_s: GPUShader | None = None
_shader_v: GPUShader | None = None


def _build_h() -> GPUShader:
    iface = GPUStageInterfaceInfo("sculpt_colpk_h_iface")
    iface.smooth("VEC2", "v_uv")
    info = GPUShaderCreateInfo()
    info.push_constant("MAT4", "ModelViewProjectionMatrix")
    info.push_constant("FLOAT", "s")
    info.push_constant("FLOAT", "v")
    info.push_constant("FLOAT", "ring_inner_ratio")
    info.vertex_in(0, "VEC2", "pos")
    info.vertex_in(1, "VEC2", "uv")
    info.vertex_out(iface)
    info.fragment_out(0, "VEC4", "fragColor")
    info.vertex_source(_COLPK_VERT)
    info.fragment_source(_COLPK_H_FRAG)
    return create_from_info(info)


def _build_s() -> GPUShader:
    iface = GPUStageInterfaceInfo("sculpt_colpk_s_iface")
    iface.smooth("VEC2", "v_uv")
    info = GPUShaderCreateInfo()
    info.push_constant("MAT4", "ModelViewProjectionMatrix")
    info.push_constant("FLOAT", "h")
    info.push_constant("FLOAT", "v")
    info.push_constant("FLOAT", "angtop")
    info.push_constant("FLOAT", "angbot")
    info.push_constant("FLOAT", "ring_inner_ratio")
    info.vertex_in(0, "VEC2", "pos")
    info.vertex_in(1, "VEC2", "uv")
    info.vertex_out(iface)
    info.fragment_out(0, "VEC4", "fragColor")
    info.vertex_source(_COLPK_VERT)
    info.fragment_source(_COLPK_S_FRAG)
    return create_from_info(info)


def _build_v() -> GPUShader:
    iface = GPUStageInterfaceInfo("sculpt_colpk_v_iface")
    iface.smooth("VEC2", "v_uv")
    info = GPUShaderCreateInfo()
    info.push_constant("MAT4", "ModelViewProjectionMatrix")
    info.push_constant("FLOAT", "h")
    info.push_constant("FLOAT", "s")
    info.push_constant("FLOAT", "angtop")
    info.push_constant("FLOAT", "angbot")
    info.push_constant("FLOAT", "ring_inner_ratio")
    info.vertex_in(0, "VEC2", "pos")
    info.vertex_in(1, "VEC2", "uv")
    info.vertex_out(iface)
    info.fragment_out(0, "VEC4", "fragColor")
    info.vertex_source(_COLPK_VERT)
    info.fragment_source(_COLPK_V_FRAG)
    return create_from_info(info)


def _get_shader_h() -> GPUShader:
    global _shader_h
    if _shader_h is None:
        _shader_h = _build_h()
    return _shader_h


def _get_shader_s() -> GPUShader:
    global _shader_s
    if _shader_s is None:
        _shader_s = _build_s()
    return _shader_s


def _get_shader_v() -> GPUShader:
    global _shader_v
    if _shader_v is None:
        _shader_v = _build_v()
    return _shader_v


def draw_colpk_hue_ring(
    cx: float,
    cy: float,
    outer_radius_px: float,
    inner_radius_px: float,
    sat: float,
    val: float,
) -> None:
    if outer_radius_px <= 0.0:
        return
    shader = _get_shader_h()
    positions, uvs, indices = _quad_verts(cx, cy, outer_radius_px)
    batch = batch_for_shader(shader, "TRIS", {"pos": positions, "uv": uvs}, indices=indices)
    with CM_GPU_BLEND("ALPHA"):
        shader.bind()
        shader.uniform_float("s", float(max(0.0, min(1.0, sat))))
        shader.uniform_float("v", float(max(0.0, min(1.0, val))))
        ratio = 0.8 if outer_radius_px <= 0.0 else max(0.0, min(0.999, inner_radius_px / outer_radius_px))
        shader.uniform_float("ring_inner_ratio", float(ratio))
        batch.draw(shader)


def draw_colpk_sat_arc(
    cx: float,
    cy: float,
    outer_radius_px: float,
    inner_radius_px: float,
    ang_top_deg: float,
    ang_bot_deg: float,
    hue: float,
    val: float,
) -> None:
    """*ang_top_deg* / *ang_bot_deg* match Blend-Wheel ``ColpkRngS`` (115° / 245°); uniforms swap names."""
    if outer_radius_px <= 0.0:
        return
    shader = _get_shader_s()
    positions, uvs, indices = _quad_verts(cx, cy, outer_radius_px)
    batch = batch_for_shader(shader, "TRIS", {"pos": positions, "uv": uvs}, indices=indices)
    with CM_GPU_BLEND("ALPHA"):
        shader.bind()
        shader.uniform_float("h", float(max(0.0, min(1.0, hue))))
        shader.uniform_float("v", float(max(0.0, min(1.0, val))))
        shader.uniform_float("angtop", float(ang_bot_deg))
        shader.uniform_float("angbot", float(ang_top_deg))
        ratio = 0.8 if outer_radius_px <= 0.0 else max(0.0, min(0.999, inner_radius_px / outer_radius_px))
        shader.uniform_float("ring_inner_ratio", float(ratio))
        batch.draw(shader)


def draw_colpk_val_arc(
    cx: float,
    cy: float,
    outer_radius_px: float,
    inner_radius_px: float,
    ang_top_deg: float,
    ang_bot_deg: float,
    hue: float,
    sat: float,
) -> None:
    """*ang_top_deg* / *ang_bot_deg* match ``ColpkRngV`` (65° / −65°); uniforms swap names."""
    if outer_radius_px <= 0.0:
        return
    shader = _get_shader_v()
    positions, uvs, indices = _quad_verts(cx, cy, outer_radius_px)
    batch = batch_for_shader(shader, "TRIS", {"pos": positions, "uv": uvs}, indices=indices)
    with CM_GPU_BLEND("ALPHA"):
        shader.bind()
        shader.uniform_float("h", float(max(0.0, min(1.0, hue))))
        shader.uniform_float("s", float(max(0.0, min(1.0, sat))))
        shader.uniform_float("angtop", float(ang_bot_deg))
        shader.uniform_float("angbot", float(ang_top_deg))
        ratio = 0.8 if outer_radius_px <= 0.0 else max(0.0, min(0.999, inner_radius_px / outer_radius_px))
        shader.uniform_float("ring_inner_ratio", float(ratio))
        batch.draw(shader)


def get_colpk_sv_swatches_layout(
    cx: float,
    cy: float,
    sv_inner_r: float,
    sv_outer_r: float,
) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float], float, float]:
    """Layout for (primary, swap, secondary) controls between S/V top caps."""
    mid_sv = 0.5 * (sv_inner_r + sv_outer_r)
    band = max(1e-6, sv_outer_r - sv_inner_r)
    top_y = cy + mid_sv * math.sin(math.radians(65.0))
    swatch_r = max(5.0, band * 0.30)
    swap_r = max(4.0, swatch_r * 0.72)
    half_span = swatch_r * 1.45 + swap_r
    left = (cx - half_span, top_y)
    center = (cx, top_y)
    right = (cx + half_span, top_y)
    return left, center, right, swatch_r, swap_r


def draw_colpk_sv_swatches(
    cx: float,
    cy: float,
    sv_inner_r: float,
    sv_outer_r: float,
    primary_rgb: tuple[float, float, float],
    secondary_rgb: tuple[float, float, float],
    *,
    hover_swap: bool = False,
) -> tuple[tuple[float, float], float]:
    """Draw left/right color swatches + center swap button. Returns (swap_center, swap_radius)."""
    left, center, right, swatch_r, swap_r = get_colpk_sv_swatches_layout(cx, cy, sv_inner_r, sv_outer_r)

    # Swatches
    draw_circle_fill(left[0], left[1], swatch_r, (*primary_rgb, 1.0), softness=0.10)
    draw_ring(left[0], left[1], swatch_r, (0.92, 0.94, 0.97, 0.90), thickness=1.1, softness=0.06)

    draw_circle_fill(right[0], right[1], swatch_r, (*secondary_rgb, 1.0), softness=0.10)
    draw_ring(right[0], right[1], swatch_r, (0.92, 0.94, 0.97, 0.90), thickness=1.1, softness=0.06)

    # Swap button
    fill = (0.15, 0.16, 0.19, 0.98) if hover_swap else (0.11, 0.12, 0.15, 0.95)
    out = (0.98, 0.98, 0.99, 0.95) if hover_swap else (0.84, 0.86, 0.90, 0.92)
    draw_circle_fill(center[0], center[1], swap_r, fill, softness=0.12)
    draw_ring(center[0], center[1], swap_r, out, thickness=1.0, softness=0.06)

    # White arrows icon (no text): top arrow points right, bottom arrow points left.
    x, y = center
    arm = swap_r * 0.60
    ah = swap_r * 0.24
    dy = swap_r * 0.22
    lines = [
        (x - arm, y + dy), (x + arm, y + dy),
        (x + arm, y + dy), (x + arm - ah, y + dy + ah),
        (x + arm, y + dy), (x + arm - ah, y + dy - ah),
        (x + arm, y - dy), (x - arm, y - dy),
        (x - arm, y - dy), (x - arm + ah, y - dy + ah),
        (x - arm, y - dy), (x - arm + ah, y - dy - ah),
    ]
    draw_lines(lines, (1.0, 1.0, 1.0, 0.95), line_width=1.3, strip=False)
    return center, swap_r
