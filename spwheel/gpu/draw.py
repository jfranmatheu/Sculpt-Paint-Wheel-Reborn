"""
Wheel overlay GPU: pie-ring (“tarta”) shaders plus ``draw_wheel`` composition.

Merges the former ``gpu_tarta`` and modal ``draw`` modules. For generic 2D
shader codegen examples see ``sculpt_paint_wheel.core.gpu.draw`` (different package).
"""

from __future__ import annotations

from typing import Any, Sequence, Tuple

from bpy.types import Context
from gpu.shader import create_from_info
from gpu.types import GPUShader, GPUShaderCreateInfo, GPUStageInterfaceInfo, GPUTexture

from ..core.gpu.imm_2d import draw_text
from ..core.gpu.state_control import CM_GPU_BLEND

from .brush_preview import get_brush_preview_texture
from .button_texture import get_custom_button_texture
from .colpk import draw_colpk_hue_ring, draw_colpk_sat_arc, draw_colpk_val_arc
from .colpk_helpers import (
    S_ANGLE_BOT,
    S_ANGLE_TOP,
    V_ANGLE_BOT,
    V_ANGLE_TOP,
    colpk_handle_positions,
    colpk_linked_preview_enabled,
    get_sculpt_brush_rgb,
)
from .utils import (
    draw_annulus,
    draw_circle_fill,
    draw_ring,
    draw_textured_circle,
    draw_textured_quad,
    quad_batch,
)


# =============================================================================
# Tarta (pie ring + soft ring + boosted textured disc)
# =============================================================================

_TARTA_VERT = """
void main() {
    v_uv = uv;
    gl_Position = ModelViewProjectionMatrix * vec4(pos, 0.0, 1.0);
}
"""

_PIE_RING_FRAG = """
vec3 srgb_to_lin(vec3 c) {
  /* Exact sRGB -> linear (pow(c, 2.2) crushes the darks). */
  return mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)), step(0.04045, c));
}
float sector_kind(int s) {
    if (s < 0 || s > 30) {
        return 0.0;
    }
    return float((sectorKindsMask >> s) & 1);
}

void main() {
    const float PI = 3.14159265359;
    const float TWO_PI = 6.28318530718;
    const float SEAM_W = 0.018;
    const float SPOKE_DARK = 0.22;
    const float RIM_W = 0.032;
    const vec3 RIM_RGB = vec3(0.36, 0.38, 0.42);

    vec2 toCenter = vec2(0.5) - v_uv;
    vec2 outward = v_uv - vec2(0.5);
    float radius = length(toCenter) * 2.0;
    if (radius < innerRatio) {
        discard;
    }
    if (radius > 1.0) {
        discard;
    }

    int n = int(n_sectors + 0.5);
    int hv = int(hover_sector);
    if (n < 1) {
        discard;
    }

    float angle = atan(outward.y, outward.x);
    float step = TWO_PI / float(n);
    float shifted = mod(PI - angle + TWO_PI, TWO_PI);
    float pos_in_seg = shifted / step;

    int sec = int(floor(pos_in_seg + 1e-5));
    if (sec >= n) {
        sec = n - 1;
    }
    if (sec < 0) {
        sec = 0;
    }

    vec4 color = mix(pieColorPopup, pieColorOp, sector_kind(sec));

    float dist_from_spoke = min(fract(pos_in_seg), 1.0 - fract(pos_in_seg));
    float seam = 1.0 - smoothstep(0.0, SEAM_W, dist_from_spoke);
    color.rgb *= mix(1.0, SPOKE_DARK, seam);

    if (hv >= 0 && sec == hv) {
        float radial = clamp((radius - innerRatio) / max(1e-5, 1.0 - innerRatio), 0.0, 1.0);
        color.rgb = mix(color.rgb, color.rgb * 1.75, radial * 0.9);
    }

    float rim_in = 1.0 - smoothstep(0.0, RIM_W, abs(radius - innerRatio));
    float rim_out = 1.0 - smoothstep(0.0, RIM_W * 1.1, abs(radius - 1.0));
    float rims = max(rim_in, rim_out);
    color.rgb = mix(color.rgb, RIM_RGB, rims * 0.58);

    float alpha = color.a;
    if (radius >= innerRatio && radius < innerRatio + inner_soft * 2.5) {
        alpha *= smoothstep(innerRatio, innerRatio + inner_soft, radius);
    }
    if (radius <= 1.0 && radius > 1.0 - outer_soft * 2.5) {
        float outer_t = clamp((1.0 - radius) / max(1e-5, outer_soft), 0.0, 1.0);
        alpha *= outer_t * outer_t * (3.0 - 2.0 * outer_t);
    }

    fragColor = vec4(srgb_to_lin(color.rgb), alpha);
}
"""

