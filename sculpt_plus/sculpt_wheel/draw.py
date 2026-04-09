"""GPU draw callback for the sculpt wheel overlay."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..core.gpu.imm_2d import draw_text, draw_circle
from ..core.gpu.state_control import CM_GPU_BLEND
from .gpu_utils import (
    draw_circle_fill,
    draw_ring,
    draw_textured_circle,
)
from .brush_assets import find_brush_for_slot, get_brush_preview_texture

if TYPE_CHECKING:
    from .op_sculpt_wheel import SculptWheelOperator


# ---------------------------------------------------------------------------
# Colours
# ---------------------------------------------------------------------------

COL_BASE = (0.12, 0.12, 0.12, 0.80)
COL_BASE_RING = (0.35, 0.35, 0.35, 0.90)
COL_SLOT_BG = (0.22, 0.22, 0.22, 0.85)
COL_SLOT_HOVER = (0.55, 0.70, 1.0, 0.35)
COL_SLOT_ACTIVE_RING = (0.85, 0.85, 0.85, 0.95)
COL_SLOT_HOVER_RING = (0.55, 0.70, 1.0, 0.80)
COL_TEXT = (0.90, 0.90, 0.90, 1.0)
COL_TOOLSET_DOT = (0.50, 0.50, 0.50, 0.70)
COL_TOOLSET_DOT_ACTIVE = (1.0, 1.0, 1.0, 0.95)


# ---------------------------------------------------------------------------
# Main draw
# ---------------------------------------------------------------------------

def draw_wheel(op: 'SculptWheelOperator') -> None:
    """Entry point called from the modal operator's ``draw_2d``."""
    cx = op.wheel_center_x
    cy = op.wheel_center_y
    radius = op.wheel_radius
    slot_radius = op.slot_radius
    icon_scale = op.icon_scale

    with CM_GPU_BLEND('ALPHA'):
        # 1. Base filled circle
        draw_circle_fill(cx, cy, radius, COL_BASE, softness=0.005)

        # 2. Outer ring
        draw_ring(cx, cy, radius, COL_BASE_RING, thickness=1.5, softness=0.006)

        # 3. Slots
        _draw_slots(op, cx, cy, slot_radius, icon_scale)

        # 4. Toolset indicator dots
        if op.toolset_count > 1:
            _draw_toolset_dots(op, cx, cy, radius)


# ---------------------------------------------------------------------------
# Slot drawing
# ---------------------------------------------------------------------------

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

    for i, (sx, sy) in enumerate(positions):
        if i >= len(slots):
            break
        slot = slots[i]
        is_active = (i == toolset.active_slot_index)
        is_hovered = (i == op.hover_index)

        # Slot background
        draw_circle_fill(sx, sy, slot_radius, COL_SLOT_BG, softness=0.015)

        # Hover highlight
        if is_hovered:
            draw_circle_fill(sx, sy, slot_radius, COL_SLOT_HOVER, softness=0.015)

        # Brush preview icon
        brush = find_brush_for_slot(slot)
        if brush is not None:
            tex = get_brush_preview_texture(brush)
            if tex is not None:
                icon_r = slot_radius * icon_scale
                draw_textured_circle(sx, sy, icon_r, tex, opacity=1.0, softness=0.025)

        # Active ring
        if is_active:
            draw_ring(sx, sy, slot_radius, COL_SLOT_ACTIVE_RING, thickness=2.0, softness=0.012)
        elif is_hovered:
            draw_ring(sx, sy, slot_radius, COL_SLOT_HOVER_RING, thickness=1.5, softness=0.012)

        # Name label
        if op.show_names and slot.display_name:
            draw_text(
                slot.display_name,
                sx, sy - slot_radius - 10,
                size=11.0,
                color=COL_TEXT,
                align='CENTER',
                shadow=True,
            )


# ---------------------------------------------------------------------------
# Toolset dots
# ---------------------------------------------------------------------------

def _draw_toolset_dots(
    op: 'SculptWheelOperator',
    cx: float, cy: float,
    wheel_radius: float,
) -> None:
    """Draw small dots below the wheel to indicate which toolset is active."""
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
