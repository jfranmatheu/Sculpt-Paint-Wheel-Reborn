from bpy import types as bpy_types

from ...utils.math.vector import Vector2i
from .fake_event import FakeEvent

__all__ = [
    'Mouse',
]


class Mouse:
    current: Vector2i   # current mouse position.
    prev: Vector2i      # previous mouse position.
    start: Vector2i     # initial mouse position.
    offset: Vector2i    # mouse offset between initial position and current position.
    delta: Vector2i     # difference of mouse position between prev and current.
    dir: Vector2i       # direction of mouse taking into account previous position.
    local: Vector2i     # local space coordinates.
    local_rel: Vector2i # local space coordinates, relative factor between [0, 1].
    enough_movement: bool

    @staticmethod
    def init(event: bpy_types.Event | FakeEvent, rect=None) -> 'Mouse':
        mouse = Mouse()
        mouse.start = Vector2i(event.mouse_region_x, event.mouse_region_y)
        mouse.current = mouse.start.copy()
        mouse.prev = mouse.start.copy()
        mouse.offset = Vector2i(0, 0)
        mouse.delta = Vector2i(0, 0)
        mouse.dir = Vector2i(0, 0)
        mouse.enough_movement = True
        if rect:
            mouse.local = mouse.current - Vector2i(*rect.position)
            size = Vector2i(*rect.size)
            size.clamp(1, 10000000)
            mouse.local_rel = mouse.local / size
            mouse.local_rel.clamp(0, 1)
        return mouse

    def update(self, event: bpy_types.Event | FakeEvent, rect=None, delta_limit=0) -> None:
        if delta_limit != 0:
            delta_x = self.current.x - self.prev.x
            delta_y = self.current.y - self.prev.y
            if delta_x < delta_limit and delta_y < delta_limit:
                self.enough_movement = False
                return

        self.delta.x = self.current.x - self.prev.x
        self.delta.y = self.current.y - self.prev.y
        self.prev.x = self.current.x
        self.prev.y = self.current.y
        self.current.x = event.mouse_region_x
        self.current.y = event.mouse_region_y
        self.offset.x = self.current.x - self.start.x
        self.offset.y = self.current.y - self.start.y
        
        self.dir.x = 0 if self.delta.x==0 else 1 if self.delta.x > 0 else -1
        self.dir.y = 0 if self.delta.y==0 else 1 if self.delta.y > 0 else -1
        if rect:
            self.local = self.current - Vector2i(*rect.position)
            self.local_rel = self.local / Vector2i(*rect.size)
            self.local_rel.clamp(0, 1)