_RING_BLR_FRAG = """
vec3 srgb_to_lin(vec3 c) {
  /* Exact sRGB -> linear (pow(c, 2.2) crushes the darks). */
  return mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)), step(0.04045, c));
}
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

    fragColor = vec4(srgb_to_lin(co.rgb), co.a * alpha * s);
}
"""

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
    iface = GPUStageInterfaceInfo("sculpt_wheel_pie_iface_v6_outward_angle")
    iface.smooth("VEC2", "v_uv")
    info = GPUShaderCreateInfo()
    info.push_constant("MAT4", "ModelViewProjectionMatrix")
    info.push_constant("VEC4", "pieColorPopup")
    info.push_constant("VEC4", "pieColorOp")
    info.push_constant("INT", "sectorKindsMask")
    info.push_constant("FLOAT", "innerRatio")
    info.push_constant("FLOAT", "inner_soft")
    info.push_constant("FLOAT", "outer_soft")
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


_MAX_TARTA_SECTORS = 10


def _pack_sector_kinds_mask(kinds: Sequence[int]) -> int:
    mask = 0
    for i, kind in enumerate(kinds[:_MAX_TARTA_SECTORS]):
        if int(kind) & 1:
            mask |= (1 << i)
    return mask


def draw_pie_split_ring(
    cx: float,
    cy: float,
    outer_radius_px: float,
    inner_ratio: float,
    n_sectors: int,
    hover_sector: int,
    color_popup: Tuple[float, float, float, float],
    color_operator: Tuple[float, float, float, float],
    sector_kinds: Sequence[int],
    inner_soft: float = 0.08,
    outer_soft: float = 0.08,
) -> None:
    if n_sectors <= 0 or outer_radius_px <= 0.0:
        return
    sk = list(sector_kinds[:n_sectors])
    sector_mask = _pack_sector_kinds_mask(sk)
    shader = _get_pie_ring_shader()
    batch = quad_batch(shader, cx, cy, outer_radius_px)
    with CM_GPU_BLEND("ALPHA"):
        shader.bind()
        shader.uniform_float("pieColorPopup", color_popup)
        shader.uniform_float("pieColorOp", color_operator)
        shader.uniform_int("sectorKindsMask", sector_mask)
        shader.uniform_float("innerRatio", float(inner_ratio))
        shader.uniform_float("inner_soft", float(inner_soft))
        shader.uniform_float("outer_soft", float(outer_soft))
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
    if radius_px <= 0.0:
        return
    shader = _get_ring_blr_shader()
    batch = quad_batch(shader, cx, cy, radius_px)
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
    shader = _get_tex_boost_shader()
    batch = quad_batch(shader, cx, cy, radius)
    with CM_GPU_BLEND("ALPHA"):
        shader.bind()
        shader.uniform_sampler("image", texture)
        shader.uniform_float("boost", float(boost))
        shader.uniform_float("softness", float(softness))
        batch.draw(shader)


# =============================================================================
# Wheel overlay (modal draw_2d)
# =============================================================================

COL_BASE = (0.075, 0.078, 0.085, 0.97)
COL_BASE_RING = (0.28, 0.30, 0.34, 0.38)
COL_WHEEL_RING_SOFT_OUT = (0.22, 0.24, 0.28, 0.45)
COL_WHEEL_RING_SOFT_IN = (0.08, 0.085, 0.095, 0.72)
COL_SLOT_BG = (0.10, 0.105, 0.12, 0.88)
COL_SLOT_HOVER = (0.20, 0.22, 0.28, 0.42)
COL_SLOT_ACTIVE_RING = (0.78, 0.62, 0.22, 0.92)
COL_SLOT_HOVER_RING = (0.40, 0.44, 0.50, 0.62)
COL_SLOT_RING = (0.16, 0.16, 0.2, 0.97)
COL_TEXT = (0.70, 0.72, 0.76, 0.98)
COL_TOOLSET_DOT = (0.32, 0.34, 0.38, 0.55)
COL_TOOLSET_DOT_ACTIVE = (0.72, 0.60, 0.26, 0.88)
COL_PIE_TARTA = (0.19, 0.19, 0.21, 0.97)
COL_PIE_TARTA_OP = (0.13, 0.16, 0.24, 0.97)
COL_PIE_OUTLINE = (0.24, 0.24, 0.26, 0.97)


