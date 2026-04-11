"""Sculpt Wheel data model — custom button sets (prefs) + active brush set (WM)."""

from pathlib import Path

import bpy
from bpy.path import abspath as bpy_abspath

from bpy.props import (
    BoolProperty,
    FloatVectorProperty,
    IntProperty,
    StringProperty,
    EnumProperty,
    PointerProperty,
    CollectionProperty,
)
from bpy.types import Context

from ..core import bl_types
from ..core._btypes.data.btype_pg import BType_PropertyGroup
from ..core.globals import GLOBALS

from .presets import preset_menus, preset_panels, preset_operators

MAX_CUSTOM_BUTTON_SETS = 10
MAX_CUSTOM_BUTTONS_PER_SET = 10

EVENT_SET_ICONS = (
    "EVENT_ZEROKEY",
    "EVENT_ONEKEY",
    "EVENT_TWOKEY",
    "EVENT_THREEKEY",
    "EVENT_FOURKEY",
    "EVENT_FIVEKEY",
    "EVENT_SIXKEY",
    "EVENT_SEVENKEY",
    "EVENT_EIGHTKEY",
    "EVENT_NINEKEY",
)

# Static enum items (no callback) so registration never depends on preferences context.
_WHEEL_BRUSH_CUSTOM_SET_ITEMS = tuple(
    (str(i), str(i), f"Custom button set {i}", EVENT_SET_ICONS[i], i)
    for i in range(MAX_CUSTOM_BUTTON_SETS)
)


def _enum_preset_menus(self, context):
    return [(a, b, c or "") for a, b, c in preset_menus]


def _enum_preset_panels(self, context):
    return [(a, b, c or "") for a, b, c in preset_panels]


def _enum_preset_operators(self, context):
    return [(a, b, c or "") for a, b, c in preset_operators]


def _enum_wheel_brush_sets(self, context):
    from .brush_sets_config import brush_set_enum_label, list_ordered_brush_set_keys

    wd = SculptWheelData.get(context)
    # During sync, the collection is filled before brush_sets_loaded flips; still list real keys.
    if not wd.brush_sets_loaded and len(wd.brush_set_configs) == 0:
        return [("NONE", "(Load brush data…)", "")]
    keys = list_ordered_brush_set_keys(context)
    if not keys:
        return [("NONE", "(No brush sets — load or rebuild)", "")]
    return [(k, brush_set_enum_label(context, k), "") for k in keys]


class WheelCustomButton(bl_types.PropertyGroup):
    """User-defined action on the inner ring of the wheel."""

    pg_parent = None  # WheelCustomButtonSet

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


def _wheel_custom_set_name_updated(self, context):
    from .persistence import touch_wheel_storage_save_debounced

    try:
        touch_wheel_storage_save_debounced(context)
    except Exception:
        pass


class WheelCustomButtonSet(bl_types.PropertyGroup):
    """Named group of up to 10 custom wheel buttons."""

    pg_parent = None  # SculptWheelStorage

    name: StringProperty(
        name="Set name",
        default="Button set",
        maxlen=256,
        update=_wheel_custom_set_name_updated,
    )
    custom_buttons: CollectionProperty(type=WheelCustomButton)


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


def _wheel_brush_cfg_item_updated(self, context):
    from .brush_sets_config import save_brush_set_configs_to_json

    save_brush_set_configs_to_json(context)
    if getattr(context, "region", None):
        context.region.tag_redraw()


class WheelBrushSetConfigItem(bl_types.PropertyGroup):
    """Per brush-set (shelve key) metadata persisted in JSON."""

    pg_parent = None  # SculptWheelData

    set_key: StringProperty(name="Shelve key", default="", maxlen=1024)
    library_name: StringProperty(
        name="Asset library",
        default="",
        maxlen=512,
        update=_wheel_brush_cfg_item_updated,
    )
    blend_name: StringProperty(
        name="Blend / group name",
        default="",
        maxlen=512,
        update=_wheel_brush_cfg_item_updated,
    )
    order: IntProperty(
        name="Order",
        description="Sort order in wheel / sidebar lists (lower first)",
        default=0,
        min=0,
        max=9999,
        update=_wheel_brush_cfg_item_updated,
    )
    display_name: StringProperty(
        name="Display name",
        description="Shown in the wheel / lists; leave empty to use the blend or group name",
        default="",
        maxlen=256,
        update=_wheel_brush_cfg_item_updated,
    )
    wheel_color: FloatVectorProperty(
        name="Wheel base color",
        description="RGBA tint for the wheel annulus when this set is active",
        size=4,
        min=0.0,
        max=1.0,
        default=(0.075, 0.078, 0.085, 0.97),
        subtype="COLOR",
        update=_wheel_brush_cfg_item_updated,
    )
    show_color_picker: BoolProperty(
        name="Color picker (reserved)",
        description="Reserved for a future in-wheel color UI",
        default=False,
        update=_wheel_brush_cfg_item_updated,
    )
    custom_button_set: EnumProperty(
        name="Custom button set",
        description="Which custom button set (0–9) to show when this brush set is active",
        items=_WHEEL_BRUSH_CUSTOM_SET_ITEMS,
        default="0",
        update=_wheel_brush_cfg_item_updated,
    )


