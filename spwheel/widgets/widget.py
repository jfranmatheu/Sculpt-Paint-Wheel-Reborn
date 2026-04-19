from typing import TYPE_CHECKING, Callable, Literal, Optional, Tuple

from bpy.types import Context, Event
import gpu
from mathutils import Vector

from ..wheels.wheel import Wheel, WheelPrefs
from ..pg.pg_wheel_theme import WheelTheme


class Widget:
    use_modal = False

    # Parenting ------------
    parent: "Widget"
    children: list["Widget"]

    # State ------------
    enabled = True  # The widget is completely disabled (no interaction and no drawing).
    interactable = True  # Whether the widget can be interacted with.
    hovered = False  # Whether the widget is hovered hovered over.

    # Transform Common -----------
    scale_x = 1.0
    scale_y = 1.0
    offset = Vector((0, 0))

    @property
    def wheel(self) -> "Wheel":
        if self.parent is None:
            raise ValueError("Widget must have a parent to get the wheel")
        if isinstance(self.parent, Wheel):
            return self.parent
        return self.parent.wheel

    def __init__(self):
        self.children = []
        self.parent = None
        self.hovered = False
        self.enabled = True
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.offset = Vector((0, 0))
        self.init()

    def init(self) -> None:
        pass

    def set_parent(self, parent: "Widget" = None) -> None:
        assert isinstance(parent, (Widget, Wheel)), "Parent must be a Widget or a Wheel"
        if parent is self:
            raise ValueError("Widget cannot be its own parent")
        self.parent = parent
        parent.add_child(self)

    def setup_event_subs(self) -> Tuple[Tuple[str, Callable[[Context], None]]] | None:
        return None

    def _activate(self, context: Context, prefs: WheelPrefs) -> None:
        self.enabled = True
        self.activate(context, prefs)
        for child in self.children:
            child._activate(context, prefs)

    def add_child(self, child: "Widget") -> None:
        if child.parent is not None:
            child.parent.remove_child(child)
        child.parent = self
        self.children.append(child)

    def remove_child(self, child: "Widget", free: bool = False) -> None:
        if child.parent != self:
            return
        self.children.remove(child)
        child.parent = None
        if free:
            child.free()

    def _on_left_press(self, context: Context, event: Event) -> Callable[[Context, Event], bool]:
        if not self.interactable:
            return False
        if not self.on_left_press(context, event):
            return False
        if self.use_modal:
            return self.modal
        return True

    def _test_hit(self, context: Context, p: Vector) ->  Optional["Widget"]:
        if not self.enabled:
            return None
        for child in self.children:
            result = child._test_hit(context, p)
            if result is not None:
                return result
        if not self.interactable:
            return None
        if self.test_hit(context, p):
            if self.hovered:
                self.on_hover_enter(context, p)
                self.hovered = True
                context.region.tag_redraw()
            return self
        else:
            if self.hovered:
                self.on_hover_exit(context)
                self.hovered = False
                context.region.tag_redraw()
        return None

    def test_hit(self, context: Context, p: Vector) -> bool:
        raise NotImplementedError("Subclasses must implement test_hit")

    def _draw(self, context: Context, theme: WheelTheme) -> None:
        if not self.enabled:
            return

        with gpu.matrix.push_pop():
            gpu.matrix.translate(self.offset)
            if self.scale_x != 1.0 or self.scale_y != 1.0:
                gpu.matrix.scale((self.scale_x, self.scale_y))

            self.draw(context, theme)
            for child in self.children:
                child._draw(context, theme)

    def free(self) -> None:
        for child in self.children:
            child.free()
        del self

    # -------------------------------------------------------
    # Subclasses must implement the following methods: #
    # -------------------------------------------------------

    def set_transform(self, context: Context) -> None:
        raise NotImplementedError("Subclasses must implement transform")

    def activate(self, context: Context, prefs: WheelPrefs) -> None:
        """ We are goind to use this widget! Let's prepare it! """
        pass

    def on_hover_enter(self, context: Context, p: Vector) -> None:
        """ Called when we just enter the widget's hitbox. """
        pass

    def on_hover_exit(self, context: Context) -> None:
        """ Called when the widget is no longer hovered over. """
        pass

    def on_left_press(self, context: Context, event: Event) -> bool:
        """
        Called when the left mouse button is pressed on the widget.
        Returns True if the widget should consume the event, False otherwise.
        """
        pass

    def modal(self, context: Context, event: Event) -> bool:
        return True

    def draw(self, context: Context, theme: WheelTheme) -> None:
        pass



class WidgetCircle(Widget):
    radius: float
    center: Vector

    @property
    def center(self) -> Vector:
        return self.offset

    def set_transform(self, offset_x: float, offset_y: float, radius: float) -> None:
        self.offset = Vector((offset_x, offset_y))
        if radius > 1.0:
            self.radius = radius
        else:
            wheel = self.wheel
            self.radius = wheel.radius * radius

    def test_hit(self, context: Context, p: Vector) -> bool:
        return (p.x - self.center.x) ** 2 + (p.y - self.center.y) ** 2 <= self.radius ** 2


class WidgetRect(Widget):
    width: float
    height: float
    pos: Vector

    @property
    def pos(self) -> Vector:
        return self.offset

    def set_transform(self, offset_x: float, offset_y: float, width: float, height: float) -> None:
        self.offset = Vector((offset_x, offset_y))
        self.width = width
        self.height = height

    def test_hit(self, context: Context, p: Vector) -> bool:
        return self.pos.x <= p.x <= self.pos.x + self.width and self.pos.y <= p.y <= self.pos.y + self.height


class WidgetRing(Widget):
    radius_inner: float
    radius_outer: float
    thickness: float

    @property
    def center(self) -> Vector:
        return self.offset

    def set_transform(self, offset_x: float, offset_y: float, radius: float, thickness: float) -> None:
        self.offset = Vector((offset_x, offset_y))
        if radius > 1.0:
            self.radius_outer = radius
        else:
            wheel = self.wheel
            self.radius_outer = wheel.radius * radius
        if thickness > 1.0:
            self.thickness = thickness
        else:
            self.thickness = self.radius_outer * thickness
        self.radius_inner = self.radius_outer - self.thickness

    def test_hit(self, context: Context, p: Vector) -> bool:
        if not (p.x - self.center.x) ** 2 + (p.y - self.center.y) ** 2 <= self.radius_outer ** 2:
            return False
        if not (p.x - self.center.x) ** 2 + (p.y - self.center.y) ** 2 >= self.radius_inner ** 2:
            return False
        return True
