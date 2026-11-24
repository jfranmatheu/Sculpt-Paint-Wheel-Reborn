from math import hypot, sqrt

import blf
from bpy.types import Context, Event
from mathutils import Vector

from ..pg.pg_wheel_theme import WheelTheme
from ..pg.pg_wheel_storage import SculptPaintWheelStorage
from ..gpu.draw import draw_text
from ..gpu.ring_prims import sector
from ..gpu.text import ellipsis_middle
from ..utils.ups import get_tool_settings, get_ups_size, get_ups_strength, set_ups_size, set_ups_strength
from .widget import Widget, WheelPrefs


CORE_TEXT_SIZE = 13.0
LINE_SPACING = 1.25      # Line step, in text heights.
TEXT_MARGIN = 0.88       # Fraction of the chord the text may take.
HOVER_LIGHTEN = 0.06     # How much lighter the centre is while hovered / dragged (when it can be dragged).

DRAG_AXIS_LOCK = 6.0     # Pixels moved before a drag picks its axis (vertical: radius, horizontal: strength).
RADIUS_PER_PIXEL = 1.0
STRENGTH_PER_PIXEL = 0.005


def _wrap_words(text: str, max_w: float) -> list[str]:
    """Greedy word wrap at the current blf size (a word wider than ``max_w`` keeps its own line)."""
    words = text.split()
    if not words:
        return []
    lines = [words[0]]
    for w in words[1:]:
        trial = f"{lines[-1]} {w}"
        if blf.dimensions(0, trial)[0] <= max_w:
            lines[-1] = trial
        else:
            lines.append(w)
    return lines


