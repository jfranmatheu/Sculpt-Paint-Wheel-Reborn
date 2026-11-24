import math
from math import pi as PI, tau as TAU

from mathutils import Vector
from bpy.types import Context

from ..pg.pg_wheel_theme import WheelTheme
from ..pg.pg_wheel_storage import WheelTartaSetStorage
from ..gpu.button_texture import get_custom_button_texture
from ..gpu.draw import draw_textured_quad, draw_text
from ..gpu.ring_prims import sector
from .widget import WidgetRing, WheelPrefs
from ..pg.pg_tarta_button import WheelTartaButton
from ..pg.pg_tarta_set import MAX_TARTA_BUTTONS


# Proportions (of the ring's outer radius) and spacing (wheel-local units).
SEG_INNER_RATIO = 0.58   # Inner edge of the segments.
CORE_GAP = 4.0           # Between the segments and the core disc.
SEG_GAP = 3.0            # Between neighbouring segments.
SEG_ROUND = 3.0          # Corner rounding of the segments.


def segment_angles(k: int, n: int) -> tuple[float, float]:
    """(a0, a1) of segment ``k`` of ``n``: radians CCW from +x; segment 0 starts at the left (180 deg), then
    clockwise."""
    step = TAU / n
    a1 = PI - k * step
    return a1 - step, a1


def segment_from_point(dx: float, dy: float, n: int) -> int:
    """Index of the segment (see ``segment_angles``) under the local offset ``(dx, dy)`` from the centre."""
    if n <= 0:
        return -1
    step = TAU / n
    return int(math.floor(((PI - math.atan2(dy, dx)) % TAU) / step)) % n


def _shade(c, k: float) -> tuple:
    """``c`` darkened (k > 0) or lightened (k < 0) by |k|, alpha kept."""
    t = 0.0 if k > 0 else 1.0
    k = abs(k)
    return (c[0] + (t - c[0]) * k, c[1] + (t - c[1]) * k, c[2] + (t - c[2]) * k, c[3])


