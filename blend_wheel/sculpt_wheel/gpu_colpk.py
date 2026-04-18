"""
GPU hue ring + saturation / value arc pickers for the sculpt wheel.

Shaders adapted from Blend-Wheel ``croma_rng_*.frag`` (point sprites → screen quads, ``v_uv``).
"""

from __future__ import annotations

from typing import Tuple

import gpu
from gpu.shader import create_from_info
from gpu.types import GPUShader, GPUShaderCreateInfo, GPUStageInterfaceInfo
from gpu_extras.batch import batch_for_shader

from ..core.gpu.state_control import CM_GPU_BLEND
from .gpu_utils import _quad_verts

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
#define SCALE 1.00
#define RAD_THRES 0.03
#define MIN_RAD 0.8 * (1.0 / SCALE)
#define MIN_RAD_2 MIN_RAD + RAD_THRES
#define MAX_RAD 1.0
#define MAX_RAD_2 MAX_RAD - RAD_THRES

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

    if (radius < MIN_RAD || radius > MAX_RAD) {
        discard;
    }

    if (radius < MIN_RAD_2) {
        alpha = smoothstep(MIN_RAD, MIN_RAD_2, radius);
    } else if (radius > MAX_RAD_2) {
        alpha = smoothstep(MAX_RAD, MAX_RAD_2, radius);
    }

    vec3 co = hsb2rgb(vec3((angle / TWO_PI) + 0.5, s, v));
    fragColor.rgb = pow(co, vec3(2.2));
    fragColor.a = alpha;
}
"""

# Saturation arc (left half of quad), angles in degrees
_COLPK_S_FRAG = """
#define ALPHA_THRES 0.01
#define SCALE 1.0
#define RAD_THRES 0.03
#define MIN_RAD 0.8 * (1.0 / SCALE)
#define MIN_RAD_2 MIN_RAD + RAD_THRES
#define MAX_RAD 1.0
#define MAX_RAD_2 MAX_RAD - RAD_THRES

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
    if (radius < MIN_RAD || radius > MAX_RAD) {
        discard;
    }

    float angle = degrees(atan(cxy.y, cxy.x));
    if (angle < 0.0) {
        angle = 360.0 + angle;
    }
    if (angle < angbot || angle > angtop) {
        discard;
    }

    if (radius < MIN_RAD_2) {
        alpha = smoothstep(MIN_RAD, MIN_RAD_2, radius);
    } else if (radius > MAX_RAD_2) {
        alpha = smoothstep(MAX_RAD, MAX_RAD_2, radius);
    }
    fragColor.a = alpha;

    float sat = smoothstep(angbot, angtop, angle);
    vec3 co = hsv2rgb(vec3(h, sat, v));
    fragColor.rgb = pow(co, vec3(2.2));
}
"""

# Value arc (right half of quad)
_COLPK_V_FRAG = """
#define ALPHA_THRES 0.01
#define SCALE 1.0
#define RAD_THRES 0.03
#define MIN_RAD 0.8 * (1.0 / SCALE)
#define MIN_RAD_2 MIN_RAD + RAD_THRES
#define MAX_RAD 1.0
#define MAX_RAD_2 MAX_RAD - RAD_THRES

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
    if (radius < MIN_RAD || radius > MAX_RAD) {
        discard;
    }

    float angle = degrees(atan(cxy.y, cxy.x));
    if (angle > angbot || angle < angtop) {
        discard;
    }

    if (radius < MIN_RAD_2) {
        alpha = smoothstep(MIN_RAD, MIN_RAD_2, radius);
    } else if (radius > MAX_RAD_2) {
        alpha = smoothstep(MAX_RAD, MAX_RAD_2, radius);
    }
    fragColor.a = alpha;

    float val = smoothstep(angbot, angtop, angle);
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
        batch.draw(shader)


def draw_colpk_sat_arc(
    cx: float,
    cy: float,
    outer_radius_px: float,
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
        batch.draw(shader)


def draw_colpk_val_arc(
    cx: float,
    cy: float,
    outer_radius_px: float,
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
        batch.draw(shader)
