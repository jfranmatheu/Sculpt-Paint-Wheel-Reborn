"""N-panel UI: brush library + custom buttons."""

from __future__ import annotations

from bpy.types import Context, UILayout

from ..core import bl_types
from ..core.globals import GLOBALS

from .data import (
    SculptWheelData,
    get_active_custom_button_buttons,
    get_wheel_storage,
    sync_brush_lib_list_index,
)
from .op_wheel_ui import WheelBrushLibMove
from .persistence import touch_wheel_storage_save_debounced
from .ui_wheel_brush_sets import SculptWheelBrushLibsUIList, SculptWheelCustomButtonSetsUIList


class SculptWheelSidebarPanel(bl_types.PanelPresets.VIEW_3D_SIDEBAR):
    """Sculpt mode sidebar: wheel library + custom buttons."""

    bl_label = "Sculpt Wheel"

    @classmethod
    def poll(cls, context: Context) -> bool:
        return context.mode == "SCULPT"

    @classmethod
    def draw_ui(cls, context: Context, layout: UILayout) -> None:
        wm = SculptWheelData.get(context)
        st = get_wheel_storage(context)
        touch_wheel_storage_save_debounced(context)

        box = layout.box()
        aid = GLOBALS.ADDON.ID
        hdr = box.row()
        split = hdr.split(factor=0.88)
        split.label(text="Brush libraries", icon="ASSET_MANAGER")
        row = split.row()
        row.ui_units_x = 1
        row.alignment = 'RIGHT'
        row.operator(
            f"{aid}.wheelreloadbrushlibraries",
            text="",
            icon="FILE_REFRESH",
        )
        if not wm.brush_libs_loaded:
            box.label(
                text="Preparing libraries (first run may take a minute). Use reload if this persists.",
            )
        col = box.column(align=True)
        col.label(text="Wheel brush library (click a row):")
        sync_brush_lib_list_index(context)
        n_cfg = len(wm.brush_lib_configs)
        rows = min(8, max(4, n_cfg)) if n_cfg else 4
        split = col.split(factor=0.9)
        left = split.column()
        left.template_list(
            SculptWheelBrushLibsUIList.bl_idname,
            "",
            wm,
            "brush_lib_configs",
            wm,
            "brush_lib_config_active_index",
            rows=rows,
        )
        right = split.column(align=True)
        mup = right.operator(WheelBrushLibMove.bl_idname, text="", icon="TRIA_UP")
        mup.direction = "UP"
        mdn = right.operator(WheelBrushLibMove.bl_idname, text="", icon="TRIA_DOWN")
        mdn.direction = "DOWN"

        cbox = layout.box()
        cbox.label(text="Custom button sets", icon="SETTINGS")
        cbox.label(text="Up to 10 sets × 10 actions, shown on the wheel inner ring.")
        r0 = cbox.row(align=True)
        r0.operator(
            f"{aid}.wheeladdcustombuttonset",
            text="Add set",
            icon="ADD",
        )
        r0.operator(
            f"{aid}.wheelremovecustombuttonset",
            text="Remove set",
            icon="REMOVE",
        )
        n_sets = len(st.custom_button_sets)
        set_rows = min(6, max(3, n_sets)) if n_sets else 3
        cbox.template_list(
            SculptWheelCustomButtonSetsUIList.bl_idname,
            "",
            st,
            "custom_button_sets",
            st,
            "custom_button_set_active_index",
            rows=set_rows,
        )

        cbox.separator()
        cbox.label(text="Add button to active set", icon="PLUS")
        create = wm.create_custom_button
        col = cbox.column(align=True)
        col.prop(create, "name")
        col.prop(create, "image_path")
        col.prop(create, "type")
        if create.type == "OPERATOR":
            col.prop(create, "operator_type")
            if create.operator_type == "PRESET":
                col.prop(create, "preset_operator")
            else:
                col.prop(create, "custom_operator", text="Code")
        else:
            col.prop(create, "popup_type")
            if create.popup_type == "MENU":
                col.prop(create, "menu_source")
                if create.menu_source == "PRESET":
                    col.prop(create, "preset_menu")
                else:
                    col.prop(create, "custom_menu")
            else:
                col.prop(create, "panel_source")
                if create.panel_source == "PRESET":
                    col.prop(create, "preset_panel")
                else:
                    col.prop(create, "custom_panel")
        row = cbox.row(align=True)
        row.operator(f"{aid}.wheeladdcustombutton", icon="ADD")
        buttons = get_active_custom_button_buttons(context)
        if buttons is not None and len(buttons) > 0:
            for i, cb in enumerate(buttons):
                r = cbox.row(align=True)
                r.label(text=f"{i}: {cb.name}")
                rm = r.operator(f"{aid}.wheelremovecustombutton", text="", icon="X")
                rm.index = i
