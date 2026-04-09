"""GPU draw callback for the sculpt wheel overlay."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bpy.types import Context

from ..core.gpu.imm_2d import draw_text
from ..core.gpu.state_control import CM_GPU_BLEND
from .gpu_utils import (
    draw_circle_fill,
    draw_ring,
    draw_textured_circle,
)
from .gpu_tarta import (
    draw_pie_split_ring,
    draw_ring_blr_gamma,
    draw_textured_circle_boost,
)
from .brush_assets import find_brush_for_slot, get_brush_preview_texture
from .custom_buttons import get_custom_button_texture
from .sculpt_paint_compat import get_sculpt_unified_paint_settings

if TYPE_CHECKING:
    from .op_sculpt_wheel import SculptWheelOperator


# Reference wheel: outer ~#1A1A1A, pie ~#333, pad ~#555, active gold ~#F0C040
COL_BASE = (0.102, 0.102, 0.102, 0.94)
COL_BASE_RING = (0.48, 0.48, 0.50, 0.55)
COL_SLOT_BG = (0.14, 0.14, 0.15, 0.92)
COL_SLOT_HOVER = (0.35, 0.35, 0.38, 0.35)
COL_SLOT_ACTIVE_RING = (0.941, 0.753, 0.251, 0.98)
COL_SLOT_HOVER_RING = (0.72, 0.72, 0.76, 0.88)
COL_TEXT = (0.88, 0.88, 0.90, 1.0)
COL_PAD_LABEL = (0.78, 0.78, 0.82, 0.92)
COL_TOOLSET_DOT = (0.55, 0.55, 0.58, 0.75)
COL_TOOLSET_DOT_ACTIVE = (0.94, 0.78, 0.28, 1.0)
COL_EDIT_RING = (0.95, 0.50, 0.15, 0.92)
COL_EDIT_RING_2 = (0.95, 0.60, 0.25, 0.88)
COL_GESTURE_PAD = (0.333, 0.333, 0.333, 0.96)
COL_GESTURE_HOVER = (0.40, 0.40, 0.43, 0.40)
COL_PIE_TARTA = (0.20, 0.20, 0.20, 0.96)
COL_PIE_OUTLINE = (0.70, 0.70, 0.74, 0.92)


def draw_wheel(context: Context, op: 'SculptWheelOperator') -> None:
    """Entry point called from the modal operator's ``draw_2d``."""
    if op._gesture_state == 'drag' and op._gesture_axis is not None:
        with CM_GPU_BLEND('ALPHA'):
            _draw_gesture_overlay(context, op)
        return

    cx = op.wheel_center_x
    cy = op.wheel_center_y
    radius = op.wheel_radius
    slot_radius = op.slot_radius
    icon_scale = op.icon_scale

    with CM_GPU_BLEND('ALPHA'):
        draw_circle_fill(cx, cy, radius, COL_BASE, softness=0.005)

        if op.wheel_ui_mode == 'EDIT':
            draw_ring(cx, cy, radius - 4.0, COL_EDIT_RING, thickness=2.0, softness=0.008)
            draw_ring(cx, cy, radius - 6.0, COL_EDIT_RING_2, thickness=1.5, softness=0.008)
        else:
            draw_ring(cx, cy, radius, COL_BASE_RING, thickness=1.2, softness=0.008)
            draw_ring_blr_gamma(cx, cy, max(8.0, radius - 6.0), 0.02, 0.01, (0.38, 0.38, 0.40, 0.88))
            draw_ring_blr_gamma(cx, cy, max(6.0, radius - 8.0), 0.02, 0.01, (0.12, 0.12, 0.13, 0.90))

        _draw_gesture_pad(context, op, cx, cy)
        _draw_custom_buttons(op, cx, cy, icon_scale)
        _draw_slots(op, cx, cy, slot_radius, icon_scale)

        if op.toolset_count > 1:
            _draw_toolset_dots(op, cx, cy, radius)

        _draw_edit_toggle(op)


def _draw_gesture_pad(context: Context, op: 'SculptWheelOperator', cx: float, cy: float) -> None:
    r = op.gesture_pad_radius
    if r <= 0:
        return
    draw_circle_fill(cx, cy, r, COL_GESTURE_PAD, softness=0.018)
    if op.hover_gesture_pad and op.wheel_ui_mode == 'PICKER':
        draw_circle_fill(cx, cy, r, COL_GESTURE_HOVER, softness=0.022)
    draw_ring_blr_gamma(cx, cy, r, 0.05, 0.02, (0.72, 0.72, 0.76, 0.95))
    if getattr(op, "_gesture_state", None) == 'drag':
        draw_ring_blr_gamma(cx, cy, r, 0.07, 0.012, (0.85, 0.82, 0.45, 0.9))
    elif op.hover_gesture_pad and op.wheel_ui_mode == 'PICKER':
        draw_ring_blr_gamma(cx, cy, r, 0.07, 0.012, (0.88, 0.86, 0.55, 0.88))

    brush = context.tool_settings.sculpt.brush
    if (
        op.wheel_ui_mode == 'PICKER'
        and brush is not None
        and getattr(op, "_gesture_state", None) != 'drag'
    ):
        draw_text(
            "PAD",
            cx,
            cy,
            size=max(12.0, r * 0.36),
            color=COL_PAD_LABEL,
            align='CENTER',
            shadow=True,
        )