def _wheel_inner_radius(op: Any, wheel_r: float) -> float:
    if getattr(op, "tarta_ring_outer_radius", 0.0) > 1.0:
        return float(op.tarta_ring_outer_radius)
    return max(28.0, wheel_r * 0.30)


def draw_wheel(context: Context, op: Any) -> None:
    """Entry point for the modal operator ``draw_2d`` callback."""
    cx = op.wheel_center_x
    cy = op.wheel_center_y
    radius = op.wheel_radius
    slot_radius = op.slot_radius
    icon_scale = op.icon_scale
    inner_r = _wheel_inner_radius(op, radius)
    inner_r = min(inner_r, radius - 32.0)

    base_col = (
        tuple(op.wheel_base_color)
        if len(getattr(op, "wheel_base_color", ())) == 4
        else COL_BASE
    )

    with CM_GPU_BLEND('ALPHA'):
        if inner_r < radius - 1.0:
            draw_annulus(cx, cy, radius, max(0.0, inner_r), base_col, softness=1.2)

        _draw_custom_buttons(op, cx, cy, icon_scale)
        _draw_color_pickers(context, op)
        _draw_slots(context, op, cx, cy, slot_radius, icon_scale)

        if getattr(op, "total_pages", 1) > 1 and getattr(op, "active_page_title", ""):
            _draw_page_title(op, cx, cy, radius)
        if getattr(op, "total_pages", 1) > 1:
            _draw_page_dots(op, cx, cy, radius)


def _draw_custom_buttons(op: Any, cx: float, cy: float, icon_scale: float) -> None:
    coll = getattr(op, "_active_custom_buttons", None)
    if coll is None or len(coll) == 0:
        return
    layout_n = op.custom_layout_n
    if layout_n <= 0 or op.tarta_ring_outer_radius <= 0.0:
        return

    hover_sec = op.hover_custom_layout_slot if op.hover_custom_layout_slot >= 0 else -1

    kinds: list[int] = []
    for si in range(layout_n):
        if si >= len(op.custom_layout_map):
            kinds.append(0)
            continue
        bid = op.custom_layout_map[si]
        if bid < 0:
            kinds.append(0)
            continue
        btn = coll[bid]
        kinds.append(1 if getattr(btn, "type", "") == "OPERATOR" else 0)

    draw_pie_split_ring(
        cx, cy,
        op.tarta_ring_outer_radius,
        op.tarta_inner_ratio,
        layout_n,
        hover_sec,
        COL_PIE_TARTA,
        COL_PIE_TARTA_OP,
        kinds,
        inner_soft=0.025,
        outer_soft=0.025,
    )

    cr = op.custom_radius
    if cr <= 0:
        return

    half = cr * 0.85 * icon_scale
    for i, (sx, sy) in enumerate(op.custom_positions):
        if i >= len(op.custom_layout_map):
            break
        bid = op.custom_layout_map[i]
        if bid < 0:
            continue
        btn = coll[bid]
        is_hov = bid == op.hover_custom_index
        tex = get_custom_button_texture(btn.image_path)
        if tex is not None:
            h = half * (1.08 if is_hov else 1.0)
            draw_textured_quad(
                sx, sy, h, tex, opacity=1.0 if is_hov else 0.94,
            )
        elif btn.name:
            draw_text(btn.name[:10], sx, sy, size=9.0, color=COL_TEXT, align='CENTER', shadow=True)


