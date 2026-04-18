"""
Widget tree and wheel-local transforms.

Geometry uses **region pixel space** (``mouse_region_x`` / ``mouse_region_y``).
Children store offsets **relative to the wheel center**; ``WheelRoot`` maps
local → region. No Blender mode or RNA imports.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterator, Optional

if TYPE_CHECKING:
    from bpy.types import Context


class Widget:
    """Tree node: optional parent, ordered children, visibility, layout cache."""

    __slots__ = ("parent", "children", "visible", "enabled", "local_x", "local_y", "_region_x", "_region_y")

    def __init__(self) -> None:
        self.parent: Optional[Widget] = None
        self.children: list[Widget] = []
        self.visible: bool = True
        self.enabled: bool = True
        self.local_x: float = 0.0
        self.local_y: float = 0.0
        self._region_x: float = 0.0
        self._region_y: float = 0.0

    def add_child(self, child: Widget, index: int | None = None) -> None:
        child.parent = self
        if index is None:
            self.children.append(child)
        else:
            self.children.insert(index, child)

    def remove_child(self, child: Widget) -> None:
        if child in self.children:
            self.children.remove(child)
        if child.parent is self:
            child.parent = None

    def wheel_root(self) -> Optional["WheelRoot"]:
        w: Optional[Widget] = self
        while w is not None:
            if isinstance(w, WheelRoot):
                return w
            w = w.parent
        return None

    def region_pos(self) -> tuple[float, float]:
        return (self._region_x, self._region_y)

    def set_local(self, lx: float, ly: float) -> None:
        self.local_x = float(lx)
        self.local_y = float(ly)

    def layout(self) -> None:
        root = self.wheel_root()
        if root is not None:
            self._region_x, self._region_y = root.to_region(self.local_x, self.local_y)
        for child in self.children:
            child.layout()

    def hit_test(self, mx: float, my: float) -> Optional["Widget"]:
        if not self.visible or not self.enabled:
            return None
        for child in reversed(self.children):
            hit = child.hit_test(mx, my)
            if hit is not None:
                return hit
        return self.hit_self(mx, my)

    def hit_self(self, mx: float, my: float) -> Optional["Widget"]:
        return None

    def draw(self, context: "Context") -> None:
        if not self.visible:
            return
        self.draw_self(context)
        for child in self.children:
            child.draw(context)

    def draw_self(self, context: "Context") -> None:
        pass

    def iter_subtree(self) -> Iterator["Widget"]:
        yield self
        for c in self.children:
            yield from c.iter_subtree()


class WheelRoot(Widget):
    """Radial wheel anchor: center and radius in region pixels."""

    __slots__ = ("center_x", "center_y", "radius")

    def __init__(self, center_x: float, center_y: float, radius: float) -> None:
        super().__init__()
        self.center_x = float(center_x)
        self.center_y = float(center_y)
        self.radius = float(radius)

    def to_region(self, lx: float, ly: float) -> tuple[float, float]:
        return (self.center_x + lx, self.center_y + ly)

    def to_local(self, rx: float, ry: float) -> tuple[float, float]:
        return (rx - self.center_x, ry - self.center_y)

    def contains_point(self, mx: float, my: float) -> bool:
        dx = mx - self.center_x
        dy = my - self.center_y
        return (dx * dx + dy * dy) <= self.radius * self.radius

    def layout(self) -> None:
        self._region_x = self.center_x
        self._region_y = self.center_y
        for child in self.children:
            child.layout()

    def hit_test(self, mx: float, my: float) -> Optional[Widget]:
        if not self.visible or not self.enabled:
            return None
        if not self.contains_point(mx, my):
            return None
        hit = Widget.hit_test(self, mx, my)
        return hit if hit is not None else self


def layout_all(root: WheelRoot) -> None:
    root.layout()


def draw_all(root: WheelRoot, context: "Context") -> None:
    root.draw(context)


def hit_all(root: WheelRoot, mx: float, my: float) -> Optional[Widget]:
    return root.hit_test(mx, my)