def _draw_custom_buttons(op: 'SculptWheelOperator', cx: float, cy: float, icon_scale: float) -> None:
    """Pie ring (DiRNGS_SPLITANG) + icons on the tarta radius (legacy px/sculpt.py order)."""
    data = op._wheel_data
    if data is None or len(data.custom_buttons) == 0:
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

    dec_rad = cr * 0.9 * icon_scale
    for i, (sx, sy) in enumerate(op.custom_positions):
        if i >= len(op.custom_layout_map):
            break
        bid = op.custom_layout_map[i]
        if bid < 0:
            continue
        btn = data.custom_buttons[bid]
        is_hov = bid == op.hover_custom_index
        tex = get_custom_button_texture(btn.image_path)
        if tex is not None:
            if is_hov:
                draw_textured_circle_boost(sx, sy, dec_rad, tex, boost=1.25, softness=0.03)
            else:
                draw_textured_circle(sx, sy, dec_rad, tex, opacity=1.0, softness=0.03)
        elif btn.name:
            draw_text(btn.name[:10], sx, sy, size=9.0, color=COL_TEXT, align='CENTER', shadow=True)

    draw_ring_blr_gamma(
        cx, cy, op.tarta_ring_outer_radius, 0.025, 0.01, COL_PIE_OUTLINE,
    )


def _draw_slots(
    op: 'SculptWheelOperator',
    cx: float, cy: float,
    slot_radius: float,
    icon_scale: float,
) -> None:
    positions = op.slot_positions
    toolset = op.active_toolset
    if toolset is None:
        return
    slots = toolset.slots
    edit = op.wheel_ui_mode == 'EDIT'

    for i, (sx, sy) in enumerate(positions):
        if i >= len(slots):
            break
        slot = slots[i]
        is_active = (i == toolset.active_slot_index)
        is_hovered = (i == op.hover_index)

        draw_circle_fill(sx, sy, slot_radius, COL_SLOT_BG, softness=0.015)
        if is_hovered:
            draw_circle_fill(sx, sy, slot_radius, COL_SLOT_HOVER, softness=0.015)

        brush = find_brush_for_slot(slot)
        if brush is not None:
            tex = get_brush_preview_texture(brush)
            if tex is not None:
                icon_r = slot_radius * icon_scale
                draw_textured_circle(sx, sy, icon_r, tex, opacity=1.0, softness=0.025)

        if is_active:
            draw_ring(sx, sy, slot_radius, COL_SLOT_ACTIVE_RING, thickness=2.0, softness=0.012)
        elif is_hovered:
            draw_ring(sx, sy, slot_radius, COL_SLOT_HOVER_RING, thickness=1.5, softness=0.012)

        if edit and is_hovered:
            draw_ring(sx, sy, slot_radius * 0.55, (1.0, 0.85, 0.2, 0.7), thickness=2.0, softness=0.02)

        if op.show_names and slot.display_name:
            draw_text(
                slot.display_name,
                sx, sy - slot_radius - 10,
                size=11.0,
                color=COL_TEXT,
                align='CENTER',
                shadow=True,
            )


def _draw_toolset_dots(
    op: 'SculptWheelOperator',
    cx: float, cy: float,
    wheel_radius: float,
) -> None:
    count = op.toolset_count
    active = op.active_toolset_idx
    dot_radius = 3.0
    spacing = 10.0
    total_w = (count - 1) * spacing
    start_x = cx - total_w * 0.5
    dot_y = cy - wheel_radius - 16

    for i in range(count):
        dx = start_x + i * spacing
        col = COL_TOOLSET_DOT_ACTIVE if i == active else COL_TOOLSET_DOT
        draw_circle_fill(dx, dot_y, dot_radius, col, softness=0.04)


def _draw_edit_toggle(op: 'SculptWheelOperator') -> None:
    tx, ty = op.edit_toggle_x, op.edit_toggle_y
    tr = op.edit_toggle_radius
    draw_circle_fill(tx, ty, tr, (0.26, 0.26, 0.28, 0.88), softness=0.04)
    draw_ring(tx, ty, tr, (0.62, 0.62, 0.66, 0.92), thickness=1.2, softness=0.03)
    label = "Ed" if op.wheel_ui_mode == 'PICKER' else "Ok"
    draw_text(label, tx, ty, size=max(9.0, tr * 0.9), color=COL_TEXT, align='CENTER', shadow=True)


def _overlay_brush_size(context: Context) -> float:
    ups = get_sculpt_unified_paint_settings(context)
    brush = context.tool_settings.sculpt.brush
    if brush is None:
        return 1.0
    if ups is not None and ups.use_unified_size:
        return float(ups.size)
    return float(brush.size)


def _overlay_brush_strength(context: Context) -> float:
    ups = get_sculpt_unified_paint_settings(context)
    brush = context.tool_settings.sculpt.brush
    if brush is None:
        return 1.0
    if ups is not None and ups.use_unified_strength:
        return float(ups.strength)
    return float(brush.strength)


def _draw_gesture_overlay(context: Context, op: 'SculptWheelOperator') -> None:
    if op._gesture_state != 'drag' or op._gesture_axis is None:
        return

    cx, cy = op._gesture_origin
    radius = op.wheel_radius
    is_vert = op._gesture_axis == 'Y'
    invert = op._gesture_invert
    show_size = (is_vert and not invert) or (not is_vert and invert)

    if show_size:
        val = _overlay_brush_size(context)
        draw_ring(cx, cy, max(1.0, val * 0.5), (0.8, 0.9, 1.0, 0.95), thickness=1.8, softness=0.02)
    else:
        val = _overlay_brush_strength(context)
        draw_ring(cx, cy, radius, (0.8, 0.8, 0.8, 0.45), thickness=1.4, softness=0.02)
        draw_ring(cx, cy, radius * min(1.0, max(0.0, val / 2.0)), (1.0, 0.95, 0.35, 0.95), thickness=1.8, softness=0.02)
