"""Sculpt Wheel data model -- PropertyGroups for brush slots and toolsets."""

from bpy.path import abspath as bpy_abspath

from bpy.props import (
    StringProperty,
    IntProperty,
    FloatVectorProperty,
    CollectionProperty,
    BoolProperty,
    EnumProperty,
    PointerProperty,
)
from bpy.types import Context

from ..core import bl_types

from .presets import preset_menus, preset_panels, preset_operators


def _enum_preset_menus(self, context):
    return [(a, b, c or "") for a, b, c in preset_menus]


def _enum_preset_panels(self, context):
    return [(a, b, c or "") for a, b, c in preset_panels]


def _enum_preset_operators(self, context):
    return [(a, b, c or "") for a, b, c in preset_operators]


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

    def swap_slots(self, a: int, b: int) -> None:
        """Swap two brush slots (order in the wheel)."""
        if a == b:
            return
        n = len(self.slots)
        if not (0 <= a < n and 0 <= b < n):
            return
        sa = self.slots[a]
        sb = self.slots[b]
        fields = (
            "asset_library_type",
            "asset_library_identifier",
            "relative_asset_identifier",
            "display_name",
        )
        tmp = {f: getattr(sa, f) for f in fields}
        tmp_color = tuple(sa.slot_color)
        for f in fields:
            setattr(sa, f, getattr(sb, f))
        sa.slot_color = tuple(sb.slot_color)
        for f in fields:
            setattr(sb, f, tmp[f])
        sb.slot_color = tmp_color
        if self.active_slot_index == a:
            self.active_slot_index = b
        elif self.active_slot_index == b:
            self.active_slot_index = a

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


class WheelCustomButton(bl_types.PropertyGroup):
    """User-defined action on the inner ring of the wheel."""

    pg_parent = None  # SculptWheelData

    name: StringProperty(name="Name", default="Custom")
    type: EnumProperty(
        name="Action Type",
        items=(
            ("OPERATOR", "Operator", "Run Python / preset operator"),
            ("POPUP", "Popup", "Open a menu or panel"),
        ),
    )
    popup_type: EnumProperty(
        name="Popup Kind",
        items=(
            ("NONE", "—", "Not used for operators"),
            ("MENU", "Menu", ""),
            ("PANEL", "Panel", ""),
        ),
        default="NONE",
    )
    attr: StringProperty(name="Payload", default="", maxlen=4096)
    image_path: StringProperty(name="Icon Path", default="", subtype="FILE_PATH")


class CreateWheelCustomButton(bl_types.PropertyGroup):
    """Temporary settings used when adding a custom button from the sidebar."""

    pg_parent = None  # SculptWheelData

    name: StringProperty(name="Name", default="Button")
    image_path: StringProperty(name="Icon Image", default="", subtype="FILE_PATH")

    type: EnumProperty(
        name="Type",
        items=(
            ("OPERATOR", "Operator", ""),
            ("POPUP", "Popup", ""),
        ),
    )
    operator_type: EnumProperty(
        name="Operator",
        items=(
            ("PRESET", "Preset", ""),
            ("CUSTOM", "Custom", ""),
        ),
        default="PRESET",
    )
    preset_operator: EnumProperty(name="Preset Operator", items=_enum_preset_operators)
    custom_operator: StringProperty(
        name="Custom Code",
        default="bpy.ops.sculpt.brush_stroke()",
        maxlen=2048,
    )

    popup_type: EnumProperty(
        name="Popup",
        items=(
            ("MENU", "Menu", ""),
            ("PANEL", "Panel", ""),
        ),
        default="MENU",
    )
    menu_source: EnumProperty(
        name="Menu Source",
        items=(
            ("PRESET", "Preset", ""),
            ("CUSTOM", "Custom", ""),
        ),
        default="PRESET",
    )
    preset_menu: EnumProperty(name="Preset Menu", items=_enum_preset_menus)
    custom_menu: StringProperty(name="Menu ID", default="VIEW3D_MT_sculpt", maxlen=256)

    panel_source: EnumProperty(
        name="Panel Source",
        items=(
            ("PRESET", "Preset", ""),
            ("CUSTOM", "Custom", ""),
        ),
        default="PRESET",
    )
    preset_panel: EnumProperty(name="Preset Panel", items=_enum_preset_panels)
    custom_panel: StringProperty(
        name="Panel ID",
        default="VIEW3D_PT_tools_brush_settings_advanced",
        maxlen=256,
    )


class SculptWheelData(bl_types.PropertyGroupRoot.SCENE):
    """Root scene-level data for the sculpt wheel."""

    toolsets: CollectionProperty(type=WheelToolset)
    active_toolset_index: IntProperty(name="Active Toolset", default=0, min=0)
    initialized: BoolProperty(default=False)

    custom_buttons: CollectionProperty(type=WheelCustomButton)
    create_custom_button: PointerProperty(type=CreateWheelCustomButton)

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

    def add_custom_button_from_create(self, create: CreateWheelCustomButton | None = None) -> bool:
        """Append a custom button from *create* (defaults to ``create_custom_button``)."""
        from .custom_buttons import build_custom_button_attr

        if len(self.custom_buttons) >= 10:
            return False
        src = create or self.create_custom_button
        attr = build_custom_button_attr(src)
        if not attr:
            return False
        b = self.custom_buttons.add()
        b.name = (src.name or "Custom").strip() or "Custom"
        b.type = src.type
        if src.type == "POPUP":
            b.popup_type = src.popup_type
        else:
            b.popup_type = "NONE"
        b.attr = attr
        ip = src.image_path
        if ip.startswith("//"):
            ip = bpy_abspath(ip)
        b.image_path = ip
        return True

    def remove_custom_button(self, index: int) -> None:
        if 0 <= index < len(self.custom_buttons):
            self.custom_buttons.remove(index)

    def remove_all_custom_buttons(self) -> None:
        while len(self.custom_buttons) > 0:
            self.custom_buttons.remove(0)


WheelToolset.pg_parent = SculptWheelData
WheelCustomButton.pg_parent = SculptWheelData
CreateWheelCustomButton.pg_parent = SculptWheelData
