"""Weight-wheel helper math and drawing utilities."""

from __future__ import annotations

from math import atan2, cos, radians, sin
from typing import Sequence

from gpu.shader import create_from_info
from gpu.types import GPUShader, GPUShaderCreateInfo, GPUStageInterfaceInfo
from gpu_extras.batch import batch_for_shader

from ..core.gpu.state_control import CM_GPU_BLEND
from ..core.gpu.imm_2d import draw_lines
from .utils import _quad_verts
from .utils import draw_circle_fill, draw_ring


START_DEG = -45.0
SWEEP_DEG = 270.0
END_DEG = START_DEG + SWEEP_DEG


def clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


def weight_value_to_angle_deg(value: float) -> float:
    value = clamp01(value)
    return END_DEG - value * SWEEP_DEG


def angle_deg_to_weight_value(angle_deg: float) -> float:
    a = angle_deg
    if a < 0.0:
        a += 360.0
    if a >= 315.0 or a <= 225.0:
        arc = (a - 315.0) if a >= 315.0 else (a + 45.0)
        return clamp01(1.0 - arc / SWEEP_DEG)
    # Dead sector clamp (left side): snap to nearest end.
    return 0.0 if a < 270.0 else 1.0


def marker_points(
    cx: float,
    cy: float,
    inner_r: float,
    outer_r: float,
    count: int,
) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    lines: list[tuple[float, float]] = []
    buttons: list[tuple[float, float]] = []
    if count <= 0:
        return lines, buttons
    for i in range(count + 1):
        t = i / count
        a = radians(END_DEG - t * SWEEP_DEG)
        c = cos(a)
        s = sin(a)
        lines.append((cx + c * inner_r, cy + s * inner_r))
        lines.append((cx + c * outer_r, cy + s * outer_r))
        buttons.append((cx + c * (outer_r + (outer_r - inner_r) * 0.6), cy + s * (outer_r + (outer_r - inner_r) * 0.6)))
    return lines, buttons


def draw_weight_handle(
    cx: float,
    cy: float,
    inner_r: float,
    outer_r: float,
    value: float,
) -> None:
    a = radians(weight_value_to_angle_deg(value))
    p0 = (cx + cos(a) * inner_r, cy + sin(a) * inner_r)
    p1 = (cx + cos(a) * outer_r, cy + sin(a) * outer_r)
    draw_lines([p0, p1], (0.05, 0.05, 0.05, 0.92), line_width=4.4, strip=False)
    draw_lines([p0, p1], (1.0, 1.0, 1.0, 0.98), line_width=2.0, strip=False)


def draw_weight_markers(
    lines: Sequence[tuple[float, float]],
    marker_buttons: Sequence[tuple[float, float]],
    *,
    button_radius: float,
    hover_index: int = -1,
    interactive: bool = True,
) -> None:
    if lines:
        draw_lines(list(lines), (0.90, 0.90, 0.90, 0.95), line_width=1.7, strip=False)
    if not interactive:
        return
    for i, p in enumerate(marker_buttons):
        draw_circle_fill(p[0], p[1], button_radius, (0.016, 0.016, 0.016, 0.80), softness=0.10)
        col = (0.85, 0.85, .89, 1.0) if i == hover_index else (0.2, 0.2, 0.2, 0.8)
        draw_ring(p[0], p[1], button_radius, col, thickness=1.1, softness=0.08)


_WEIGHT_RING_VERT = """
void main() {
    v_uv = uv;
    gl_Position = ModelViewProjectionMatrix * vec4(pos, 0.0, 1.0);
}
"""

_WEIGHT_RING_FRAG = """
#define PI 3.14159265359
#define PI_4 (PI / 4.0)
#define ARC_HALF (3.0 * PI / 4.0)

vec3 hsv2rgb(vec3 c) {
    vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

void main() {
    // Match gl_PointCoord orientation from legacy shader.
    vec2 uv = vec2(v_uv.x, 1.0 - v_uv.y);
    vec2 cxy = 2.0 * uv - 1.0;
    float r = dot(cxy, cxy);
    float delta = fwidth(r);
    float alpha = 1.0 - smoothstep(1.0 - delta, 1.0 + delta, r);
    if (alpha < 0.05) {
        discard;
    }

    vec2 toCenter = vec2(0.5) - uv;
    float radius = length(toCenter) * 2.0;
    float minRad = clamp(ring_inner_ratio, 0.0, 0.999);
    if (radius < minRad || radius > 1.0) {
        discard;
    }

    // Match legacy wheel shader math.
    float angle = atan(toCenter.x, toCenter.y); // swapped args on purpose
    if (abs(angle) > ARC_HALF) {
        discard;
    }
    angle *= 1.2;

    float minRad2 = minRad + 0.03;
    float maxRad2 = 1.0 - 0.03;
    if (radius < minRad2) {
        alpha = smoothstep(minRad, minRad2, radius);
    } else if (radius > maxRad2) {
        alpha = smoothstep(1.0, maxRad2, radius);
    }

    // Flip orientation and use hue ramp for smooth cyan/yellow transitions:
    // blue(240) -> cyan(180) -> green(120) -> yellow(60) -> red(0).
    float u = 1.0 - clamp((angle + ARC_HALF) / (2.0 * ARC_HALF), 0.0, 1.0);
    float hue = mix(2.0 / 3.0, 0.0, u);
    vec3 co = hsv2rgb(vec3(hue, 1.0, 1.0));
    fragColor = vec4(pow(co, vec3(2.2)), alpha);
}
"""

_shader_weight_ring: GPUShader | None = None


def _get_weight_ring_shader() -> GPUShader:
    global _shader_weight_ring
    if _shader_weight_ring is None:
        iface = GPUStageInterfaceInfo("spwheel_weight_ring_iface")
        iface.smooth("VEC2", "v_uv")
        info = GPUShaderCreateInfo()
        info.push_constant("MAT4", "ModelViewProjectionMatrix")
        info.push_constant("FLOAT", "ring_inner_ratio")
        info.vertex_in(0, "VEC2", "pos")
        info.vertex_in(1, "VEC2", "uv")
        info.vertex_out(iface)
        info.fragment_out(0, "VEC4", "fragColor")
        info.vertex_source(_WEIGHT_RING_VERT)
        info.fragment_source(_WEIGHT_RING_FRAG)
        _shader_weight_ring = create_from_info(info)
    return _shader_weight_ring


def draw_weight_hue_ring(cx: float, cy: float, outer_radius_px: float, inner_radius_px: float) -> None:
    if outer_radius_px <= 0.0:
        return
    shader = _get_weight_ring_shader()
    positions, uvs, indices = _quad_verts(cx, cy, outer_radius_px)
    batch = batch_for_shader(shader, "TRIS", {"pos": positions, "uv": uvs}, indices=indices)
    ratio = 0.8 if outer_radius_px <= 0.0 else max(0.0, min(0.999, inner_radius_px / outer_radius_px))
    with CM_GPU_BLEND("ALPHA"):
        shader.bind()
        shader.uniform_float("ring_inner_ratio", float(ratio))
        batch.draw(shader)
