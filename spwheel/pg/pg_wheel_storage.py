import bpy
from typing import Optional
from bpy.props import BoolProperty, CollectionProperty, EnumProperty, IntProperty, PointerProperty
from bpy.types import Context

from ..core.bl_types import PropertyGroup
from .pg_tarta_set import MAX_TARTA_BUTTONS, WheelTartaSet
from .pg_brush_set import BrushSet
from .default_sets import DEFAULTS_VERSION, MASKING_SET_NAME, get_tarta_set, get_masking_set, get_brush_set
from ..utils.tint_palette import default_tint

# Dynamic set dropdowns. Items are numbered with the set's index: Blender stores an enum's number, and the items are
# sorted by name, so without explicit numbers a rename (re-sort) made the stored value point at another set.
TARTA_SET_ENUM_ITEMS: list[tuple[str, str, str, int]] = [("__none__", "No sets", "No custom button sets available", 0)]
BRUSH_SET_ENUM_ITEMS: list[tuple[str, str, str, int]] = [("__none__", "No sets", "No brush sets available", 0)]

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
        TARTA_SET_ENUM_ITEMS = [("__none__", "No sets", "No custom button sets available", 0)]
    else:
        TARTA_SET_ENUM_ITEMS = [(str(idx), name, "", idx) for idx, name in entries]
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
        BRUSH_SET_ENUM_ITEMS = [("__none__", "No sets", "No brush sets available", 0)]
    else:
        BRUSH_SET_ENUM_ITEMS = [(str(idx), name, "", idx) for idx, name in entries]
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

