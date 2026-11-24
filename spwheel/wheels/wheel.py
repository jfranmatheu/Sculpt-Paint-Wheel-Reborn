
from typing import TYPE_CHECKING, Callable, Dict, Optional, Set, Type
from collections import defaultdict

from bpy.types import Context, Event
import gpu
from mathutils import Vector

from ..core.utils.callback_utils import CallbackDict
from ..utils.fun import point_inside_circle
from ..pg.pg_wheel_prefs import WheelPrefs, WheelTheme
from ..gpu.draw import draw_circle_fill, draw_ring
from ..gpu.ring_prims import sector
from ..pg.pg_wheel_storage import SculptPaintWheelStorage, WheelStorage

if TYPE_CHECKING:
    from ..widgets import Widget


_registered_types: Dict[str, Type['Wheel']] = {}


class Wheel:
    instances: dict[str, "Wheel"] = {}
    bl_context_mode: str | Set[str] = 'NONE' # MUST BE SET IN SUBCLASSES!
    default_radius = 210

    @classmethod
    def get(cls, context: Context) -> "Wheel":
        if context.mode not in cls.instances:
            global _registered_types
            if mode_cls := _registered_types.get(context.mode, None):
                cls.instances[context.mode] = mode_cls(context)
            else:
                raise ValueError(f'No wheel registered for mode: {context.mode}')
        return cls.instances[context.mode]

    def __init__(self, context: Context) -> None:
        self.center = Vector((0.0, 0.0))
        self.radius = self.default_radius
        self.scale = 1.0
        self._widgets: list["Widget"] = []
        self.hovered_widget: "Widget" | None = None
        self._pressed_widget: "Widget" | None = None
        self._last_mouse: Vector | None = None  # Region space, from the last update_hover.
        self._event_subscriptions: CallbackDict = CallbackDict()
        self.setup(context)
        for wg in self.get_all_widgets():
            if subs := wg.setup_event_subs():
                for (sub_id, sub_callback) in subs:
                    self._event_subscriptions.add_callback(sub_id, sub_callback)

    def get_all_widgets(self) -> list["Widget"]:
        all_widgets = []
        def visit(widget: "Widget") -> None:
            nonlocal all_widgets
            all_widgets.append(widget)
            if widget.children:
                for child in widget.children:
                    visit(child)
        for wg in self._widgets:
            visit(wg)
        return all_widgets

    def _activate(self, context: Context, center: Optional[Vector] = None) -> None:
        if center:
            self.center = center
        prefs = WheelPrefs.get(context)
        # Fix #1: Cache the scale once per activation so drawing and hit-testing share it.
        self.scale = prefs.scale if prefs.scale > 0.0 else 1.0
        storage = WheelStorage.get_by_mode(context)
        self.activate(context, prefs, storage)
        for widget in self._widgets:
            widget._on_wheel_activate(context, prefs, storage)
        # Activation rebuilds widgets (e.g. the brush slots): the hovered / pressed ones may be gone. Hover again at
        # the mouse (the centre when opening), so a click without moving hits what is really under it.
        self.hovered_widget = None
        self._pressed_widget = None
        p = center if center is not None else self._last_mouse
        if p is not None:
            self.update_hover(context, p)

    def to_region(self, lx: float, ly: float) -> tuple[float, float]:
        s = self.scale
        return (self.center.x + lx * s, self.center.y + ly * s)

    def to_local(self, rx: float, ry: float) -> tuple[float, float]:
        s = self.scale
        return ((rx - self.center.x) / s, (ry - self.center.y) / s)

    def contains_point(self, p: Vector) -> bool:
        return point_inside_circle(p, self.center, self.radius * self.scale)

    def add_widget(self, widget: "Widget") -> None:
        self._widgets.append(widget)

    def add_child(self, widget: "Widget") -> None:
        self.add_widget(widget)

    def update_hover(self, context: Context, p: Vector) -> bool:
        # Widget transforms are defined in wheel-local space, while mouse coords
        # arrive in region space. Convert once and use local coords for hit tests.
        self._last_mouse = p.copy()
        p_local = Vector(self.to_local(p.x, p.y))

        if self.hovered_widget:
            if not self.hovered_widget._test_hit(context, p_local):
                self.hovered_widget = None
        # Match hit-testing priority with draw order: later drawn widgets are "on top".
        for widget in reversed(self._widgets):
            result = widget._test_hit(context, p_local)
            if result is not None:
                self.hovered_widget = result
                return True
        # Check itself.
        if self.contains_point(p):
            return True
        return False

    def on_left_press(self, context: Context, event: Event) -> Callable[[Context, Event], bool] | bool | None:
        if self.hovered_widget:
            if self.hovered_widget.click_on_release:
                ret = self.hovered_widget._on_left_press(context, event)
                if ret:
                    self._pressed_widget = self.hovered_widget
                return ret
            self._pressed_widget = None
            return self.hovered_widget._on_left_press(context, event)
        self._pressed_widget = None
        return None

    def on_left_release(self, context: Context, event: Event) -> bool:
        if self._pressed_widget is None:
            return False
        pressed_widget = self._pressed_widget
        self._pressed_widget = None
        if self.hovered_widget is not pressed_widget:
            return False
        return pressed_widget._on_left_click(context, event)

    def subscribe_to_event(self, event_name: str, callback: Callable[[Context, Event], None]) -> None:
        self._event_subscriptions.add_callback(event_name, callback)

    def propagate_event(self, event_name: str, context: Context, event: Event) -> None:
        self._event_subscriptions.call_callbacks(event_name, context, event)

    def on_scroll_up(self, context: Context, event: Event) -> None:
        self.propagate_event('scroll_up', context, event)

    def on_scroll_down(self, context: Context, event: Event) -> None:
        self.propagate_event('scroll_down', context, event)

    def _draw(self, context: Context, prefs: WheelPrefs) -> None:
        theme = prefs.theme.effective()  # Dark or Light palette (Auto: follows Blender's theme).
        with gpu.matrix.push_pop():
            gpu.matrix.translate(self.center)
            gpu.matrix.scale((self.scale, self.scale))
            self.draw(context, theme)
            for widget in self._widgets:
                widget._draw(context, theme)

    # -------------------------------------------------------
    # Subclasses must implement the following methods: #
    # -------------------------------------------------------

    def setup(self, context: Context) -> None:
        """ Setup widgets for this wheel (called once!) """
        # To implement in subclasses!
        pass

    def activate(self, context: Context, prefs: WheelPrefs, storage: SculptPaintWheelStorage) -> None:
        """ We are goind to use this wheel! Let's prepare it! """
        pass

    def draw(self, context: Context, theme: WheelTheme) -> None:
        r = self.radius
        if theme.shadow_opacity > 0.0:
            # A soft dark disc a bit lower than the wheel (as FlexSpace's ring menu): its blur shows around it.
            sector(0.0, -r * 0.025, 0.0, r, fill=(0.0, 0.0, 0.0, theme.shadow_opacity),
                   soft=max(r * theme.shadow_size, 1.0))
        sector(0.0, 0.0, 0.0, r, fill=tuple(theme.base_color), border=tuple(theme.base_outline_color), border_w=1.0)


# -------------------------------------------------------

def register():
    for wheel_subcls in Wheel.__subclasses__():
        if wheel_subcls.__subclasses__():
            for subcls in wheel_subcls.__subclasses__():
                _registered_types[subcls.bl_context_mode] = subcls
        else:
            _registered_types[wheel_subcls.bl_context_mode] = wheel_subcls

def unregister():
    _registered_types.clear()
