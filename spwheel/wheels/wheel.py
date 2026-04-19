
from typing import TYPE_CHECKING, Callable, Dict, Set, Type
from collections import defaultdict

from bpy.types import Context, Event
import gpu
from mathutils import Vector

from ..core.utils.callback_utils import CallbackDict
from ..utils.fun import point_inside_circle
from ..pg.pg_wheel_prefs import WheelPrefs

if TYPE_CHECKING:
    from ..widgets import Widget


_registered_types: Dict[str, Type['Wheel']] = {}


class Wheel:
    instances: dict[str, "Wheel"] = {}
    bl_context_mode: str | Set[str] = 'NONE' # MUST BE SET IN SUBCLASSES!

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
        self.radius = 200
        self._widgets: list["Widget"] = []
        self.hovered_widget: "Widget" | None = None
        self._event_subscriptions: CallbackDict = CallbackDict()
        self.setup(context)
        for wg in self.get_all_widgets():
            if subs := wg.setup_event_subs():
                for (sub_id, sub_callback) in subs:
                    self._event_subscriptions.add_callback(sub_id, sub_callback)

    def get_all_widgets(self) -> list["Widget"]:
        all_widgets = []
        def get_children(widget: "Widget") -> list["Widget"]:
            nonlocal all_widgets
            if widget.children:
                for child in widget.children:
                    all_widgets.append(child)
                    get_children(child)
        for wg in self._widgets:
            get_children(wg)
        return all_widgets

    def _activate(self, context: Context, prefs: WheelPrefs, center: Vector) -> None:
        self.center = center
        self.activate(context, prefs)
        for widget in self._widgets:
            widget._activate(context, prefs)

    def to_region(self, lx: float, ly: float) -> tuple[float, float]:
        return (self.center.x + lx, self.center.y + ly)

    def to_local(self, rx: float, ry: float) -> tuple[float, float]:
        return (rx - self.center.x, ry - self.center.y)

    def contains_point(self, p: Vector) -> bool:
        return point_inside_circle(p, self.center, self.radius)

    def add_widget(self, widget: "Widget") -> None:
        self._widgets.append(widget)

    def add_child(self, widget: "Widget") -> None:
        self.add_widget(widget)

    def update_hover(self, context: Context, p: Vector) -> bool:
        if self.hovered_widget:
            if not self.hovered_widget._test_hit(context, p):
                self.hovered_widget = None
        for widget in self._widgets:
            result = widget._test_hit(context, p)
            if result is not None:
                self.hovered_widget = result
                return True
        # Check itself.
        if self.contains_point(p):
            return True
        return False

    def on_left_press(self, context: Context, event: Event) -> Callable[[Context, Event], bool] | None:
        if self.hovered_widget:
            return self.hovered_widget._on_left_press(context, event)
        return None

    def subscribe_to_event(self, event_name: str, callback: Callable[[Context], None]) -> None:
        self._event_subscriptions.add_callback(event_name, callback)

    def propagate_event(self, context: Context, event_name: str) -> None:
        self._event_subscriptions.call_callbacks(event_name, context)

    def on_scroll_up(self, context: Context) -> None:
        self.propagate_event(context, 'scroll_up')

    def on_scroll_down(self, context: Context) -> None:
        self.propagate_event(context, 'scroll_down')

    def _draw(self, context: Context, prefs: WheelPrefs) -> None:
        theme = prefs.theme
        with gpu.matrix.push_pop():
            gpu.matrix.translate(self.center)
            gpu.matrix.scale((prefs.scale, prefs.scale))
            for widget in self._widgets:
                widget._draw(context, theme)
            self.draw(context, theme)

    # -------------------------------------------------------
    # Subclasses must implement the following methods: #
    # -------------------------------------------------------

    def setup(self, context: Context) -> None:
        """ Setup widgets for this wheel (called once!) """
        # To implement in subclasses!
        pass

    def activate(self, context: Context, prefs: WheelPrefs) -> None:
        """ We are goind to use this wheel! Let's prepare it! """
        pass

    def draw(self, context: Context, prefs: WheelPrefs) -> None:
        # To implement in subclasses!
        pass


# -------------------------------------------------------

def register():
    for wheel_subcls in Wheel.__subclasses__():
        _registered_types[wheel_subcls.bl_context_mode] = wheel_subcls

def unregister():
    _registered_types.clear()
