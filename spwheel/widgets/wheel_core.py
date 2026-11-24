from math import sqrt

import blf
from bpy.types import Context

from ..pg.pg_wheel_theme import WheelTheme
from ..pg.pg_wheel_storage import SculptPaintWheelStorage
from ..gpu.draw import draw_text
from ..gpu.ring_prims import sector
from ..gpu.text import ellipsis_middle
from ..utils.ups import get_tool_settings
from .widget import Widget, WheelPrefs


CORE_TEXT_SIZE = 13.0
LINE_SPACING = 1.25      # Line step, in text heights.
TEXT_MARGIN = 0.88       # Fraction of the chord the text may take.


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
    both ways. Display only: no interaction."""
    interactable = False
    text_size = CORE_TEXT_SIZE  # (Sized from the core radius on draw.)

    def __init__(self, ring) -> None:
        super().__init__()
        self.ring = ring
        self.interactable = False
        self.max_lines = 2

    def on_wheel_activate(self, context: Context, wheel_prefs: WheelPrefs, storage: SculptPaintWheelStorage, wg_prefs = None) -> None:
        self.max_lines = max(1, min(3, wheel_prefs.center_text_max_lines))

    def get_text(self, context: Context) -> str:
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
        sector(cx, cy, 0.0, r, fill=tuple(theme.core_color), border=tuple(theme.tarta_outline_color), border_w=1.0)
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