class SculptWheelStorage(BType_PropertyGroup):
    """Global wheel custom buttons (add-on preferences)."""

    custom_button_sets: CollectionProperty(type=WheelCustomButtonSet)
    custom_button_set_active_index: IntProperty(
        name="Active custom set",
        default=0,
        min=0,
        max=MAX_CUSTOM_BUTTON_SETS - 1,
    )

    @classmethod
    def get_datapath(cls) -> str:
        pkg = GLOBALS.ADDON.PACKAGE_NAME
        return f"preferences.addons['{pkg}'].preferences.sculpt_wheel_storage"

    @classmethod
    def get(cls, context: Context) -> "SculptWheelStorage":
        addon = context.preferences.addons.get(GLOBALS.ADDON.PACKAGE_NAME)
        if addon is None:
            raise RuntimeError("Sculpt+ add-on is not enabled")
        return addon.preferences.sculpt_wheel_storage


class SculptWheelData(bl_types.PropertyGroupRoot.WINDOW_MANAGER):
    """Per-window-manager sculpt wheel state."""

    brush_sets_loaded: BoolProperty(
        name="Brush sets loaded",
        description="Brush shelve has been read and configs synced to this session",
        default=False,
    )
    brush_set_configs: CollectionProperty(type=WheelBrushSetConfigItem)
    brush_set_config_active_index: IntProperty(name="Active brush set config", default=0)

    wheel_brush_set: EnumProperty(
        name="Brush Set",
        description="Cached brush set (one .blend / group) shown on the wheel",
        items=_enum_wheel_brush_sets,
    )
    create_custom_button: PointerProperty(type=CreateWheelCustomButton)

    @classmethod
    def get(cls, context: Context) -> "SculptWheelData":
        return super().get(context)


def get_wheel_storage(context: Context) -> SculptWheelStorage:
    return SculptWheelStorage.get(context)


def get_active_custom_button_buttons(context: Context):
    """``custom_buttons`` collection of the active custom set, or ``None`` if none."""
    st = get_wheel_storage(context)
    if len(st.custom_button_sets) == 0:
        return None
    si = int(st.custom_button_set_active_index)
    si = max(0, min(len(st.custom_button_sets) - 1, si))
    return st.custom_button_sets[si].custom_buttons


def resolve_custom_buttons_for_brush_set(context: Context, set_key: str):
    """Custom buttons collection for the wheel brush set *set_key* (from WM config)."""
    wd = SculptWheelData.get(context)
    st = get_wheel_storage(context)
    if len(st.custom_button_sets) == 0:
        return None
    idx = 0
    for it in wd.brush_set_configs:
        if it.set_key == set_key:
            try:
                idx = int(it.custom_button_set)
            except (AttributeError, TypeError, ValueError):
                idx = 0
            idx = max(0, min(MAX_CUSTOM_BUTTON_SETS - 1, idx))
            break
    idx = min(idx, len(st.custom_button_sets) - 1)
    return st.custom_button_sets[idx].custom_buttons


def wheel_add_custom_button_from_create(
    context: Context,
    create: CreateWheelCustomButton | None = None,
) -> bool:
    """Append a custom button from *create* (defaults to WM ``create_custom_button``)."""
    from .custom_buttons import build_custom_button_attr

    st = get_wheel_storage(context)
    wm = SculptWheelData.get(context)
    buttons = get_active_custom_button_buttons(context)
    if buttons is None:
        return False
    if len(buttons) >= MAX_CUSTOM_BUTTONS_PER_SET:
        return False
    src = create or wm.create_custom_button
    attr = build_custom_button_attr(src)
    if not attr:
        return False
    b = buttons.add()
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
    from .persistence import save_wheel_storage

    save_wheel_storage(context)
    return True


def wheel_remove_custom_button(context: Context, button_index: int) -> None:
    buttons = get_active_custom_button_buttons(context)
    if buttons is None:
        return
    if 0 <= button_index < len(buttons):
        buttons.remove(button_index)
        from .persistence import save_wheel_storage

        save_wheel_storage(context)


def wheel_remove_all_custom_buttons_in_active_set(context: Context) -> None:
    buttons = get_active_custom_button_buttons(context)
    if buttons is None:
        return
    while len(buttons) > 0:
        buttons.remove(0)
    from .persistence import save_wheel_storage

    save_wheel_storage(context)


def register() -> None:
    if GLOBALS.IN_BACKGROUND:
        return
    from .persistence import load_custom_buttons_if_empty, schedule_custom_buttons_load

    sculpt_data_root = Path(bpy.utils.resource_path("USER")) / "sculpt_plus_data"
    sculpt_data_root.mkdir(parents=True, exist_ok=True)
    try:
        load_custom_buttons_if_empty(bpy.context)
    except Exception:
        schedule_custom_buttons_load()


def unregister() -> None:
    pass


WheelCustomButton.pg_parent = WheelCustomButtonSet
WheelCustomButtonSet.pg_parent = SculptWheelStorage
CreateWheelCustomButton.pg_parent = SculptWheelData
WheelBrushSetConfigItem.pg_parent = SculptWheelData
