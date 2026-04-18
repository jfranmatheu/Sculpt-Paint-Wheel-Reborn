
from typing import TYPE_CHECKING
from bpy.types import Context
import gpu
from mathutils import Vector

if TYPE_CHECKING:
    from ..widgets import Widget



class Wheel:
    instances: dict[str, "Wheel"] = {}

    @classmethod
    def get(cls, context: Context) -> "Wheel":
        if context.mode not in cls.instances:
            cls.instances[context.mode] = cls(context)
        return cls.instances[context.mode]

    def __init__(self, context: Context) -> None:
        self.position = Vector((0.0, 0.0))
        self.size = 320
        self._widgets: list["Widget"] = []
        self.setup(context)

    def add_widget(self, widget: "Widget") -> None:
        self._widgets.append(widget)

    def setup(self, context: Context) -> None:
        pass

    def draw(self, context: Context) -> None:
        with gpu.matrix.push_pop():
            gpu.matrix.translate(self.position)
            gpu.matrix.scale((self.size, self.size, 1.0))
            for widget in self._widgets:
                widget._draw(context)
