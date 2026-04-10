"""Sculpt Wheel data model — custom buttons (prefs) + active brush set (WM)."""

from pathlib import Path

import bpy
from bpy.path import abspath as bpy_abspath

from bpy.props import (
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


def _enum_preset_menus(self, context):
    return [(a, b, c or "") for a, b, c in preset_menus]


def _enum_preset_panels(self, context):
    return [(a, b, c or "") for a, b, c in preset_panels]


def _enum_preset_operators(self, context):
    return [(a, b, c or "") for a, b, c in preset_operators]


brush_sets_items = [("NONE", "(No brush data — Reload)", "")]
def _enum_wheel_brush_sets(self, context):
    from .brush_library_cache import brush_set_display_label, list_cached_brush_set_keys
    global brush_sets_items
    keys = list_cached_brush_set_keys()
    if not keys:
        return [("NONE", "(No brush data — Reload)", "")]
    brush_sets_items = [(k, brush_set_display_label(k), "") for k in keys]
    return brush_sets_items


class WheelCustomButton(bl_types.PropertyGroup):
    """User-defined action on the inner ring of the wheel."""

    pg_parent = None  # SculptWheelStorage

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


class SculptWheelStorage(BType_PropertyGroup):
    """Global wheel custom buttons (add-on preferences)."""

    custom_buttons: CollectionProperty(type=WheelCustomButton)

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


def wheel_add_custom_button_from_create(
    context: Context,
    create: CreateWheelCustomButton | None = None,
) -> bool:
    """Append a custom button from *create* (defaults to WM ``create_custom_button``)."""
    from .custom_buttons import build_custom_button_attr

    st = get_wheel_storage(context)
    wm = SculptWheelData.get(context)
    if len(st.custom_buttons) >= 10:
        return False
    src = create or wm.create_custom_button
    attr = build_custom_button_attr(src)
    if not attr:
        return False
    b = st.custom_buttons.add()
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


def wheel_remove_custom_button(context: Context, index: int) -> None:
    st = get_wheel_storage(context)
    if 0 <= index < len(st.custom_buttons):
        st.custom_buttons.remove(index)
        from .persistence import save_wheel_storage

        save_wheel_storage(context)


def wheel_remove_all_custom_buttons(context: Context) -> None:
    st = get_wheel_storage(context)
    while len(st.custom_buttons) > 0:
        st.custom_buttons.remove(0)
    from .persistence import save_wheel_storage

    save_wheel_storage(context)


def register() -> None:
    if GLOBALS.IN_BACKGROUND:
        return
    from .brush_library_cache import ensure_brush_asset_database, refresh_brush_library_cache
    from .persistence import load_custom_buttons_if_empty, schedule_custom_buttons_load

    sculpt_data_root = Path(bpy.utils.resource_path("USER")) / "sculpt_plus_data"
    sculpt_data_root.mkdir(parents=True, exist_ok=True)
    ensure_brush_asset_database()
    refresh_brush_library_cache()
    try:
        load_custom_buttons_if_empty(bpy.context)
    except Exception:
        schedule_custom_buttons_load()


def unregister() -> None:
    pass


WheelCustomButton.pg_parent = SculptWheelStorage
CreateWheelCustomButton.pg_parent = SculptWheelData
