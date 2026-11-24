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
SEG_INNER_RATIO = 0.61   # Inner edge of the segments.
CORE_GAP = 6.0           # Between the segments and the core disc.
SEG_GAP_RATIO = 0.027    # Between neighbouring segments, as a fraction of the pie's outer radius.
SEG_ROUND_RATIO = 0.03   # Corner rounding of the segments, as a fraction of the pie's outer radius.
PRESSED_BLEND = 0.55     # How far a pressed segment's fill goes towards the pressed color.
HOVER_LIGHTEN = 0.10     # How much lighter a hovered segment is.
STRIP_WIDTH = 3.0        # Color strip (tint target): width, and its inset from the segment's edges.
STRIP_INSET = 4.0


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


def _mix(a, b, k: float) -> tuple:
    """sRGB mix of the rgb of ``a`` towards ``b``; alpha of ``a`` kept."""
    return (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k, a[2] + (b[2] - a[2]) * k, a[3])


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
        self._pressed_bid: int = -1  # Button pressed (it runs on the release, when still over it).

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
        pressed_col = tuple(theme.tarta_pressed_color)
        n = self.layout_n
        target = theme.tarta_tint_target
        tint_opacity = theme.tarta_tint_opacity
        tints = [theme.get_tarta_tint(self._tarta_buttons[bid]) if bid >= 0 else None
                 for bid in self.custom_layout_map[:n]]
        seg_gap = self.seg_outer * SEG_GAP_RATIO
        seg_round = self.seg_outer * SEG_ROUND_RATIO

        # Segments.
        for k in range(n):
            a0, a1 = segment_angles(k, n)
            bid = self.custom_layout_map[k]
            if bid < 0:
                fill = (seg_fill[0], seg_fill[1], seg_fill[2], seg_fill[3] * 0.45)
                sector(cx, cy, self.seg_inner, self.seg_outer, a0, a1, fill=fill, gap=seg_gap, round_=seg_round)
                continue
            btn = self._tarta_buttons[bid]
            # Fill = state (pressed toggles / operators), outline = hover.
            pressed = btn.get_state(context) is True
            fill = theme.get_tarta_fill(btn)
            if pressed:
                fill = _mix(fill, pressed_col, PRESSED_BLEND)
            if k == self.hover_layout_slot:
                # Hover lightens on a dark palette, darkens on a light one.
                fill = _mix(fill, (0.0, 0.0, 0.0, 1.0) if getattr(theme, 'is_light', False) else (1.0, 1.0, 1.0, 1.0),
                            HOVER_LIGHTEN)
            if pressed:
                seg_border = (pressed_col[0], pressed_col[1], pressed_col[2], 0.9)
            elif (tint := tints[k]) is not None and target == "OUTLINE":
                seg_border = (tint[0], tint[1], tint[2], tint_opacity)
            else:
                seg_border = border
            sector(cx, cy, self.seg_inner, self.seg_outer, a0, a1,
                   fill=(fill[0], fill[1], fill[2], 1.0),
                   border=seg_border, border_w=1.0,
                   gap=seg_gap, round_=seg_round)
            if target == "COLOR_STRIP" and (tint := tints[k]) is not None:
                r0 = self.seg_inner + STRIP_INSET
                sector(cx, cy, r0, r0 + STRIP_WIDTH, a0, a1, fill=(tint[0], tint[1], tint[2], tint_opacity),
                       gap=seg_gap + STRIP_INSET * 2.0, round_=STRIP_WIDTH * 0.5)

        # Icons (or the name when the button has no image), centred in their segment.
        if n:
            r_lo = self.seg_inner
            if target == "COLOR_STRIP" and any(t is not None for t in tints):
                # The strip takes the segment's inner edge: icons go in the band above it (moved out, and sized
                # to that band, so they don't sit on the strip). Same for every button, strip or not.
                r_lo += STRIP_INSET + STRIP_WIDTH
            rm = (r_lo + self.seg_outer) * 0.5
            # (Half-size: the icon is tarta_icon_size of the band's thickness, and fits its angular width.)
            half = min((self.seg_outer - r_lo) * theme.tarta_icon_size * 0.5,
                       rm * math.sin(min(PI / n, PI * 0.5)) * 0.5)
            col_text = tuple(theme.text_color)
            icon_base = tuple(getattr(theme, 'icon_color', (1.0, 1.0, 1.0, 1.0)))
            for k in range(n):
                bid = self.custom_layout_map[k]
                if bid < 0:
                    continue
                btn = self._tarta_buttons[bid]
                a0, a1 = segment_angles(k, n)
                am = (a0 + a1) * 0.5 if n > 1 else PI * 0.5  # A single button fills the ring: icon on top.
                sx, sy = cx + rm * math.cos(am), cy + rm * math.sin(am)
                tex = get_custom_button_texture(btn.icon_filepath)
                if tex is not None:
                    icon_tint = icon_base
                    if target == "ICON" and (tint := tints[k]) is not None:
                        icon_tint = _mix(icon_base, tint, tint_opacity)
                    draw_textured_quad(sx, sy, half, tex, tint=icon_tint)
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
        armed = self.hover_custom_bid != -1 and self.hover_layout_slot != -1 and self.layout_n > 0
        self._pressed_bid = self.hover_custom_bid if armed else -1
        return armed

    def on_left_click(self, context: Context, event) -> bool:
        pressed_bid, self._pressed_bid = self._pressed_bid, -1
        if self.hover_custom_bid == -1 or self.hover_layout_slot == -1 or self.layout_n <= 0:
            return False
        if self.hover_custom_bid != pressed_bid:
            return False  # (Released over another button than the pressed one: like leaving a button, no click.)
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
