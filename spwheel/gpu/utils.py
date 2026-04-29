"""GPU shader and batch helpers for the sculpt wheel overlay."""

from __future__ import annotations

from math import cos, sin, pi
from typing import Tuple

import gpu
from gpu.shader import create_from_info
from gpu.types import GPUShader, GPUShaderCreateInfo, GPUStageInterfaceInfo, GPUTexture
from gpu_extras.batch import batch_for_shader

from ..core.gpu.state_control import CM_GPU_BLEND


# ---------------------------------------------------------------------------
# Shader sources
# ---------------------------------------------------------------------------

_CIRCLE_FILL_VERT = """
void main() {
    v_uv = uv;
    gl_Position = ModelViewProjectionMatrix * vec4(pos, 0.0, 1.0);
}
"""

_CIRCLE_FILL_FRAG = """
void main() {
    float d = length(v_uv - vec2(0.5));
    float r = 0.5;
    float edge = smoothstep(r, r - softness, d);
    fragColor = vec4(pow(color.rgb, vec3(2.2)), color.a * edge);
}
"""

_RING_VERT = """
void main() {
    v_uv = uv;
    gl_Position = ModelViewProjectionMatrix * vec4(pos, 0.0, 1.0);
}
"""

_RING_FRAG = """
void main() {
    float d = length(v_uv - vec2(0.5));
    float band = max(outerRadius - innerRadius, 1e-5);
    float s = min(max(softness, 1e-5), band * 0.48);
    float aOuter = 1.0 - smoothstep(outerRadius - s, outerRadius + s, d);
    float aInner = smoothstep(innerRadius - s, innerRadius + s, d);
    float ring = aOuter * aInner;
    fragColor = vec4(pow(color.rgb, vec3(2.2)), color.a * ring);
}
"""

_TEXTURED_CIRCLE_VERT = """
void main() {
    v_uv = uv;
    gl_Position = ModelViewProjectionMatrix * vec4(pos, 0.0, 1.0);
}
"""

_TEXTURED_CIRCLE_FRAG = """
void main() {
    float d = length(v_uv - vec2(0.5));
    float r = 0.5;
    float mask = smoothstep(r, r - softness, d);
    vec4 tex = texture(image, v_uv);
    fragColor = vec4(pow(tex.rgb, vec3(2.2)), tex.a * mask * opacity);
}
"""

_ANNULUS_VERT = """
void main() {
    v_world = pos;
    gl_Position = ModelViewProjectionMatrix * vec4(pos, 0.0, 1.0);
}
"""

_ANNULUS_FRAG = """
void main() {
    float r = distance(v_world, center);
    float band = max(outerR - innerR, 1e-5);
    float s = min(max(softness, 1e-5), band * 0.48);
    float aOuter = 1.0 - smoothstep(outerR - s, outerR + s, r);
    float aInner = smoothstep(innerR - s, innerR + s, r);
    float a = aOuter * aInner;
    fragColor = vec4(pow(color.rgb, vec3(2.2)), color.a * a);
}
"""

_TEXTURED_QUAD_FRAG = """
void main() {
    vec4 tex = texture(image, v_uv);
    fragColor = vec4(pow(tex.rgb, vec3(2.2)), tex.a * opacity);
}
"""


# ---------------------------------------------------------------------------
# Compiled shader singletons
# ---------------------------------------------------------------------------

_shader_circle_fill: GPUShader | None = None
_shader_ring: GPUShader | None = None
_shader_tex_circle: GPUShader | None = None
_shader_annulus: GPUShader | None = None
_shader_tex_quad: GPUShader | None = None


def _build_circle_fill_shader() -> GPUShader:
    iface = GPUStageInterfaceInfo("sculpt_wheel_circle_fill_iface")
    iface.smooth('VEC2', "v_uv")

    info = GPUShaderCreateInfo()
    info.push_constant('MAT4', "ModelViewProjectionMatrix")
    info.push_constant('VEC4', "color")
    info.push_constant('FLOAT', "softness")
    info.vertex_in(0, 'VEC2', "pos")
    info.vertex_in(1, 'VEC2', "uv")
    info.vertex_out(iface)
    info.fragment_out(0, 'VEC4', "fragColor")
    info.vertex_source(_CIRCLE_FILL_VERT)
    info.fragment_source(_CIRCLE_FILL_FRAG)
    return create_from_info(info)