class TartaRing(WidgetRing):
    """Pie menu: a ring of rounded segments, one per custom button. The space inside (``core_radius``) is left
    for the wheel's centre widget."""
    click_on_release = True
    _tarta_buttons: list[WheelTartaButton] = []

    def init(self) -> None:
        self.layout_n = 0
        self.custom_layout_map: list[int] = []
        self.seg_inner = 0.0
        self.seg_outer = 0.0
        self.core_radius = 0.0
        self.hover_layout_slot: int = -1
        self.hover_custom_bid: int = -1

    def on_wheel_activate(self, context: Context, wheel_prefs: WheelPrefs, storage: WheelTartaSetStorage, wg_prefs = None) -> None:
        self._active_tarta_set = storage.active_tarta_set
        self._tarta_buttons = self._active_tarta_set.buttons if self._active_tarta_set else []
        self.hover_layout_slot = -1
        self.hover_custom_bid = -1
        self.layout()

    def layout(self) -> None:
        n = len(self._tarta_buttons)
        self.seg_outer = self.radius_outer
        self.seg_inner = self.radius_outer * SEG_INNER_RATIO
        self.core_radius = max(self.seg_inner - CORE_GAP, 0.0)
        if n == 0:
            self.layout_n = 0
            self.custom_layout_map = []
            # No buttons: the centre takes the whole ring.
            self.core_radius = self.radius_outer
            return
        # One segment per button, no empty padding slots.
        self.layout_n = min(n, MAX_TARTA_BUTTONS)
        self.custom_layout_map = list(range(self.layout_n))

    # ----- DRAWING --------------------------------

    def draw(self, context: Context, theme: WheelTheme) -> None:
        cx, cy = self.center
        seg_fill = tuple(theme.tarta_color)  # (Empty slots; buttons: theme.get_tarta_fill.)
        border = tuple(theme.tarta_outline_color)
        accent = tuple(theme.tarta_accent_color)
        n = self.layout_n

        # Segments.
        for k in range(n):
            a0, a1 = segment_angles(k, n)
            bid = self.custom_layout_map[k]
            if bid < 0:
                fill = (seg_fill[0], seg_fill[1], seg_fill[2], seg_fill[3] * 0.45)
                sector(cx, cy, self.seg_inner, self.seg_outer, a0, a1, fill=fill, gap=SEG_GAP, round_=SEG_ROUND)
                continue
            btn = self._tarta_buttons[bid]
            # Fill = state (pressed toggles / operators), outline = hover.
            pressed = btn.get_state(context) is True
            if k == self.hover_layout_slot:
                seg_border, seg_border_w = (_shade(accent, -0.6) if pressed else _shade(accent, -0.3)), 2.0
            else:
                seg_border, seg_border_w = border, 1.0
            sector(cx, cy, self.seg_inner, self.seg_outer, a0, a1,
                   fill=accent if pressed else theme.get_tarta_fill(btn),
                   border=seg_border, border_w=seg_border_w,
                   gap=SEG_GAP, round_=SEG_ROUND)

        # Icons (or the name when the button has no image), centred in their segment.
        if n:
            rm = (self.seg_inner + self.seg_outer) * 0.5
            half = min((self.seg_outer - self.seg_inner) * 0.3, rm * math.sin(min(PI / n, PI * 0.5)) * 0.55)
            col_text = tuple(theme.text_color)
            for k in range(n):
                bid = self.custom_layout_map[k]
                if bid < 0:
                    continue
                btn = self._tarta_buttons[bid]
                a0, a1 = segment_angles(k, n)
                am = (a0 + a1) * 0.5 if n > 1 else PI * 0.5  # A single button fills the ring: icon on top.
                sx, sy = cx + rm * math.cos(am), cy + rm * math.sin(am)
                hovered = k == self.hover_layout_slot
                tex = get_custom_button_texture(btn.image_path)
                if tex is not None:
                    draw_textured_quad(sx, sy, half * (1.08 if hovered else 1.0), tex, opacity=1.0 if hovered else 0.9)
                elif btn.name:
                    draw_text(btn.name[:10], sx, sy, size=9.0, color=col_text, align='CENTER', valign='MIDDLE', shadow=True)

    # ----- INTERACTION --------------------------------

    @property
    def hover_label(self) -> str | None:
        """Name of the hovered button (shown by the wheel's centre widget), None when nothing is hovered."""
        if self.hover_custom_bid < 0:
            return None
        return self._tarta_buttons[self.hover_custom_bid].name

    def on_left_press(self, context: Context, event) -> bool:
        # Arm click on press; actual action is executed on release.
        return self.hover_custom_bid != -1 and self.hover_layout_slot != -1 and self.layout_n > 0

    def on_left_click(self, context: Context, event) -> bool:
        if self.hover_custom_bid == -1 or self.hover_layout_slot == -1 or self.layout_n <= 0:
            return False
        hovered_button = self._tarta_buttons[self.hover_custom_bid]
        hovered_button(context)
        return True

    def sync_hover(self, context: Context, mx: float, my: float) -> None:
        prev = self.hover_layout_slot
        self.hover_layout_slot = -1
        self.hover_custom_bid = -1
        if self.layout_n > 0:
            cx, cy = self.center
            dx, dy = mx - cx, my - cy
            if self.seg_inner - 1.0 <= math.hypot(dx, dy) <= self.seg_outer + 2.0:
                k = segment_from_point(dx, dy, self.layout_n)
                bid = self.custom_layout_map[k]
                if bid >= 0:
                    self.hover_custom_bid = bid
                    self.hover_layout_slot = k
        if prev != self.hover_layout_slot:
            context.region.tag_redraw()

    def test_hit(self, context: Context, p: Vector) -> bool:
        self.sync_hover(context, p.x, p.y)
        return self.hover_custom_bid >= 0
