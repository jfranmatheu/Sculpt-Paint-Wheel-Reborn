from typing import Optional
from bpy.props import BoolProperty, CollectionProperty, EnumProperty, IntProperty, PointerProperty
from bpy.types import Context

from ..core.bl_types import PropertyGroup
from .pg_tarta_set import WheelTartaSet
from .pg_brush_set import BrushSet
from .default_sets import get_tarta_set, get_brush_set

TARTA_SET_ENUM_ITEMS: list[tuple[str, str, str]] = [("__none__", "No sets", "No custom button sets available")]
BRUSH_SET_ENUM_ITEMS: list[tuple[str, str, str]] = [("__none__", "No sets", "No brush sets available")]

def _sorted_tarta_set_entries(storage: "WheelTartaSetStorage") -> list[tuple[int, str]]:
    entries: list[tuple[int, str]] = []
    for idx, tarta_set in enumerate(storage.tarta_sets):
        name = (tarta_set.name or "").strip() or f"Set {idx + 1}"
        entries.append((idx, name))
    entries.sort(key=lambda item: (item[1].lower(), item[0]))
    return entries


def enum_tarta_set_items(self: "WheelTartaSetStorage", context):
    global TARTA_SET_ENUM_ITEMS
    entries = _sorted_tarta_set_entries(self)
    if not entries:
        TARTA_SET_ENUM_ITEMS = [("__none__", "No sets", "No custom button sets available")]
    else:
        TARTA_SET_ENUM_ITEMS = [(str(idx), name, "") for idx, name in entries]
    return TARTA_SET_ENUM_ITEMS


def update_tarta_sets_enum(self: "WheelTartaSetStorage", context) -> None:
    value = self.tarta_sets_enum
    if value == "__none__":
        self.active_tarta_set_index = -1
        return
    try:
        idx = int(value)
    except (TypeError, ValueError):
        return
    if 0 <= idx < len(self.tarta_sets):
        self.active_tarta_set_index = idx


def _sync_tarta_sets_enum(storage: "WheelTartaSetStorage") -> None:
    if not storage.tarta_sets:
        storage.tarta_sets_enum = "__none__"
        storage.active_tarta_set_index = -1
        return
    active_idx = storage.active_tarta_set_index
    if not (0 <= active_idx < len(storage.tarta_sets)):
        active_idx = 0
        storage.active_tarta_set_index = active_idx
    storage.tarta_sets_enum = str(active_idx)


def _sorted_brush_set_entries(storage: "WheelBrushSetStorage") -> list[tuple[int, str]]:
    entries: list[tuple[int, str]] = []
    for idx, brush_set in enumerate(storage.brush_sets):
        name = (brush_set.name or "").strip() or f"Set {idx + 1}"
        entries.append((idx, name))
    entries.sort(key=lambda item: (item[1].lower(), item[0]))
    return entries


def enum_brush_set_items(self: "WheelBrushSetStorage", context):
    global BRUSH_SET_ENUM_ITEMS
    entries = _sorted_brush_set_entries(self)
    if not entries:
        BRUSH_SET_ENUM_ITEMS = [("__none__", "No sets", "No brush sets available")]
    else:
        BRUSH_SET_ENUM_ITEMS = [(str(idx), name, "") for idx, name in entries]
    return BRUSH_SET_ENUM_ITEMS


def update_brush_sets_enum(self: "WheelBrushSetStorage", context) -> None:
    value = self.brush_sets_enum
    if value == "__none__":
        self.active_brush_set_index = -1
        return
    try:
        idx = int(value)
    except (TypeError, ValueError):
        return
    if 0 <= idx < len(self.brush_sets):
        self.active_brush_set_index = idx


def _sync_brush_sets_enum(storage: "WheelBrushSetStorage") -> None:
    if not storage.brush_sets:
        storage.brush_sets_enum = "__none__"
        storage.active_brush_set_index = -1
        return
    active_idx = storage.active_brush_set_index
    if not (0 <= active_idx < len(storage.brush_sets)):
        active_idx = 0
        storage.active_brush_set_index = active_idx
    storage.brush_sets_enum = str(active_idx)