def update_active_brush_set_index(self: "WheelBrushSetStorage", context) -> None:
    if self.active_brush_set_index < 0:
        return
    if self.brush_sets_enum != '__none__':
        if int(self.brush_sets_enum) == self.active_brush_set_index:
            return
    self.brush_sets_enum = str(self.active_brush_set_index)


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
    # The "Masking" default set is added once (also to existing data); deleting it doesn't bring it back.
    masking_set_seeded: BoolProperty(default=False)
    # Version of the default buttons this data has seen (default_sets.DEFAULTS_VERSION).
    defaults_version: IntProperty(default=0)
    # Bundled buttons created before custom tints get their default color once.
    tints_seeded: BoolProperty(default=False)
    active_tarta_set_index: IntProperty(
        name="Active Custom Buttons Set Index",
        description="Index of the active custom buttons set",
        default=-1
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
        update=update_active_brush_set_index,
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


# `context.mode` values that have a wheel.
SUPPORTED_MODES = (
    "SCULPT",
    "SCULPT_CURVES",
    "SCULPT_GREASE_PENCIL",
    "PAINT_TEXTURE",
    "PAINT_VERTEX",
    "PAINT_GREASE_PENCIL",
    "VERTEX_GREASE_PENCIL",
    "PAINT_WEIGHT",
    "WEIGHT_GREASE_PENCIL",
)

_STORAGE_ATTR_OVERRIDES = {
    "PAINT_WEIGHT": "weight",
}


def _storage_attr(mode: str) -> str:
    return _STORAGE_ATTR_OVERRIDES.get(mode, mode.lower())


class WheelStorage(PropertyGroup):
    is_initialized: BoolProperty(
        name="Initialized",
        description="Whether the wheel storage is initialized",
        default=False,
    )

    sculpt: PointerProperty(type=SculptPaintWheelStorage)
    sculpt_curves: PointerProperty(type=SculptPaintWheelStorage)
    sculpt_grease_pencil: PointerProperty(type=SculptPaintWheelStorage)

    paint_texture: PointerProperty(type=SculptPaintWheelStorage)
    paint_vertex: PointerProperty(type=SculptPaintWheelStorage)
    paint_grease_pencil: PointerProperty(type=SculptPaintWheelStorage)
    vertex_grease_pencil: PointerProperty(type=SculptPaintWheelStorage)

    # Mesh weight paint keeps its original property name so saved user data still loads.
    weight: PointerProperty(type=WeightWheelStorage)
    weight_grease_pencil: PointerProperty(type=WeightWheelStorage)

    @classmethod
    def get(cls, context: Context) -> 'WheelStorage':
        return super().get(context)

    @classmethod
    def get_by_mode(cls, context: Context | str) -> SculptPaintWheelStorage | WeightWheelStorage:
        if isinstance(context, Context):
            mode = context.mode
        else:
            mode = context
            context = bpy.context
        data = super().get(context)
        if data is None:
            return None
        return getattr(data, _storage_attr(mode), None)

    def initialize_defaults(self) -> None:
        #if self.is_initialized:
        #    return
        self.is_initialized = True

        for mode in SUPPORTED_MODES:
            storage = getattr(self, _storage_attr(mode), None)
            if storage is None:
                continue

            fresh_tarta_sets = len(getattr(storage, "tarta_sets", ())) == 0
            if default_tarta_buttons := get_tarta_set(mode):
                tarta_storage: WheelTartaSetStorage = storage
                if len(tarta_storage.tarta_sets) == 0:
                    def_tarta_set: WheelTartaSet = tarta_storage.add_tarta_set()
                    def_tarta_set.name = "Default Set"
                    for button_meta in default_tarta_buttons:
                        if isinstance(button_meta, dict):
                            def_tarta_set.add_tarta_button_from_metadata(button_meta, mode)
                elif tarta_storage.defaults_version < DEFAULTS_VERSION:
                    # Existing data: give its "Default Set" the default buttons added since (while there is room).
                    def_tarta_set = next((s for s in tarta_storage.tarta_sets if s.name == "Default Set"), None)
                    if def_tarta_set is not None:
                        have = {WheelTartaSet.button_key(b) for b in def_tarta_set.buttons}
                        for button_meta in default_tarta_buttons:
                            if len(def_tarta_set.buttons) >= MAX_TARTA_BUTTONS:
                                break
                            if isinstance(button_meta, dict) and WheelTartaSet.metadata_key(button_meta) not in have:
                                def_tarta_set.add_tarta_button_from_metadata(button_meta, mode)
                tarta_storage.defaults_version = DEFAULTS_VERSION

            if (masking_buttons := get_masking_set(mode)) and not storage.masking_set_seeded:
                tarta_storage: WheelTartaSetStorage = storage
                active_idx = tarta_storage.active_tarta_set_index
                masking_set: WheelTartaSet = tarta_storage.add_tarta_set()
                masking_set.name = MASKING_SET_NAME
                for button_meta in masking_buttons:
                    masking_set.add_tarta_button_from_metadata(button_meta, mode)
                if fresh_tarta_sets:
                    # New data: the masking set is the main default set, first and active.
                    tarta_storage.tarta_sets.move(len(tarta_storage.tarta_sets) - 1, 0)
                    tarta_storage.active_tarta_set_index = 0
                    _sync_tarta_sets_enum(tarta_storage)
                elif active_idx >= 0:
                    # Existing data: keep the set the user had active.
                    tarta_storage.active_tarta_set_index = active_idx
                    _sync_tarta_sets_enum(tarta_storage)
                storage.masking_set_seeded = True

            if hasattr(storage, "tarta_sets") and not storage.tints_seeded:
                for tarta_set in storage.tarta_sets:
                    for button in tarta_set.buttons:
                        if button.tint == "NONE":
                            button.tint = default_tint(button.image_path, mode)
                storage.tints_seeded = True

            if default_brush_names := get_brush_set(mode):
                brush_storage: WheelBrushSetStorage = storage
                if hasattr(brush_storage, "brush_sets") and len(brush_storage.brush_sets) == 0:
                    def_brush_set: BrushSet = brush_storage.add_brush_set(mode)
                    def_brush_set.name = "Default Set"
                    for brush_name in default_brush_names:
                        def_brush_set.add_brush_from_essential(mode, brush_name)

            # Re-align the set dropdowns with the active sets (saved dropdown values from older versions were
            # positions in a name-sorted list, not set indices).
            if hasattr(storage, "tarta_sets"):
                _sync_tarta_sets_enum(storage)
            if hasattr(storage, "brush_sets"):
                _sync_brush_sets_enum(storage)
