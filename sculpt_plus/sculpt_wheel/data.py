"""Sculpt Wheel data model — custom button sets (prefs) + active brush library/blend (WM)."""

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

_WHEEL_BRUSH_CUSTOM_SET_ITEMS = (
    (
        "ACTIVE",
        "Active",
        "Use the custom button set selected in the sidebar (active index)",
        "LINKED",
        MAX_CUSTOM_BUTTON_SETS,
    ),
) + tuple(
    (str(i), str(i), f"Custom button set {i}", EVENT_SET_ICONS[i], i)
    for i in range(MAX_CUSTOM_BUTTON_SETS)
)

DEFAULT_WHEEL_COLOR = (0.075, 0.078, 0.085, 0.97)


def _enum_preset_menus(self, context):
    return [(a, b, c or "") for a, b, c in preset_menus]


def _enum_preset_panels(self, context):
    return [(a, b, c or "") for a, b, c in preset_panels]


def _enum_preset_operators(self, context):
    return [(a, b, c or "") for a, b, c in preset_operators]


def _enum_wheel_brush_libraries(self, context):
    """Dynamic enum: one entry per (library_id, blend_id) in the loaded index."""
    from ..src.brush_management import is_loaded, list_library_blend_keys

    if not is_loaded():
        return [("NONE", "(Preparing brush data…)", "")]
    keys = list_library_blend_keys()
    if not keys:
        return [("NONE", "(No brush libraries — sync or add asset libraries)", "")]
    return [(f"{lid}|{bid}", label, "") for lid, bid, label in keys]


_BRUSH_ACTIVE_SYNC_DEPTH = 0


def _sync_list_index_from_active_blend(wd: "SculptWheelData") -> None:
    n = len(wd.brush_lib_configs)
    if n <= 0:
        return
    key = wd.wheel_active_blend
    if not key or key == "NONE":
        return
    for i, it in enumerate(wd.brush_lib_configs):
        if it.blend_key == key:
            if int(wd.brush_lib_config_active_index) != i:
                wd.brush_lib_config_active_index = i
            break


def _wheel_active_blend_updated(self, context: Context) -> None:
    global _BRUSH_ACTIVE_SYNC_DEPTH
    if _BRUSH_ACTIVE_SYNC_DEPTH:
        return
    _BRUSH_ACTIVE_SYNC_DEPTH += 1
    try:
        _sync_list_index_from_active_blend(self)
    finally:
        _BRUSH_ACTIVE_SYNC_DEPTH -= 1


def _brush_lib_config_active_index_updated(self, context: Context) -> None:
    global _BRUSH_ACTIVE_SYNC_DEPTH
    if _BRUSH_ACTIVE_SYNC_DEPTH:
        return
    wd = self
    n = len(wd.brush_lib_configs)
    if n <= 0:
        return
    _BRUSH_ACTIVE_SYNC_DEPTH += 1
    try:
        idx = max(0, min(n - 1, int(wd.brush_lib_config_active_index)))
        if int(wd.brush_lib_config_active_index) != idx:
            wd.brush_lib_config_active_index = idx
        key = wd.brush_lib_configs[idx].blend_key
        if wd.wheel_active_blend != key:
            wd.wheel_active_blend = key
    finally:
        _BRUSH_ACTIVE_SYNC_DEPTH -= 1


def sync_brush_lib_list_index(context: Context) -> None:
    """Ensure UIList selection matches ``wheel_active_blend``."""
    _wheel_active_blend_updated(SculptWheelData.get(context), context)


# ──────────────────────────────────────────────────────────────────────
# Custom Buttons (unchanged from original)
# ──────────────────────────────────────────────────────────────────────

class WheelCustomButton(bl_types.PropertyGroup):
    pg_parent = None

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
    pg_parent = None

    name: StringProperty(
        name="Set name",
        default="Button set",
        maxlen=256,
        update=_wheel_custom_set_name_updated,
    )
    custom_buttons: CollectionProperty(type=WheelCustomButton)


class CreateWheelCustomButton(bl_types.PropertyGroup):
    pg_parent = None

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


# ──────────────────────────────────────────────────────────────────────
# Brush Library Config (per-blend metadata for the wheel)
# ──────────────────────────────────────────────────────────────────────

def _wheel_brush_lib_cfg_updated(self, context):
    from .brush_lib_config import clamp_brush_lib_item_pages, save_brush_lib_configs_to_json
    clamp_brush_lib_item_pages(context, self)
    save_brush_lib_configs_to_json(context)
    if getattr(context, "region", None):
        context.region.tag_redraw()


