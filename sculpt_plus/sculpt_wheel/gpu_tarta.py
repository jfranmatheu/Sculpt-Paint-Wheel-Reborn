"""
GPU drawing for the sculpt wheel “tarta” (pie) custom-button ring.

Ports the visual intent of ``DiRNGS_SPLITANG`` and ``DiRNGBLR`` from the legacy
addon (``gpu/dibuix.py``, ``__lib__`` RNGS_SPLITANG_FS / RNGBLR_FS) using
screen-space quads and ``GPUShaderCreateInfo`` (Blender 4+/5+).
"""

from __future__ import annotations

from typing import Tuple

import gpu
from gpu.shader import create_from_info
from gpu.types import GPUShader, GPUShaderCreateInfo, GPUStageInterfaceInfo, GPUTexture
from gpu_extras.batch import batch_for_shader

from ..core.gpu.state_control import CM_GPU_BLEND

from .gpu_utils import _quad_verts


# ---------------------------------------------------------------------------
# Vertex (shared)
# ---------------------------------------------------------------------------

_TARTA_VERT = """
void main() {
    v_uv = uv;
    gl_Position = ModelViewProjectionMatrix * vec4(pos, 0.0, 1.0);
}
"""

# ---------------------------------------------------------------------------
# Split pie ring — sharp radial slices (RNGS_SPLITANG_FS-style).
# Spoke darkening, hover lift, inner/outer light rims (reference wheel).
# ---------------------------------------------------------------------------

_PIE_RING_FRAG = """
void main() {
    const float PI = 3.14159265359;
    const float TWO_PI = 6.28318530718;
    const float SEAM_W = 0.018;
    const float SPOKE_DARK = 0.22;
    const float RIM_W = 0.032;
    const vec3 RIM_RGB = vec3(0.36, 0.38, 0.42);

    vec4 color = pieColor;

    vec2 cxy = 2.0 * v_uv - 1.0;
    float r_disc = dot(cxy, cxy);
    float s_mask = smoothstep(0.55, 0.45, abs(r_disc / 9.5) * 5.0);
    if (s_mask < 0.05) {
        discard;
    }

    vec2 toCenter = vec2(0.5) - v_uv;
    float radius = length(toCenter) * 2.0;
    if (radius < innerRatio) {
        discard;
    }

    int n = int(n_sectors + 0.5);
    int hv = int(hover_sector);
    if (n < 1) {
        discard;
    }

    float angle = atan(-toCenter.y, toCenter.x);
    float step = TWO_PI / float(n);
    float shifted = mod(angle - PI * 0.5 + step * 0.5 + TWO_PI, TWO_PI);
    float pos_in_seg = shifted / step;
    float dist_from_spoke = min(fract(pos_in_seg), 1.0 - fract(pos_in_seg));
    float seam = 1.0 - smoothstep(0.0, SEAM_W, dist_from_spoke);
    color.rgb *= mix(1.0, SPOKE_DARK, seam);

    int sec = int(floor(pos_in_seg + 1e-5));
    if (sec >= n) {
        sec = n - 1;
    }
    if (sec < 0) {
        sec = 0;
    }

    if (hv >= 0 && sec == hv) {
        float radial = clamp((radius - innerRatio) / max(1e-5, 1.0 - innerRatio), 0.0, 1.0);
        color.rgb = mix(color.rgb, color.rgb * 1.15, radial * 0.9);
    }

    float rim_in = 1.0 - smoothstep(0.0, RIM_W, abs(radius - innerRatio));
    float rim_out = 1.0 - smoothstep(0.0, RIM_W * 1.1, abs(radius - 1.0));
    float rims = max(rim_in, rim_out);
    color.rgb = mix(color.rgb, RIM_RGB, rims * 0.58);

    float alpha = color.a * s_mask;
    if (radius >= innerRatio && radius < innerRatio + inner_soft * 2.5) {
        alpha *= smoothstep(innerRatio, innerRatio + inner_soft, radius);
    }

    fragColor = vec4(pow(color.rgb, vec3(2.2)), alpha);
}
"""

