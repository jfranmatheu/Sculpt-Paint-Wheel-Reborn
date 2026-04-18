from typing import Literal
from bpy.types import Context, Event
import gpu
from mathutils import Vector

from ..core.utils import OpReturn


class Transform:
    def __init__(self, widget: "Widget", parent: "Transform" = None):
        self.parent = parent
        parent.children.append(self)
        self.children = []
        self.widget = widget
        self._x_min = 0.0
        self._y_min = 0.0
        self._x_max = 0.0
        self._y_max = 0.0
        self.offset = Vector((0.0, 0.0)) # Offset from parent.
        self.size = Vector((widget.default_width, widget.default_height))
        self.pos = Vector((0.0, 0.0)) # World position.
        self.rotation = 0.0
        self.scale_x = 1.0
        self.scale_y = 1.0

    def set_anchor(self, x_min: float, y_min: float, x_max: float, y_max: float) -> None:
        parent: Transform = self.parent
        if parent is None:
            return
        self._x_min = parent.size.x * x_min
        self._y_min = parent.size.y * y_min
        self._x_max = parent.size.x * x_max
        self._y_max = parent.size.y * y_max

        self.pos = Vector((self._x_min, self._y_min))
        self.size = Vector((self._x_max - self._x_min, self._y_max - self._y_min))


class Widget:
    default_width = 100.0
    default_height = 100.0
    hitbox_shape: Literal["RECT", "CIRCLE"] = "RECT"
    z_index = 0
    use_modal = False

    def __init__(self, context: Context, parent: "Widget" = None):
        self.parent = parent
        self.children = []
        parent.add_child(self)
        self.visible = True
        self.enabled = True
        self.transform = Transform(self, parent.transform)
        self.setup(context)

    def add_child(self, child: "Widget") -> None:
        if child.parent is not None:
            child.parent.remove_child(child)
        child.parent = self
        self.children.append(child)

    def remove_child(self, child: "Widget") -> None:
        if child.parent != self:
            return
        self.children.remove(child)
        child.parent = None

    def _handle_event(self, context: Context, event: Event) -> OpReturn:
        if not self.handle_event(context, event):
            return OpReturn.PASS
        if self.use_modal:
            return OpReturn.RUN
        return OpReturn.FINISH

    def test_hit(self, p: Vector) -> bool:
        if not self.visible:
            return False
        if not self.enabled:
            return False
        t = self.transform
        if t is None:
            return False
        if self.hitbox_shape == "RECT":
            return t.pos.x <= p.x <= t.pos.x + t.size.x and t.pos.y <= p.y <= t.pos.y + t.size.y
        elif self.hitbox_shape == "CIRCLE":
            return (p.x - t.pos.x) ** 2 + (p.y - t.pos.y) ** 2 <= (t.size.x / 2) ** 2
        else:
            raise ValueError(f"Unknown hitbox shape: {self.hitbox_shape}")

    def _draw(self, context: Context) -> None:
        if not self.visible:
            return
        if not self.enabled:
            return
        t = self.transform
        if t is None:
            return

        with gpu.matrix.push_pop():
            gpu.matrix.translate(t.offset)
            if t.scale_x != 1.0 or t.scale_y != 1.0:
                gpu.matrix.scale((t.scale_x, t.scale_y))
                
            self.draw(context)

    # -------------------------------------------------------

    def setup(self, context: Context) -> None:
        pass
    
    def handle_event(self, context: Context, event: Event) -> bool:
        return True

    def draw(self, context: Context) -> None:
        pass