def _build_ring_shader() -> GPUShader:
    iface = GPUStageInterfaceInfo("sculpt_wheel_ring_iface")
    iface.smooth('VEC2', "v_uv")

    info = GPUShaderCreateInfo()
    info.push_constant('MAT4', "ModelViewProjectionMatrix")
    info.push_constant('VEC4', "color")
    info.push_constant('FLOAT', "innerRadius")
    info.push_constant('FLOAT', "outerRadius")
    info.push_constant('FLOAT', "softness")
    info.vertex_in(0, 'VEC2', "pos")
    info.vertex_in(1, 'VEC2', "uv")
    info.vertex_out(iface)
    info.fragment_out(0, 'VEC4', "fragColor")
    info.vertex_source(_RING_VERT)
    info.fragment_source(_RING_FRAG)
    return create_from_info(info)


def _build_tex_circle_shader() -> GPUShader:
    iface = GPUStageInterfaceInfo("sculpt_wheel_tex_circle_iface")
    iface.smooth('VEC2', "v_uv")

    info = GPUShaderCreateInfo()
    info.push_constant('MAT4', "ModelViewProjectionMatrix")
    info.push_constant('FLOAT', "opacity")
    info.push_constant('FLOAT', "softness")
    info.sampler(0, 'FLOAT_2D', "image")
    info.vertex_in(0, 'VEC2', "pos")
    info.vertex_in(1, 'VEC2', "uv")
    info.vertex_out(iface)
    info.fragment_out(0, 'VEC4', "fragColor")
    info.vertex_source(_TEXTURED_CIRCLE_VERT)
    info.fragment_source(_TEXTURED_CIRCLE_FRAG)
    return create_from_info(info)


def _build_annulus_shader() -> GPUShader:
    iface = GPUStageInterfaceInfo("sculpt_wheel_annulus_iface")
    iface.smooth('VEC2', "v_world")

    info = GPUShaderCreateInfo()
    info.push_constant('MAT4', "ModelViewProjectionMatrix")
    info.push_constant('VEC2', "center")
    info.push_constant('VEC4', "color")
    info.push_constant('FLOAT', "innerR")
    info.push_constant('FLOAT', "outerR")
    info.push_constant('FLOAT', "softness")
    info.vertex_in(0, 'VEC2', "pos")
    info.vertex_out(iface)
    info.fragment_out(0, 'VEC4', "fragColor")
    info.vertex_source(_ANNULUS_VERT)
    info.fragment_source(_ANNULUS_FRAG)
    return create_from_info(info)


def _build_tex_quad_shader() -> GPUShader:
    iface = GPUStageInterfaceInfo("sculpt_wheel_tex_quad_iface")
    iface.smooth('VEC2', "v_uv")

    info = GPUShaderCreateInfo()
    info.push_constant('MAT4', "ModelViewProjectionMatrix")
    info.push_constant('FLOAT', "opacity")
    info.sampler(0, 'FLOAT_2D', "image")
    info.vertex_in(0, 'VEC2', "pos")
    info.vertex_in(1, 'VEC2', "uv")
    info.vertex_out(iface)
    info.fragment_out(0, 'VEC4', "fragColor")
    info.vertex_source(_TEXTURED_CIRCLE_VERT)
    info.fragment_source(_TEXTURED_QUAD_FRAG)
    return create_from_info(info)


def _get_circle_fill_shader() -> GPUShader:
    global _shader_circle_fill
    if _shader_circle_fill is None:
        _shader_circle_fill = _build_circle_fill_shader()
    return _shader_circle_fill


def _get_ring_shader() -> GPUShader:
    global _shader_ring
    if _shader_ring is None:
        _shader_ring = _build_ring_shader()
    return _shader_ring


def _get_tex_circle_shader() -> GPUShader:
    global _shader_tex_circle
    if _shader_tex_circle is None:
        _shader_tex_circle = _build_tex_circle_shader()
    return _shader_tex_circle