def _draw_color_pickers(context: Context, op: Any) -> None:
    if not getattr(op, "show_color_picker", False):
        return
    cx = op.wheel_center_x
    cy = op.wheel_center_y
    hi = float(getattr(op, "colpk_hue_inner_r", 0.0))
    ho = float(getattr(op, "colpk_hue_outer_r", 0.0))
    si = float(getattr(op, "colpk_sv_inner_r", 0.0))
    so = float(getattr(op, "colpk_sv_outer_r", 0.0))
    if ho <= 0.0 or so <= 0.0:
        return

    rgb = get_sculpt_brush_rgb(context)
    from mathutils import Color

    c = Color()
    c.r, c.g, c.b = rgb
    h, s, v = float(c.h), float(c.s), float(c.v)

    if colpk_linked_preview_enabled(context):
        draw_colpk_hue_ring(cx, cy, ho, hi, s, v)
        draw_colpk_sat_arc(cx, cy, so, si, S_ANGLE_TOP, S_ANGLE_BOT, h, v)
        draw_colpk_val_arc(cx, cy, so, si, V_ANGLE_TOP, V_ANGLE_BOT, h, s)
    else:
        draw_colpk_hue_ring(cx, cy, ho, hi, 1.0, 1.0)
        draw_colpk_sat_arc(cx, cy, so, si, S_ANGLE_TOP, S_ANGLE_BOT, h, 1.0)
        draw_colpk_val_arc(cx, cy, so, si, V_ANGLE_TOP, V_ANGLE_BOT, h, 1.0)

    hr = max(3.0, op.wheel_radius * 0.018)
    col_outline = (0.82, 0.84, 0.88, 0.92)
    col_fill = (0.06, 0.062, 0.07, 0.96)
    for hp in colpk_handle_positions(op, context):
        if hp is None:
            continue
        hx, hy = hp
        draw_circle_fill(hx, hy, hr, col_fill, softness=0.12)
        draw_ring(hx, hy, hr, col_outline, thickness=1.15, softness=0.05)


def _draw_slots(
    _context: Context,
    op: Any,
    cx: float, cy: float,
    slot_radius: float,
    icon_scale: float,
) -> None:
    positions = op.slot_positions
    brushes = op.brushes
    if not brushes:
        return

    for i, (sx, sy) in enumerate(positions):
        if i >= len(brushes):
            break
        brush = brushes[i]
        is_active = i == op.active_brush_slot_index
        is_hovered = i == op.hover_index

        draw_circle_fill(sx, sy, slot_radius, COL_SLOT_BG, softness=0.015)
        if is_hovered:
            draw_circle_fill(sx, sy, slot_radius, COL_SLOT_HOVER, softness=0.015)

        icon_r = slot_radius * icon_scale
        tex = get_brush_preview_texture(brush.preview.path, brush.name) if brush.preview.path else None
        if tex is not None:
            draw_textured_circle(sx, sy, icon_r, tex, opacity=1.0, softness=0.025)

        if is_active:
            draw_ring(sx, sy, slot_radius, COL_SLOT_ACTIVE_RING, thickness=2.0, softness=0.012)
        elif is_hovered:
            draw_ring(sx, sy, slot_radius, COL_SLOT_HOVER_RING, thickness=1.5, softness=0.012)
        else:
            draw_ring(sx, sy, slot_radius, COL_SLOT_RING, thickness=1.0, softness=0.012)

        name = brush.name or ""
        if op.show_names and name:
            draw_text(
                name,
                sx, sy - slot_radius - 10,
                size=11.0,
                color=COL_TEXT,
                align='CENTER',
                shadow=True,
            )


def _draw_page_title(
    op: Any,
    cx: float, cy: float,
    wheel_radius: float,
) -> None:
    title = (getattr(op, "active_page_title", "") or "").strip()
    if not title:
        return
    ty = cy - wheel_radius - (28.0 if getattr(op, "total_pages", 1) > 1 else 14.0)
    draw_text(
        title[:48],
        cx,
        ty - 10.0,
        size=10.0,
        color=COL_TEXT,
        align="CENTER",
        shadow=True,
    )


def _draw_page_dots(
    op: Any,
    cx: float, cy: float,
    wheel_radius: float,
) -> None:
    count = int(getattr(op, "total_pages", 1))
    active = int(getattr(op, "active_page", 0))
    if count <= 1:
        return
    dot_radius = 3.0
    spacing = min(10.0, max(5.0, 180.0 / max(count, 1)))
    total_w = (count - 1) * spacing
    start_x = cx - total_w * 0.5
    dot_y = cy - wheel_radius - 14.0

    for i in range(count):
        dx = start_x + i * spacing
        col = COL_TOOLSET_DOT_ACTIVE if i == active else COL_TOOLSET_DOT
        draw_circle_fill(dx, dot_y, dot_radius, col, softness=0.04)