class WheelTartaSetStorage(PropertyGroup):
 # Tarta Sets.
    # -----------------------------------------------------------------------

    tarta_sets: CollectionProperty(type=WheelTartaSet)
    active_tarta_set_index: IntProperty(
        name="Active Custom Buttons Set Index",
        description="Index of the active custom buttons set",
        default=-1,
    )
    tarta_sets_enum: EnumProperty(
        name="Custom Button Set",
        description="Select active custom button set",
        items=enum_tarta_set_items,
        update=update_tarta_sets_enum,
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

    def add_tarta_set(self, name: Optional[str] = None) -> WheelTartaSet:
        new_tarta_set = self.tarta_sets.add()
        self.active_tarta_set_index = len(self.tarta_sets) - 1
        # Avoid duplicate names.
        name = name or f"Button Set {len(self.tarta_sets)}"
        picked_names = {t.name for t in self.tarta_sets}
        if name in picked_names:
            for i in range(1, 100):
                name = f"Button Set {i}"
                if name not in picked_names:
                    break
        new_tarta_set.name = name
        _sync_tarta_sets_enum(self)
        return new_tarta_set

    def remove_active_tarta_set(self) -> None:
        self.tarta_sets.remove(self.active_tarta_set_index)
        self.active_tarta_set_index = -1 if not self.tarta_sets else self.active_tarta_set_index - 1
        _sync_tarta_sets_enum(self)

    def move_active_tarta_set(self, direction: int) -> None:
        if direction == 1:
            target_index = (self.active_tarta_set_index - 1 + len(self.tarta_sets)) % len(self.tarta_sets)
        elif direction == -1:
            target_index = (self.active_tarta_set_index + 1) % len(self.tarta_sets)
        else:
            raise ValueError(f"Invalid direction: {direction}")
        self.tarta_sets.move(self.active_tarta_set_index, target_index)
        self.active_tarta_set_index = target_index
        _sync_tarta_sets_enum(self)

    def ensure_tarta_set(self, context: Context) -> WheelTartaSet:
        if len(self.tarta_sets) > 0:
            _sync_tarta_sets_enum(self)
            return
        # Create a default tarta set.
        new_tarta_set = self.tarta_sets.add()
        new_tarta_set.name = "Default Set"
        self.active_tarta_set_index = 0
        _sync_tarta_sets_enum(self)
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
    brush_sets_enum: EnumProperty(
        name="Brush Set",
        description="Select active brush set",
        items=enum_brush_set_items,
        update=update_brush_sets_enum,
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
    
    def add_brush_set(self, mode: str) -> BrushSet:
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
        if 'SCULPT' in mode:
            new_brush_set.wheel_type = 'SCULPT'
        elif 'VERTEX' in mode:
            new_brush_set.wheel_type = 'VERTEX'
        elif 'WEIGHT' in mode:
            new_brush_set.wheel_type = 'WEIGHT'
        else:
            new_brush_set.wheel_type = 'PAINT'
        _sync_brush_sets_enum(self)
        return new_brush_set

    def remove_active_brush_set(self) -> None:
        self.brush_sets.remove(self.active_brush_set_index)
        self.active_brush_set_index = -1 if not self.brush_sets else self.active_brush_set_index - 1
        _sync_brush_sets_enum(self)

    def move_active_brush_set(self, direction: int) -> None:
        if direction == 1:
            target_index = (self.active_brush_set_index - 1 + len(self.brush_sets)) % len(self.brush_sets)
        elif direction == -1:
            target_index = (self.active_brush_set_index + 1) % len(self.brush_sets)
        else:
            raise ValueError(f"Invalid direction: {direction}")
        self.brush_sets.move(self.active_brush_set_index, target_index)
        self.active_brush_set_index = target_index
        _sync_brush_sets_enum(self)


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
        mode_key = mode.lower()
        if mode_key in {"paint_weight", "weight_gpencil", "weight_grease_pencil"}:
            mode_key = "weight"
        return getattr(data, mode_key, None)

    def initialize_defaults(self) -> None:
        if self.is_initialized:
            return
        self.is_initialized = True

        for key in ('sculpt', 'weight'):
            mode = key.upper()
            if default_tarta_buttons := get_tarta_set(mode):
                tarta_storage: WheelTartaSetStorage = getattr(self, key)
                def_tarta_set: WheelTartaSet = tarta_storage.add_tarta_set()
                def_tarta_set.name = "Default Set"
                for button_meta in default_tarta_buttons:
                    def_tarta_set.add_tarta_button_from_metadata(button_meta)

            if default_brush_names := get_brush_set(mode):
                brush_storage: WheelBrushSetStorage = getattr(self, key)
                def_brush_set: BrushSet = brush_storage.add_brush_set()
                def_brush_set.name = "Default Set"
                for brush_name in default_brush_names:
                    def_brush_set.add_brush_from_essential(mode, brush_name)