def _get_annulus_shader() -> GPUShader:
    global _shader_annulus
    if _shader_annulus is None:
        _shader_annulus = _build_annulus_shader()
    return _shader_annulus


def _get_tex_quad_shader() -> GPUShader:
    global _shader_tex_quad
    if _shader_tex_quad is None:
        _shader_tex_quad = _build_tex_quad_shader()
    return _shader_tex_quad


# ---------------------------------------------------------------------------
# Quad geometry helper
# ---------------------------------------------------------------------------

def _quad_verts(cx: float, cy: float, half: float) -> Tuple[list, list, list]:
    """Return (positions, uvs, indices) for a screen-space quad centred at (cx, cy)."""
    positions = [
        (cx - half, cy - half),
        (cx + half, cy - half),
        (cx + half, cy + half),
        (cx - half, cy + half),
    ]
    uvs = [
        (0.0, 0.0),
        (1.0, 0.0),
        (1.0, 1.0),
        (0.0, 1.0),
    ]
    indices = [(0, 1, 2), (2, 3, 0)]
    return positions, uvs, indices


# ---------------------------------------------------------------------------
# Public draw functions
# ---------------------------------------------------------------------------

def draw_circle_fill(
    cx: float, cy: float, radius: float,
    color: Tuple[float, float, float, float],
    softness: float = 0.01,
) -> None:
    """Draw an anti-aliased filled circle."""
    shader = _get_circle_fill_shader()
    positions, uvs, indices = _quad_verts(cx, cy, radius)
    batch = batch_for_shader(shader, 'TRIS', {"pos": positions, "uv": uvs}, indices=indices)
    with CM_GPU_BLEND('ALPHA'):
        shader.bind()
        shader.uniform_float("color", color)
        shader.uniform_float("softness", softness)
        batch.draw(shader)


def draw_ring(
    cx: float, cy: float, radius: float,
    color: Tuple[float, float, float, float],
    thickness: float = 2.0,
    softness: float = 0.008,
) -> None:
    """Draw an anti-aliased ring (annulus)."""
    shader = _get_ring_shader()
    half = radius + thickness
    positions, uvs, indices = _quad_verts(cx, cy, half)
    batch = batch_for_shader(shader, 'TRIS', {"pos": positions, "uv": uvs}, indices=indices)

    outer_r = 0.5
    inner_r = 0.5 * (radius - thickness) / (radius + thickness)

    with CM_GPU_BLEND('ALPHA'):
        shader.bind()
        shader.uniform_float("color", color)
        shader.uniform_float("outerRadius", outer_r)
        shader.uniform_float("innerRadius", inner_r)
        shader.uniform_float("softness", softness)
        batch.draw(shader)


def draw_textured_circle(
    cx: float, cy: float, radius: float,
    texture: GPUTexture,
    opacity: float = 1.0,
    softness: float = 0.02,
) -> None:
    """Draw a texture clipped to a circle."""
    shader = _get_tex_circle_shader()
    positions, uvs, indices = _quad_verts(cx, cy, radius)
    batch = batch_for_shader(shader, 'TRIS', {"pos": positions, "uv": uvs}, indices=indices)
    with CM_GPU_BLEND('ALPHA'):
        shader.bind()
        shader.uniform_sampler("image", texture)
        shader.uniform_float("opacity", opacity)
        shader.uniform_float("softness", softness)
        batch.draw(shader)


def draw_annulus(
    cx: float,
    cy: float,
    outer_r: float,
    inner_r: float,
    color: Tuple[float, float, float, float],
    softness: float = 2.75,
) -> None:
    """Filled ring in pixel space (inner_r < r < outer_r).

    *softness* is the half-width of the antialiased edge on inner and outer
    boundaries, in **pixels** (symmetric ``smoothstep`` ramps).
    """
    if outer_r <= inner_r + 0.5:
        return
    shader = _get_annulus_shader()
    positions, _uvs, indices = _quad_verts(cx, cy, outer_r)
    batch = batch_for_shader(shader, 'TRIS', {"pos": positions}, indices=indices)
    with CM_GPU_BLEND('ALPHA'):
        shader.bind()
        shader.uniform_float("center", (cx, cy))
        shader.uniform_float("color", color)
        shader.uniform_float("innerR", inner_r)
        shader.uniform_float("outerR", outer_r)
        shader.uniform_float("softness", softness)
        batch.draw(shader)