# ---------------------------------------------------------------------------
# Soft ring (legacy RNGBLR — anti-aliased annulus in UV space)
# ---------------------------------------------------------------------------

_RING_BLR_FRAG = """
void main() {
    vec4 co = ringColor;

    vec2 cxy = 2.0 * v_uv - 1.0;
    float r = dot(cxy, cxy);
    float s = smoothstep(0.55, 0.45, abs(r / 9.5) * 5.0);
    if (s < 0.05) {
        discard;
    }

    vec2 toCenter = vec2(0.5) - v_uv;
    float radius = length(toCenter) * 2.0;
    float alpha = 1.0;

    float outter = 1.0;
    float rad = outter - thickness;
    float inner = rad - thickness;
    if (radius < inner) {
        discard;
    }

    if (radius > rad) {
        alpha = smoothstep(outter, rad - edge_soft, radius);
    } else {
        alpha = smoothstep(inner, rad + edge_soft, radius);
    }

    fragColor = vec4(pow(co.rgb, vec3(2.2)), co.a * alpha * s);
}
"""

# ---------------------------------------------------------------------------
# Textured disc with optional RGB boost (legacy DiIMGA_Intensify feel)
# ---------------------------------------------------------------------------

_TEX_BOOST_VERT = _TARTA_VERT

_TEX_BOOST_FRAG = """
void main() {
    float d = length(v_uv - vec2(0.5));
    float r = 0.5;
    float mask = smoothstep(r, r - softness, d);
    vec4 tex = texture(image, v_uv);
    if (tex.a < 0.05) {
        discard;
    }
    vec3 rgb = tex.rgb * boost;
    fragColor = vec4(rgb, tex.a * mask);
}
"""


_shader_pie_ring: GPUShader | None = None
_shader_ring_blr: GPUShader | None = None
_shader_tex_boost: GPUShader | None = None


def _build_pie_ring_shader() -> GPUShader:
    iface = GPUStageInterfaceInfo("sculpt_wheel_pie_iface_v3_dark")
    iface.smooth("VEC2", "v_uv")
    info = GPUShaderCreateInfo()
    info.push_constant("MAT4", "ModelViewProjectionMatrix")
    info.push_constant("VEC4", "pieColor")
    info.push_constant("FLOAT", "innerRatio")
    info.push_constant("FLOAT", "inner_soft")
    info.push_constant("FLOAT", "n_sectors")
    info.push_constant("FLOAT", "hover_sector")
    info.vertex_in(0, "VEC2", "pos")
    info.vertex_in(1, "VEC2", "uv")
    info.vertex_out(iface)
    info.fragment_out(0, "VEC4", "fragColor")
    info.vertex_source(_TARTA_VERT)
    info.fragment_source(_PIE_RING_FRAG)
    return create_from_info(info)


def _build_ring_blr_shader() -> GPUShader:
    iface = GPUStageInterfaceInfo("sculpt_wheel_ring_blr_iface")
    iface.smooth("VEC2", "v_uv")
    info = GPUShaderCreateInfo()
    info.push_constant("MAT4", "ModelViewProjectionMatrix")
    info.push_constant("VEC4", "ringColor")
    info.push_constant("FLOAT", "thickness")
    info.push_constant("FLOAT", "edge_soft")
    info.vertex_in(0, "VEC2", "pos")
    info.vertex_in(1, "VEC2", "uv")
    info.vertex_out(iface)
    info.fragment_out(0, "VEC4", "fragColor")
    info.vertex_source(_TARTA_VERT)
    info.fragment_source(_RING_BLR_FRAG)
    return create_from_info(info)


