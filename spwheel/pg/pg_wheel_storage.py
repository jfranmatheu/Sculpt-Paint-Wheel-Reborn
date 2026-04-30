from bpy.props import BoolProperty, CollectionProperty, IntProperty, PointerProperty
from bpy.types import Context

from ..core.bl_types import PropertyGroup
from .pg_tarta_set import WheelTartaSet
from .pg_brush_set import BrushSet
from .default_sets import get_tarta_set, get_brush_set


class WheelTartaSetStorage(PropertyGroup):
 # Tarta Sets.
    # -----------------------------------------------------------------------

    tarta_sets: CollectionProperty(type=WheelTartaSet)
    active_tarta_set_index: IntProperty(
        name="Active Custom Buttons Set Index",
        description="Index of the active custom buttons set",
        default=-1,
    )

    @property
    def active_tarta_set(self) -> WheelTartaSet:
        if not self.tarta_sets:
            return None
        if self.active_tarta_set_index < 0:
            return None
        if self.active_tarta_set_index >= len(self.tarta_sets):
            return None
        return self.tarta_sets[self.active_tarta_set_index]

    def add_tarta_set(self) -> WheelTartaSet:
        new_tarta_set = self.tarta_sets.add()
        self.active_tarta_set_index = len(self.tarta_sets) - 1
        # Avoid duplicate names.
        name = f"Button Set {len(self.tarta_sets)}"
        picked_names = {t.name for t in self.tarta_sets}
        if name in picked_names:
            for i in range(1, 100):
                name = f"Button Set {i}"
                if name not in picked_names:
                    break
        new_tarta_set.name = name
        return new_tarta_set

    def remove_active_tarta_set(self) -> None:
        self.tarta_sets.remove(self.active_tarta_set_index)
        self.active_tarta_set_index = -1 if not self.tarta_sets else self.active_tarta_set_index - 1

    def move_active_tarta_set(self, direction: int) -> None:
        if direction == 1:
            target_index = (self.active_tarta_set_index - 1 + len(self.tarta_sets)) % len(self.tarta_sets)
        elif direction == -1:
            target_index = (self.active_tarta_set_index + 1) % len(self.tarta_sets)
        else:
            raise ValueError(f"Invalid direction: {direction}")
        self.tarta_sets.move(self.active_tarta_set_index, target_index)
        self.active_tarta_set_index = target_index

    def ensure_tarta_set(self, context: Context) -> WheelTartaSet:
        if len(self.tarta_sets) > 0:
            return
        # Create a default tarta set.
        new_tarta_set = self.tarta_sets.add()
        new_tarta_set.name = "Default Set"

        return new_tarta_set


class WheelBrushSetStorage(PropertyGroup):
    # Wheel Data: Brush Sets.
    # -----------------------------------------------------------------------

    brush_sets: CollectionProperty(type=BrushSet)
    active_brush_set_index: IntProperty(
        name="Active Brush Set Index",
        description="Index of the active brush set",
        default=-1,
    )

    @property
    def active_brush_set(self) -> BrushSet:
        if not self.brush_sets:
            return None
        if self.active_brush_set_index < 0:
            return None
        if self.active_brush_set_index >= len(self.brush_sets):
            return None
        return self.brush_sets[self.active_brush_set_index]
    
    def add_brush_set(self) -> BrushSet:
        new_brush_set = self.brush_sets.add()
        self.active_brush_set_index = len(self.brush_sets) - 1
        # Avoid duplicate names.
        name = f"Brush Set {len(self.brush_sets)}"
        picked_names = {t.name for t in self.brush_sets}
        if name in picked_names:
            for i in range(1, 100):
                name = f"Brush Set {i}"
                if name not in picked_names:
                    break
        new_brush_set.name = name
        return new_brush_set

    def remove_active_brush_set(self) -> None:
        self.brush_sets.remove(self.active_brush_set_index)
        self.active_brush_set_index = -1 if not self.brush_sets else self.active_brush_set_index - 1

    def move_active_brush_set(self, direction: int) -> None:
        if direction == 1:
            target_index = (self.active_brush_set_index - 1 + len(self.brush_sets)) % len(self.brush_sets)
        elif direction == -1:
            target_index = (self.active_brush_set_index + 1) % len(self.brush_sets)
        else:
            raise ValueError(f"Invalid direction: {direction}")
        self.brush_sets.move(self.active_brush_set_index, target_index)
        self.active_brush_set_index = target_index


class SculptPaintWheelStorage(WheelTartaSetStorage, WheelBrushSetStorage, PropertyGroup):
    pass


class WeightWheelStorage(WheelTartaSetStorage, PropertyGroup):
    pass


class WheelStorage(PropertyGroup):
    is_initialized: BoolProperty(
        name="Initialized",
        description="Whether the wheel storage is initialized",
        default=False,
    )

    sculpt: PointerProperty(type=SculptPaintWheelStorage)
    paint_texture: PointerProperty(type=SculptPaintWheelStorage)
    weight: PointerProperty(type=WeightWheelStorage)

    @classmethod
    def get(cls, context: Context) -> 'WheelStorage':
        return super().get(context)

    @classmethod
    def get_by_mode(cls, context: Context | str) -> SculptPaintWheelStorage | WeightWheelStorage:
        if isinstance(context, Context):
            mode = context.mode
        else:
            mode = context
        data = super().get(context)
        if data is None:
            return None
        return getattr(data, mode.lower(), None)

    def initialize(self) -> None:
        if self.is_initialized:
            return
        self.is_initialized = True

        for key in ('sculpt', ): #, 'paint_texture', 'weight'):
            '''if def_tarta_set := get_tarta_set(key):
                tarta_storage: WheelTartaSetStorage = getattr(self, key)
                def_tarta_set: WheelTartaSet = tarta_storage.active_tarta_set()
                for tool_set in def_tarta_set:
                    def_tarta_set.add_tarta_button_from_metadata(tool_set)'''
            if defaults_metadata := get_brush_set(key.upper()):
                brush_storage: WheelBrushSetStorage = getattr(self, key)
                def_brush_set: BrushSet = brush_storage.add_brush_set()
                def_brush_set.name = "Default Set"
                for brush_metadata in defaults_metadata:
                    def_brush_set.add_brush_from_metadata(brush_metadata)
