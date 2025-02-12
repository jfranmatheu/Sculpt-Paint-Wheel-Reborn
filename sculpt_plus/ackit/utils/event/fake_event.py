from typing import Tuple

from bpy import types as bpy_types

from ..math.vector import Vector2i
from ...enums.event import EventType, EventValue




class FakeEvent:
    type: EventType | str = EventType.NONE
    value: EventValue | str = EventValue.NOTHING
    unicode: str = ''
    ascii: str = ''

    alt: bool = False
    ctrl: bool = False
    shift: bool = False
    oskey: bool = False

    tilt: Tuple[float, float] = (0.0, 0.0)
    pressure: float = 0.0

    is_tablet: bool = False
    is_repeat: bool = False
    is_mouse_absolute: bool = False

    mouse_x: Tuple[int, int] = (0, 0)
    mouse_y: Tuple[int, int] = (0, 0)
    mouse_region_x: Tuple[int, int] = (0, 0)
    mouse_region_y: Tuple[int, int] = (0, 0)
    mouse_prev_x: Tuple[int, int] = (0, 0)
    mouse_prev_y: Tuple[int, int] = (0, 0)

    @classmethod
    def from_modal_event(cls, modal_event: bpy_types.Event) -> 'FakeEvent':
        return cls().update(modal_event)        

    def update(self, event: bpy_types.Event) -> None:
        self.type = event.type
        self.value = event.value
        self.alt = event.alt
        self.ctrl = event.ctrl
        self.shift = event.shift
        self.unicode = event.unicode
        self.ascii = event.ascii
        self.mouse_region_x = event.mouse_region_x
        self.mouse_region_y = event.mouse_region_y

    def get_mouse_region_pos(self):
        return Vector2i(self.mouse_region_x, self.mouse_region_y)
