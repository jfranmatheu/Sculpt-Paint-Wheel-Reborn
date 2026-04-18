"""Circular / disk button base and toggle variant (mode-agnostic)."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any, Callable, Optional

from .core import Widget

if TYPE_CHECKING:
    from bpy.types import Context


class ButtonBase(Widget):
    """Hit target is a disk at ``region_pos()`` with ``hit_radius``."""

    __slots__ = ("hit_radius", "hovered", "pressed", "on_activate")

    def __init__(self, hit_radius: float = 16.0) -> None:
        super().__init__()
        self.hit_radius = float(hit_radius)
        self.hovered: bool = False
        self.pressed: bool = False
        self.on_activate: Optional[Callable[..., Any]] = None

    def hit_self(self, mx: float, my: float) -> Optional[Widget]:
        rx, ry = self._region_x, self._region_y
        if math.hypot(mx - rx, my - ry) <= self.hit_radius:
            return self
        return None

    def set_hover(self, mx: float, my: float) -> None:
        h = self.hit_self(mx, my) is not None
        self.hovered = bool(h)

    def draw_self(self, context: "Context") -> None:
        pass


class ToggleButton(ButtonBase):
    """Two-state button; ``state`` toggles on activate."""

    __slots__ = ("state",)

    def __init__(self, hit_radius: float = 16.0, initial: bool = False) -> None:
        super().__init__(hit_radius=hit_radius)
        self.state: bool = initial

    def activate(self) -> None:
        self.state = not self.state
        if self.on_activate is not None:
            self.on_activate(self)
