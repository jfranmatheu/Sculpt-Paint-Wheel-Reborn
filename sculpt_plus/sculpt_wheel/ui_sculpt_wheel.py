"""N-panel UI: brush asset library + custom buttons."""

from __future__ import annotations

from bpy.types import Context, UILayout

from ..core import bl_types

from .data import SculptWheelData, get_wheel_storage
from .persistence import touch_wheel_storage_save_debounced


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
        box.label(text="Brush library", icon="ASSET_MANAGER")
        row = box.row(align=True)
        row.operator(
            "sculpt_plus.wheelreloadbrushlibraries",
            icon="FILE_REFRESH",
        )
        col = box.column(align=True)
        col.prop(wm, "wheel_brush_set", text="Brush set")

        cbox = layout.box()
        cbox.label(text="Custom buttons", icon="SETTINGS")
        cbox.label(text="Up to 10 actions with icons on the wheel center ring.")
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
        row.operator("sculpt_plus.wheeladdcustombutton", icon="ADD")
        if len(st.custom_buttons) > 0:
            for i, cb in enumerate(st.custom_buttons):
                r = cbox.row(align=True)
                r.label(text=f"{i}: {cb.name}")
                rm = r.operator("sculpt_plus.wheelremovecustombutton", text="", icon="X")
                rm.index = i