class WheelBrushLibConfigItem(bl_types.PropertyGroup):
    """Per brush library/blend metadata for the wheel UI."""

    pg_parent = None

    blend_key: StringProperty(name="Blend key", default="", maxlen=2048)
    library_id: StringProperty(name="Library ID", default="", maxlen=256)
    blend_id: StringProperty(name="Blend ID", default="", maxlen=256)
    library_name: StringProperty(
        name="Library name",
        default="",
        maxlen=512,
        update=_wheel_brush_lib_cfg_updated,
    )
    blend_name: StringProperty(
        name="Blend name",
        default="",
        maxlen=512,
        update=_wheel_brush_lib_cfg_updated,
    )
    order: IntProperty(
        name="Order",
        default=0,
        min=0,
        max=9999,
        update=_wheel_brush_lib_cfg_updated,
    )
    display_name: StringProperty(
        name="Display name",
        default="",
        maxlen=256,
        update=_wheel_brush_lib_cfg_updated,
    )
    wheel_color: FloatVectorProperty(
        name="Wheel base color",
        size=4,
        min=0.0,
        max=1.0,
        default=DEFAULT_WHEEL_COLOR,
        subtype="COLOR",
        update=_wheel_brush_lib_cfg_updated,
    )
    custom_button_set: EnumProperty(
        name="Custom button set",
        items=_WHEEL_BRUSH_CUSTOM_SET_ITEMS,
        default="ACTIVE",
        update=_wheel_brush_lib_cfg_updated,
    )
    active_page: IntProperty(
        name="Active page",
        description="Wheel page index for this library (clamped to available pages)",
        default=0,
        min=0,
        max=511,
        soft_max=31,
        update=_wheel_brush_lib_cfg_updated,
    )


# ──────────────────────────────────────────────────────────────────────
# Storage (addon prefs) & WM data
# ──────────────────────────────────────────────────────────────────────

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

    brush_libs_loaded: BoolProperty(
        name="Libraries loaded",
        default=False,
    )
    brush_lib_configs: CollectionProperty(type=WheelBrushLibConfigItem)
    brush_lib_config_active_index: IntProperty(
        name="Active library config",
        default=0,
        min=0,
        update=_brush_lib_config_active_index_updated,
    )

    wheel_active_blend: EnumProperty(
        name="Active Brush Library",
        description="Active brush library blend on the wheel",
        items=_enum_wheel_brush_libraries,
        update=_wheel_active_blend_updated,
    )
    create_custom_button: PointerProperty(type=CreateWheelCustomButton)

    @classmethod
    def get(cls, context: Context) -> "SculptWheelData":
        return super().get(context)


def get_wheel_storage(context: Context) -> SculptWheelStorage:
    return SculptWheelStorage.get(context)


def get_active_custom_button_buttons(context: Context):
    st = get_wheel_storage(context)
    if len(st.custom_button_sets) == 0:
        return None
    si = int(st.custom_button_set_active_index)
    si = max(0, min(len(st.custom_button_sets) - 1, si))
    return st.custom_button_sets[si].custom_buttons


def resolve_custom_buttons_for_blend(context: Context, blend_key: str):
    """Custom buttons collection for the given blend_key (from WM config)."""
    wd = SculptWheelData.get(context)
    st = get_wheel_storage(context)
    if len(st.custom_button_sets) == 0:
        return None
    idx = 0
    for it in wd.brush_lib_configs:
        if it.blend_key == blend_key:
            if getattr(it, "custom_button_set", None) == "ACTIVE":
                idx = int(st.custom_button_set_active_index)
            else:
                try:
                    idx = int(it.custom_button_set)
                except (AttributeError, TypeError, ValueError):
                    idx = 0
                idx = max(0, min(MAX_CUSTOM_BUTTON_SETS - 1, idx))
            break
    idx = max(0, min(len(st.custom_button_sets) - 1, idx))
    return st.custom_button_sets[idx].custom_buttons


def wheel_add_custom_button_from_create(
    context: Context,
    create: CreateWheelCustomButton | None = None,
) -> bool:
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


# ──────────────────────────────────────────────────────────────────────
# Parse active blend key
# ──────────────────────────────────────────────────────────────────────

def parse_blend_key(blend_key: str) -> tuple[str, str]:
    """Split ``"library_id|blend_id"`` into ``(library_id, blend_id)``."""
    if "|" in blend_key:
        parts = blend_key.split("|", 1)
        return parts[0], parts[1]
    return "", ""


def make_blend_key(library_id: str, blend_id: str) -> str:
    return f"{library_id}|{blend_id}"


# ──────────────────────────────────────────────────────────────────────
# Register / Unregister
# ──────────────────────────────────────────────────────────────────────

def register() -> None:
    if GLOBALS.IN_BACKGROUND:
        return
    from ..src.brush_management.handlers import register_handlers
    from .persistence import load_custom_buttons_if_empty, schedule_custom_buttons_load
    from .brush_lib_config import schedule_brush_lib_bootstrap

    sculpt_data_root = Path(bpy.utils.resource_path("USER")) / "sculpt_plus_data"
    sculpt_data_root.mkdir(parents=True, exist_ok=True)

    register_handlers()

    try:
        load_custom_buttons_if_empty(bpy.context)
    except Exception:
        schedule_custom_buttons_load()

    schedule_brush_lib_bootstrap()


def unregister() -> None:
    from ..src.brush_management.handlers import unregister_handlers
    from ..src.brush_management import reset
    unregister_handlers()
    reset()


WheelCustomButton.pg_parent = WheelCustomButtonSet
WheelCustomButtonSet.pg_parent = SculptWheelStorage
CreateWheelCustomButton.pg_parent = SculptWheelData
WheelBrushLibConfigItem.pg_parent = SculptWheelData
