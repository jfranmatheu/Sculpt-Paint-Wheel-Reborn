"""Weight picker ring + center gesture pad (size/strength) for weight wheel."""

from __future__ import annotations

from math import atan2, hypot
from typing import TYPE_CHECKING

import bpy
from mathutils import Vector

from ..gpu.weight import (
    angle_deg_to_weight_value,
    draw_weight_handle,
    draw_weight_hue_ring,
    draw_weight_markers,
    marker_points,
)
from ..gpu.draw import draw_text
from ..gpu.utils import draw_circle_fill, draw_ring
from ..utils.ups import (
    get_ups_size,
    get_ups_strength,
    get_ups_weight,
    set_ups_size,
    set_ups_strength,
    set_ups_weight,
)
from .widget import WidgetRing

if TYPE_CHECKING:
    from bpy.types import Context, Event
    from ..pg.pg_wheel_theme import WheelTheme


class WeightPickerWidget(WidgetRing):
    interactable = True
    use_modal = True

    def init(self) -> None:
        self.marker_lines: list[tuple[float, float]] = []
        self.marker_buttons: list[tuple[float, float]] = []
        self.marker_button_radius = 6.0
        self.hover_marker_index = -1
        self.center_pad_radius = 34.0
        self.color_ring_radius = 0.0
        self.color_ring_inner_radius = 0.0
        self.color_ring_outer_radius = 0.0
        self._drag_mode = None  # "weight" | "pad" | "marker"
        self._pad_axis = None  # "h" | "v"
        self._drag_start_mouse = Vector((0.0, 0.0))
        self._drag_prev_mouse = Vector((0.0, 0.0))
        self._center_text: str | None = None  # Shown in the wheel's centre while dragging.

    @property
    def center_text(self) -> str | None:
        """While dragging, what the drag is changing (it overrides any hover text in the wheel's centre)."""
        return self._center_text if self._drag_mode is not None else None

    @property
    def hover_label(self) -> str | None:
        """The hovered weight marker."""
        if self.hover_marker_index < 0 or not self.marker_buttons:
            return None
        return f"Weight {self.hover_marker_index / max(1, len(self.marker_buttons) - 1):.1f}"

    @staticmethod
    def _clamp(v: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, v))

    def _weight_value(self, context: "Context") -> float:
        return float(get_ups_weight(context) or 0.0)

    def _set_weight_value(self, context: "Context", value: float) -> None:
        """Set the brush weight (live while dragging); the masked selection gets it when the drag ends."""
        self._center_text = f"{self._clamp(value, 0.0, 1.0):.2f}"
        value = self._clamp(value, 0.0, 1.0)
        set_ups_weight(context, value)
        self._weight_changed = True

    def _apply_weight_to_selection(self, context: "Context") -> None:
        """Set the weight of the masked selection, once per drag (weight_set pushes an undo step each time)."""
        if not getattr(self, "_weight_changed", False):
            return
        self._weight_changed = False
        if getattr(self.wg_prefs, "set_weight_of_selection_directly", True) and context.mode == "PAINT_WEIGHT":
            ob = context.active_object
            if ob and getattr(ob, "data", None):
                data = ob.data
                if getattr(data, "use_paint_mask", False) or getattr(data, "use_paint_mask_vertex", False):
                    bpy.ops.paint.weight_set()

    def _finish_drag(self, context: "Context") -> None:
        if self._drag_mode in {"weight", "marker"}:
            self._apply_weight_to_selection(context)
        self._drag_mode = None
        self._pad_axis = None

    def _weight_from_pointer(self, p_local: Vector) -> float:
        dx = p_local.x - self.center.x
        dy = p_local.y - self.center.y
        a = atan2(dy, dx) * (180.0 / 3.141592653589793)
        return angle_deg_to_weight_value(a)

    def on_wheel_activate(self, context: "Context", wheel_prefs, storage, wg_prefs=None) -> None:
        self.wg_prefs = wg_prefs or wheel_prefs.weight
        outer = max(self.radius_inner, self.radius_outer)
        # Match legacy proportions: the weight color ring is a single-radius ring,
        # not the full widget annulus thickness.
        self.color_ring_radius = outer * 0.89
        self.color_ring_inner_radius = self.color_ring_radius * 0.82
        self.color_ring_outer_radius = self.color_ring_radius
        ring_thick = max(self.color_ring_outer_radius - self.color_ring_inner_radius, 1.0)
        marker_count = int(getattr(self.wg_prefs, "marker_count", 10))
        self.marker_lines, self.marker_buttons = marker_points(
            self.center.x,
            self.center.y,
            self.color_ring_radius * 1.05,
            self.color_ring_radius * 1.14,
            marker_count,
        )
        self.marker_button_radius = max(9.0, self.color_ring_radius * 0.11)
        # Rebuild marker lines so they connect arc outer edge -> marker circle border.
        rebuilt_lines: list[tuple[float, float]] = []
        cx, cy = self.center.x, self.center.y
        arc_edge_r = self.color_ring_outer_radius
        for bx, by in self.marker_buttons:
            vx = bx - cx
            vy = by - cy
            d = hypot(vx, vy)
            if d <= 1e-8:
                continue
            inv = 1.0 / d
            ux = vx * inv
            uy = vy * inv
            sx = cx + ux * arc_edge_r
            sy = cy + uy * arc_edge_r
            ex = bx - ux * self.marker_button_radius
            ey = by - uy * self.marker_button_radius
            rebuilt_lines.append((sx, sy))
            rebuilt_lines.append((ex, ey))
        self.marker_lines = rebuilt_lines
        self.center_pad_radius = max(24.0, self.color_ring_radius * 0.26)
        self.hover_marker_index = -1

    def test_hit(self, context: "Context", p: Vector) -> bool:
        self.hover_marker_index = -1
        if getattr(self.wg_prefs, "show_markers", True) and getattr(self.wg_prefs, "use_interactable_markers", True):
            for i, b in enumerate(self.marker_buttons):
                if hypot(p.x - b[0], p.y - b[1]) <= self.marker_button_radius:
                    self.hover_marker_index = i
                    return True

        if hypot(p.x - self.center.x, p.y - self.center.y) <= self.center_pad_radius:
            return True
        r = hypot(p.x - self.center.x, p.y - self.center.y)
        return self.color_ring_inner_radius * 0.96 <= r <= self.color_ring_outer_radius * 1.06

    def on_left_press(self, context: "Context", event: "Event") -> bool:
        mx, my = self.wheel.to_local(event.mouse_region_x, event.mouse_region_y)
        p = Vector((mx, my))
        self._drag_start_mouse = p.copy()
        self._drag_prev_mouse = p.copy()
        self._pad_axis = None

        if self.hover_marker_index != -1:
            marker_count = max(1, len(self.marker_buttons) - 1)
            self._set_weight_value(context, self.hover_marker_index / marker_count)
            context.region.tag_redraw()
            self._drag_mode = "marker"
            return True

        if hypot(p.x - self.center.x, p.y - self.center.y) <= self.center_pad_radius:
            self._drag_mode = "pad"
            self._center_text = None
            return True

        self._drag_mode = "weight"
        self._set_weight_value(context, self._weight_from_pointer(p))
        context.region.tag_redraw()
        return True

    def end_drag(self, context: "Context") -> None:
        self._finish_drag(context)

    def modal(self, context: "Context", event: "Event") -> bool:
        if self._drag_mode is None:
            return False
        if event.type in {"MOUSEMOVE", "INBETWEEN_MOUSEMOVE"}:
            mx, my = self.wheel.to_local(event.mouse_region_x, event.mouse_region_y)
            p = Vector((mx, my))
            if self._drag_mode == "weight":
                self._set_weight_value(context, self._weight_from_pointer(p))
            elif self._drag_mode == "pad":
                diff = p - self._drag_prev_mouse
                if self._pad_axis is None:
                    d0 = p - self._drag_start_mouse
                    if abs(d0.x) > 6.0 or abs(d0.y) > 6.0:
                        self._pad_axis = "v" if abs(d0.y) >= abs(d0.x) else "h"
                if self._pad_axis == "v":
                    size = float(get_ups_size(context) or 35.0)
                    speed = 1.0 * (0.25 if event.shift else 1.0) * (2.0 if event.ctrl else 1.0)
                    new_size = int(self._clamp(size + diff.y * speed, 1.0, 500.0))
                    set_ups_size(context, new_size)
                    self._center_text = f"Radius {new_size}"
                elif self._pad_axis == "h":
                    strength = float(get_ups_strength(context) or 0.5)
                    speed = 0.01 * (0.25 if event.shift else 1.0) * (2.0 if event.ctrl else 1.0)
                    new_strength = self._clamp(strength + diff.x * speed, 0.01, 2.0)
                    set_ups_strength(context, new_strength)
                    self._center_text = f"Strength {new_strength:.2f}"
            self._drag_prev_mouse = p
            context.region.tag_redraw()
            return True
        if event.type == "LEFTMOUSE" and event.value == "RELEASE":
            self._finish_drag(context)
            return False
        if event.type in {"RIGHTMOUSE", "ESC"} and event.value == "PRESS":
            self._finish_drag(context)
            return False
        return True

    def draw(self, context: "Context", theme: "WheelTheme") -> None:
        cx, cy = self.center
        # inner = min(self.radius_inner, self.radius_outer)
        # outer = max(self.radius_inner, self.radius_outer)

        # draw_ring(cx, cy, inner, theme.base_outline_color, thickness=1.15)
        # draw_ring(cx, cy, outer, theme.base_outline_color, thickness=1.15)

        if getattr(self.wg_prefs, "show_markers", True):
            draw_weight_markers(
                self.marker_lines,
                self.marker_buttons,
                button_radius=self.marker_button_radius,
                hover_index=self.hover_marker_index,
                interactive=getattr(self.wg_prefs, "use_interactable_markers", True),
            )
            marker_count = max(1, len(self.marker_buttons) - 1)
            label_size = max(10.0, self.wheel.radius * 0.05)
            for i, p in enumerate(self.marker_buttons):
                lbl = f"{(i / marker_count):.1f}"
                draw_text(lbl, p[0], p[1], size=label_size, color=(.95, .95, .95, 0.88), align="CENTER", valign='MIDDLE', shadow=False, font_id=1)

        draw_weight_hue_ring(cx, cy, self.color_ring_outer_radius, self.color_ring_inner_radius)
        draw_weight_handle(
            cx,
            cy,
            self.color_ring_radius * 0.80,
            self.color_ring_radius * 1.03,
            self._weight_value(context),
        )

        # (The centre pad, the size / strength drag area, is not drawn: the wheel's centre shows the hovered item,
        # and the value being dragged.)