def _build_tex_boost_shader() -> GPUShader:
    iface = GPUStageInterfaceInfo("sculpt_wheel_tex_boost_iface")
    iface.smooth("VEC2", "v_uv")
    info = GPUShaderCreateInfo()
    info.push_constant("MAT4", "ModelViewProjectionMatrix")
    info.push_constant("FLOAT", "boost")
    info.push_constant("FLOAT", "softness")
    info.sampler(0, "FLOAT_2D", "image")
    info.vertex_in(0, "VEC2", "pos")
    info.vertex_in(1, "VEC2", "uv")
    info.vertex_out(iface)
    info.fragment_out(0, "VEC4", "fragColor")
    info.vertex_source(_TEX_BOOST_VERT)
    info.fragment_source(_TEX_BOOST_FRAG)
    return create_from_info(info)


def _get_pie_ring_shader() -> GPUShader:
    global _shader_pie_ring
    if _shader_pie_ring is None:
        _shader_pie_ring = _build_pie_ring_shader()
    return _shader_pie_ring


def _get_ring_blr_shader() -> GPUShader:
    global _shader_ring_blr
    if _shader_ring_blr is None:
        _shader_ring_blr = _build_ring_blr_shader()
    return _shader_ring_blr


def _get_tex_boost_shader() -> GPUShader:
    global _shader_tex_boost
    if _shader_tex_boost is None:
        _shader_tex_boost = _build_tex_boost_shader()
    return _shader_tex_boost


def draw_pie_split_ring(
    cx: float,
    cy: float,
    outer_radius_px: float,
    inner_ratio: float,
    n_sectors: int,
    hover_sector: int,
    color: Tuple[float, float, float, float],
    inner_soft: float = 0.08,
) -> None:
    """Draw the segmented annulus behind custom buttons (legacy SPLITANG)."""
    if n_sectors <= 0 or outer_radius_px <= 0.0:
        return
    shader = _get_pie_ring_shader()
    positions, uvs, indices = _quad_verts(cx, cy, outer_radius_px)
    batch = batch_for_shader(shader, "TRIS", {"pos": positions, "uv": uvs}, indices=indices)
    with CM_GPU_BLEND("ALPHA"):
        shader.bind()
        shader.uniform_float("pieColor", color)
        shader.uniform_float("innerRatio", float(inner_ratio))
        shader.uniform_float("inner_soft", float(inner_soft))
        shader.uniform_float("n_sectors", float(n_sectors))
        shader.uniform_float("hover_sector", float(hover_sector))
        batch.draw(shader)


def draw_ring_blr_gamma(
    cx: float,
    cy: float,
    radius_px: float,
    thickness: float,
    edge_soft: float,
    color: Tuple[float, float, float, float],
) -> None:
    """Soft annulus in normalized UV space (legacy DiRNGBLR). *radius_px* is outer extent of the quad."""
    if radius_px <= 0.0:
        return
    shader = _get_ring_blr_shader()
    positions, uvs, indices = _quad_verts(cx, cy, radius_px)
    batch = batch_for_shader(shader, "TRIS", {"pos": positions, "uv": uvs}, indices=indices)
    with CM_GPU_BLEND("ALPHA"):
        shader.bind()
        shader.uniform_float("ringColor", color)
        shader.uniform_float("thickness", float(thickness))
        shader.uniform_float("edge_soft", float(edge_soft))
        batch.draw(shader)


def draw_textured_circle_boost(
    cx: float,
    cy: float,
    radius: float,
    texture: GPUTexture,
    boost: float = 1.15,
    softness: float = 0.025,
) -> None:
    """Circular icon with linear RGB boost (legacy hover intensify)."""
    shader = _get_tex_boost_shader()
    positions, uvs, indices = _quad_verts(cx, cy, radius)
    batch = batch_for_shader(shader, "TRIS", {"pos": positions, "uv": uvs}, indices=indices)
    with CM_GPU_BLEND("ALPHA"):
        shader.bind()
        shader.uniform_sampler("image", texture)
        shader.uniform_float("boost", float(boost))
        shader.uniform_float("softness", float(softness))
        batch.draw(shader)
