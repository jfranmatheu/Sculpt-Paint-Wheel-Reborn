"""Sculpt Wheel data model -- PropertyGroups for brush slots and toolsets."""

from bpy.props import (
    StringProperty,
    IntProperty,
    FloatVectorProperty,
    CollectionProperty,
    BoolProperty,
)
from bpy.types import Context

from ..core import bl_types


class WheelBrushSlot(bl_types.PropertyGroup):
    """A single slot in the wheel referencing a brush asset."""
    pg_parent = None  # Set by WheelToolset below.

    asset_library_type: StringProperty(name="Library Type", default='LOCAL')
    asset_library_identifier: StringProperty(name="Library ID", default="")
    relative_asset_identifier: StringProperty(name="Asset ID", default="")
    display_name: StringProperty(name="Name", default="")
    slot_color: FloatVectorProperty(
        name="Slot Color",
        subtype='COLOR_GAMMA',
        size=4,
        default=(0.4, 0.4, 0.4, 1.0),
        min=0.0, max=1.0,
    )

    def set_from_brush(self, brush, asset_ref=None) -> None:
        """Populate this slot from a loaded Brush data-block.

        *asset_ref* is an optional ``AssetWeakReference`` (e.g. from
        ``Paint.brush_asset_reference``) that carries the full asset triple.
        """
        self.display_name = brush.name
        if asset_ref is not None:
            self.asset_library_type = asset_ref.asset_library_type
            self.asset_library_identifier = asset_ref.asset_library_identifier
            self.relative_asset_identifier = asset_ref.relative_asset_identifier
        else:
            wr = getattr(brush, "asset_weak_reference", None)
            if wr is not None and getattr(wr, "relative_asset_identifier", ""):
                self.asset_library_type = wr.asset_library_type
                self.asset_library_identifier = wr.asset_library_identifier
                self.relative_asset_identifier = wr.relative_asset_identifier
            else:
                self.asset_library_type = 'LOCAL'
                self.asset_library_identifier = ""
                self.relative_asset_identifier = brush.name

    @property
    def is_valid(self) -> bool:
        return bool(self.display_name) or bool(self.relative_asset_identifier)


class WheelToolset(bl_types.PropertyGroup):
    """A named set of brush slots that the user curates."""
    pg_parent = None  # Set by SculptWheelData below.

    name: StringProperty(name="Name", default="Toolset")
    slots: CollectionProperty(type=WheelBrushSlot)
    active_slot_index: IntProperty(name="Active Slot", default=-1, min=-1)

    def add_brush(self, brush, asset_ref=None) -> WheelBrushSlot:
        slot = self.slots.add()
        slot.set_from_brush(brush, asset_ref)
        return slot

    def remove_slot(self, index: int) -> None:
        if 0 <= index < len(self.slots):
            self.slots.remove(index)
            if self.active_slot_index >= len(self.slots):
                self.active_slot_index = len(self.slots) - 1

    def move_slot(self, from_idx: int, to_idx: int) -> None:
        self.slots.move(from_idx, to_idx)

    def select_slot(self, context: Context, index: int) -> bool:
        """Activate the brush at *index*. Returns True on success."""
        if index < 0 or index >= len(self.slots):
            return False
        slot = self.slots[index]
        if not slot.is_valid:
            return False
        self.active_slot_index = index
        from .brush_assets import activate_brush_asset
        return activate_brush_asset(context, slot)


WheelBrushSlot.pg_parent = WheelToolset


class SculptWheelData(bl_types.PropertyGroupRoot.SCENE):
    """Root scene-level data for the sculpt wheel."""

    toolsets: CollectionProperty(type=WheelToolset)
    active_toolset_index: IntProperty(name="Active Toolset", default=0, min=0)
    initialized: BoolProperty(default=False)

    @property
    def active_toolset(self) -> WheelToolset | None:
        if len(self.toolsets) == 0:
            return None
        idx = min(self.active_toolset_index, len(self.toolsets) - 1)
        return self.toolsets[idx]

    def ensure_default_toolset(self, context: Context) -> WheelToolset:
        """Create a default toolset from currently loaded sculpt brushes if none exist."""
        if len(self.toolsets) > 0:
            return self.active_toolset
        ts = self.toolsets.add()
        ts.name = "Default"
        from .brush_assets import get_sculpt_brushes
        for brush in get_sculpt_brushes():
            ts.add_brush(brush)
        self.initialized = True
        return ts


WheelToolset.pg_parent = SculptWheelData
