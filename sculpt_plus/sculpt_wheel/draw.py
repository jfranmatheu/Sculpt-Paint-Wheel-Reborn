"""GPU draw callback for the sculpt wheel overlay."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bpy.types import Context

from ..core.gpu.imm_2d import draw_text
from ..core.gpu.state_control import CM_GPU_BLEND
from .gpu_utils import (
    draw_annulus,
    draw_circle_fill,
    draw_ring,
    draw_textured_circle,
    draw_textured_quad,
)
from .gpu_tarta import (
    draw_pie_split_ring,
    draw_ring_blr_gamma,
)
from .brush_assets import get_wheel_brush_preview_texture
from .custom_buttons import get_custom_button_texture
if TYPE_CHECKING:
    from .op_sculpt_wheel import SculptWheelOperator


# Dark-mode wheel: near-black base, cool-neutral grays, muted accents (no harsh whites).
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
COL_PIE_TARTA = (0.22, 0.225, 0.24, 0.97)
COL_PIE_OUTLINE = (0.40, 0.42, 0.46, 0.62)


def _wheel_inner_radius(op: "SculptWheelOperator", wheel_r: float) -> float:
    """Inner edge of the main wheel ring: flush with tarta outer when present."""
    if getattr(op, "tarta_ring_outer_radius", 0.0) > 1.0:
        return float(op.tarta_ring_outer_radius)
    return max(28.0, wheel_r * 0.30)


def draw_wheel(context: Context, op: 'SculptWheelOperator') -> None:
    """Entry point called from the modal operator's ``draw_2d``."""
    cx = op.wheel_center_x
    cy = op.wheel_center_y
    radius = op.wheel_radius
    slot_radius = op.slot_radius
    icon_scale = op.icon_scale
    inner_r = _wheel_inner_radius(op, radius)
    inner_r = min(inner_r, radius - 32.0)

    with CM_GPU_BLEND('ALPHA'):
        if inner_r < radius - 1.0:
            draw_annulus(cx, cy, radius, max(0.0, inner_r), COL_BASE)

        draw_ring(cx, cy, radius, COL_BASE_RING, thickness=1.25, softness=0.008)
        draw_ring_blr_gamma(cx, cy, max(8.0, radius - 5.0), 0.02, 0.01, COL_WHEEL_RING_SOFT_OUT)
        if inner_r > 2.0:
            draw_ring_blr_gamma(
                cx, cy, max(8.0, inner_r + 5.0), 0.022, 0.014, COL_WHEEL_RING_SOFT_IN,
            )

        _draw_custom_buttons(op, cx, cy, icon_scale)
        _draw_slots(context, op, cx, cy, slot_radius, icon_scale)

        if op.brush_set_count > 1:
            _draw_brush_set_dots(op, cx, cy, radius)


def _draw_custom_buttons(op: 'SculptWheelOperator', cx: float, cy: float, icon_scale: float) -> None:
    """Pie ring (DiRNGS_SPLITANG) + icons on the tarta radius (legacy px/sculpt.py order)."""
    st = getattr(op, "_wheel_storage", None)
    if st is None or len(st.custom_buttons) == 0:
        return
    layout_n = op.custom_layout_n
    if layout_n <= 0 or op.tarta_ring_outer_radius <= 0.0:
        return

    hover_sec = op.hover_custom_layout_slot if op.hover_custom_layout_slot >= 0 else -1
    draw_pie_split_ring(
        cx,
        cy,
        op.tarta_ring_outer_radius,
        op.tarta_inner_ratio,
        layout_n,
        hover_sec,
        COL_PIE_TARTA,
        inner_soft=0.06,
    )

    cr = op.custom_radius
    if cr <= 0:
        draw_ring_blr_gamma(
            cx, cy, op.tarta_ring_outer_radius, 0.025, 0.01, COL_PIE_OUTLINE,
        )
        return

    # Square icons, uncropped (full texture alpha), slightly smaller than slot radius.
    half = cr * 0.52 * icon_scale
    for i, (sx, sy) in enumerate(op.custom_positions):
        if i >= len(op.custom_layout_map):
            break
        bid = op.custom_layout_map[i]
        if bid < 0:
            continue
        btn = st.custom_buttons[bid]
        is_hov = bid == op.hover_custom_index
        tex = get_custom_button_texture(btn.image_path)
        if tex is not None:
            h = half * (1.08 if is_hov else 1.0)
            draw_textured_quad(
                sx, sy, h, tex, opacity=1.0 if is_hov else 0.94,
            )
        elif btn.name:
            draw_text(btn.name[:10], sx, sy, size=9.0, color=COL_TEXT, align='CENTER', shadow=True)

    draw_ring_blr_gamma(
        cx, cy, op.tarta_ring_outer_radius, 0.025, 0.01, COL_PIE_OUTLINE,
    )


def _draw_slots(
    context: Context,
    op: 'SculptWheelOperator',
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
        entry = brushes[i]
        is_active = i == op.active_brush_slot_index
        is_hovered = i == op.hover_index

        draw_circle_fill(sx, sy, slot_radius, COL_SLOT_BG, softness=0.015)
        if is_hovered:
            draw_circle_fill(sx, sy, slot_radius, COL_SLOT_HOVER, softness=0.015)

        icon_r = slot_radius * icon_scale
        tex = get_wheel_brush_preview_texture(entry)
        if tex is not None:
            draw_textured_circle(sx, sy, icon_r, tex, opacity=1.0, softness=0.025)

        if is_active:
            draw_ring(sx, sy, slot_radius, COL_SLOT_ACTIVE_RING, thickness=2.0, softness=0.012)
        elif is_hovered:
            draw_ring(sx, sy, slot_radius, COL_SLOT_HOVER_RING, thickness=1.5, softness=0.012)
        else:
            draw_ring(sx, sy, slot_radius, COL_SLOT_RING, thickness=1.0, softness=0.012)

        name = str(entry.get("brush_name") or "")
        if op.show_names and name:
            draw_text(
                name,
                sx, sy - slot_radius - 10,
                size=11.0,
                color=COL_TEXT,
                align='CENTER',
                shadow=True,
            )


def _draw_brush_set_dots(
    op: 'SculptWheelOperator',
    cx: float, cy: float,
    wheel_radius: float,
) -> None:
    count = op.brush_set_count
    active = op.active_brush_set_index
    dot_radius = 3.0
    spacing = 10.0
    total_w = (count - 1) * spacing
    start_x = cx - total_w * 0.5
    dot_y = cy - wheel_radius - 16

    for i in range(count):
        dx = start_x + i * spacing
        col = COL_TOOLSET_DOT_ACTIVE if i == active else COL_TOOLSET_DOT
        draw_circle_fill(dx, dot_y, dot_radius, col, softness=0.04)