def draw_textured_quad(
    cx: float,
    cy: float,
    half: float,
    texture: GPUTexture,
    opacity: float = 1.0,
) -> None:
    """Axis-aligned square with texture; alpha from texture (no circular mask)."""
    shader = _get_tex_quad_shader()
    positions, uvs, indices = _quad_verts(cx, cy, half)
    batch = batch_for_shader(shader, 'TRIS', {"pos": positions, "uv": uvs}, indices=indices)
    with CM_GPU_BLEND('ALPHA'):
        shader.bind()
        shader.uniform_sampler("image", texture)
        shader.uniform_float("opacity", opacity)
        batch.draw(shader)


# ---------------------------------------------------------------------------
# Wheel layout math
# ---------------------------------------------------------------------------

def compute_slot_radius_in_single_ring(ring_radius: float, count: int) -> float:
    """Compute the radius of each small slot circle so *count* fit around *ring_radius*."""
    if count <= 0:
        return 0.0
    if count == 1:
        return ring_radius * 0.4
    return ring_radius * sin(pi / count) / (1.0 + sin(pi / count))

def compute_slot_radius_in_double_ring(inner_radius: float, outer_radius: float, count: int, ring_padding: float = 8) -> float:
    """Compute slot radius for circles packed inside an annulus.

    The returned value is constrained by:
    - radial thickness available in the annulus (after ``ring_padding``), and
    - angular spacing at the annulus mid-radius for ``count`` slots.
    """
    if count <= 0:
        return 0.0
    if count == 1:
        return outer_radius * 0.4

    inner_radius = inner_radius + ring_padding
    outer_radius = outer_radius - ring_padding

    # Normalize radii ordering.
    inner_r = min(inner_radius, outer_radius)
    outer_r = max(inner_radius, outer_radius)

    # Keep slots away from annulus boundaries.
    # Slot centers sit on the annulus midline.
    center_radius = 0.5 * (inner_r + outer_r)

    # (1) Radial fit: each circle must stay inside annulus thickness.
    radial_limit = 0.5 * (outer_r - inner_r)

    # (2) Tangential fit: neighboring circles around the ring cannot overlap.
    tangential_limit = center_radius * sin(pi / count)

    return max(0.0, min(radial_limit, tangential_limit))

def compute_slot_positions_in_single_ring(
    cx: float, cy: float, ring_radius: float, count: int, slot_radius: float,
) -> list[Tuple[float, float]]:
    """Compute screen-space centre positions for *count* slots on a ring.

    The **first radial boundary** (start of slice 0, then clockwise) lies on the
    **180°** ray (left). Slice centers sit at π − (i + ½)·step.
    """
    if count <= 0:
        return []
    if count == 1:
        return [(cx - ring_radius, cy)]
    positions: list[Tuple[float, float]] = []
    angle_step = 2.0 * pi / count
    for i in range(count):
        angle = pi - (i + 0.5) * angle_step
        x = cx + (ring_radius - slot_radius) * cos(angle)
        y = cy + (ring_radius - slot_radius) * sin(angle)
        positions.append((x, y))
    return positions


def compute_slot_positions_in_double_ring(
    cx: float, cy: float, inner_radius: float, outer_radius: float, count: int
) -> list[Tuple[float, float]]:
    """Compute screen-space centre positions for *count* slots on a double ring. """
    mid_radius = 0.5 * (inner_radius + outer_radius)
    return compute_slot_positions_in_single_ring(cx, cy, mid_radius, count, 0.0)


def compute_custom_button_layout_count(num_buttons: int) -> int:
    """Even layout count between 4 and 10 (legacy wheel “tarta” spacing)."""
    if num_buttons <= 0:
        return 0
    n = min(10, max(4, num_buttons))
    if n % 2:
        n += 1
    return n


def map_custom_layout_indices(layout_count: int, num_buttons: int) -> list[int]:
    """For each layout slot, index into the active custom-button list or -1 if empty pad."""
    return [i if i < num_buttons else -1 for i in range(layout_count)]