class WheelCore(Widget):
    """Centre of the wheel: a disc inside ``ring`` (its ``core_radius``) naming the hovered item (any widget with a
    ``hover_label``: a custom button, a brush), else the active brush. Up to ``center_text_max_lines`` lines, centred
    both ways.

    With ``use_center_drag``, dragging in it changes the brush: up / down its radius, left / right its strength
    (Shift: finer, Ctrl: faster; Esc / right click: back to the values before the drag)."""
    use_modal = True
    text_size = CORE_TEXT_SIZE  # (Sized from the core radius on draw.)

    def __init__(self, ring) -> None:
        super().__init__()
        self.ring = ring
        self.interactable = False
        self.max_lines = 2
        self._drag_axis: str | None = None  # None: not dragging; "" (no axis yet) | "v" (radius) | "h" (strength).
        self._drag_start = Vector((0.0, 0.0))
        self._drag_prev = Vector((0.0, 0.0))
        self._start_size = 0.0
        self._start_strength = 0.0
        self._size = 0.0      # Unrounded radius: small steps add up instead of being cut off on every event.
        self._strength = 0.0
        self._center_text: str | None = None

    def on_wheel_activate(self, context: Context, wheel_prefs: WheelPrefs, storage: SculptPaintWheelStorage, wg_prefs = None) -> None:
        self.max_lines = max(1, min(3, wheel_prefs.center_text_max_lines))
        self.interactable = bool(getattr(wheel_prefs, "use_center_drag", True))
        self._drag_axis = None

    # ----- INTERACTION --------------------------------

    @property
    def center_text(self) -> str | None:
        """While dragging, what the drag is changing."""
        return self._center_text if self._drag_axis else None

    def test_hit(self, context: Context, p: Vector) -> bool:
        r = self.ring.core_radius
        if r <= 2.0 or not self.ring.enabled:
            return False
        cx, cy = self.ring.center
        return hypot(p.x - cx, p.y - cy) <= r

    def on_left_press(self, context: Context, event: Event) -> bool:
        try:
            size = get_ups_size(context)
            strength = get_ups_strength(context)
        except AttributeError:  # (No active brush.)
            return False
        if size is None or strength is None:
            return False
        self._start_size = self._size = float(size)
        self._start_strength = self._strength = float(strength)
        # Region pixels: the radius is in screen pixels, whatever the wheel's scale.
        self._drag_start = Vector((event.mouse_region_x, event.mouse_region_y))
        self._drag_prev = self._drag_start.copy()
        self._drag_axis = ""
        self._center_text = None
        return True

    def end_drag(self, context: Context) -> None:
        self._drag_axis = None

    def modal(self, context: Context, event: Event) -> bool:
        if self._drag_axis is None:
            return False
        if event.type in {"MOUSEMOVE", "INBETWEEN_MOUSEMOVE"}:
            p = Vector((event.mouse_region_x, event.mouse_region_y))
            diff = p - self._drag_prev
            self._drag_prev = p
            if not self._drag_axis:
                d0 = p - self._drag_start
                if abs(d0.x) <= DRAG_AXIS_LOCK and abs(d0.y) <= DRAG_AXIS_LOCK:
                    return True
                self._drag_axis = "v" if abs(d0.y) >= abs(d0.x) else "h"
                diff = d0  # (The movement before the axis was picked counts too.)
            speed = (0.25 if event.shift else 1.0) * (2.0 if event.ctrl else 1.0)
            if self._drag_axis == "v":
                self._size = max(1.0, min(5000.0, self._size + diff.y * RADIUS_PER_PIXEL * speed))
                size = int(round(self._size))
                set_ups_size(context, size)
                self._center_text = f"Radius {size} px"
            else:
                hi = max(1.0, self._start_strength)  # (Brushes already above 1 can be dragged from there.)
                self._strength = max(0.0, min(hi, self._strength + diff.x * STRENGTH_PER_PIXEL * speed))
                set_ups_strength(context, self._strength)
                self._center_text = f"Strength {self._strength:.3f}"
            context.region.tag_redraw()
            return True
        if event.type == "LEFTMOUSE" and event.value == "RELEASE":
            self.end_drag(context)
            context.region.tag_redraw()
            return False
        if event.type in {"RIGHTMOUSE", "ESC"} and event.value == "PRESS":
            if self._drag_axis == "v":
                set_ups_size(context, int(round(self._start_size)))
            elif self._drag_axis == "h":
                set_ups_strength(context, self._start_strength)
            self.end_drag(context)
            context.region.tag_redraw()
            return False
        return True

    # ----- DRAWING --------------------------------

    def get_text(self, context: Context) -> str:
        for widget in self.wheel._widgets:
            if text := getattr(widget, 'center_text', None):
                return text
        label = getattr(self.wheel.hovered_widget, 'hover_label', None)
        if label:
            return label
        ts = get_tool_settings(context)
        if ts is not None and ts.brush is not None:
            return ts.brush.name
        return ''

    def layout_lines(self, text: str, radius: float, line_h: float) -> list[str]:
        """The fewest lines (up to ``max_lines``) that fit ``text`` in the disc; each line as wide as the chord at
        the block's top / bottom edge allows. Text that still doesn't fit: the last line shortened with an ellipsis."""
        blf.size(0, int(round(self.text_size)))
        lines: list[str] = []
        max_w = 0.0
        for n in range(1, self.max_lines + 1):
            half_h = n * line_h * LINE_SPACING * 0.5
            if half_h >= radius:
                break
            max_w = 2.0 * sqrt(radius * radius - half_h * half_h) * TEXT_MARGIN
            lines = _wrap_words(text, max_w)
            if len(lines) <= n and all(blf.dimensions(0, ln)[0] <= max_w for ln in lines):
                return lines
        if not lines:  # (Not even one line fits vertically: one line at the disc's width.)
            return [ellipsis_middle(text, radius * 2.0 * TEXT_MARGIN, size=self.text_size)]
        n = min(len(lines), self.max_lines)
        out = lines[:n]
        if len(lines) > n:
            out[-1] = " ".join([out[-1]] + lines[n:])
        return [ellipsis_middle(ln, max_w, size=self.text_size) for ln in out]

    def draw(self, context: Context, theme: WheelTheme) -> None:
        r = self.ring.core_radius
        if r <= 2.0 or not self.ring.enabled:
            return
        cx, cy = self.ring.center
        fill = tuple(theme.core_color)
        if self.interactable and (self.hovered or self._drag_axis is not None):
            fill = tuple(c + (1.0 - c) * HOVER_LIGHTEN for c in fill[:3]) + (fill[3],)
        sector(cx, cy, 0.0, r, fill=fill, border=tuple(theme.tarta_outline_color), border_w=1.0)
        self.text_size = min(max(r * 0.2, 9.0), 28.0)

        text = self.get_text(context).strip()
        if not text:
            return
        blf.size(0, int(round(self.text_size)))
        line_h = blf.dimensions(0, "Mg")[1]
        lines = self.layout_lines(text, r, line_h)
        step = line_h * LINE_SPACING
        y = cy + (len(lines) - 1) * step * 0.5
        col = tuple(theme.text_color)
        for ln in lines:
            draw_text(ln, cx, y, size=self.text_size, color=col, align='CENTER', valign='MIDDLE')
            y -= step
