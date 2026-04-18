"""UIList: brush library rows with optional per-row page list."""

from __future__ import annotations

from bpy.types import Context, UIList, UILayout

from ..core import bl_types

from .brush_lib_config import blend_display_label, get_active_page, page_rows_for_blend_item
from .data import EVENT_SET_ICONS
from .op_wheel_ui import WheelSetBrushLibActivePage


class SculptWheelBrushLibsUIList(bl_types.UIList):
    """Brush libraries; expand with the arrow to list and pick a starting wheel page."""

    bl_label = "Brush libraries"

    def draw_item(
        self,
        context: Context,
        layout: UILayout,
        data,
        item,
        icon,
        active_data,
        active_propname,
        index,
    ):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            if not item:
                return
            col = layout.column(align=True)
            row = col.row(align=True)
            tri = row.row(align=True)
            tri.ui_units_x = 1.25
            arr = "DOWNARROW_HLT" if item.wheel_pages_expanded else "RIGHTARROW"
            tri.prop(
                item,
                "wheel_pages_expanded",
                text="",
                toggle=True,
                icon=arr,
                emboss=False,
                icon_only=True,
            )
            ix = row.row(align=True)
            ix.alignment = "RIGHT"
            ix.ui_units_x = 2.0
            # ix.label(text=f"{index + 1}")
            row.label(text=blend_display_label(context, item.blend_key))

            if item.wheel_pages_expanded:
                pages = page_rows_for_blend_item(context, item)
                ap = int(get_active_page(context, item.blend_key))
                if not pages:
                    sub = col.row(align=True)
                    sub.label(text="No pages (reload libraries)", icon="ERROR")
                else:
                    pages_col = col.box().column(align=True)
                    pages_col.scale_y = 0.8
                    for pi, pname, cnt in pages:
                        pr = pages_col.row(align=True)
                        pr.alignment = 'LEFT'
                        ic = "RADIOBUT_ON" if pi == ap else "RECORD_OFF"
                        btn = pr.operator(
                            WheelSetBrushLibActivePage.bl_idname,
                            text=f"{pi}:  {pname}  ({cnt})",
                            icon=ic,
                            depress=(pi == ap),
                            emboss=False,
                        )
                        pr.active = pi == ap
                        btn.blend_key = item.blend_key
                        btn.page_index = pi
        elif self.layout_type in {"GRID"}:
            layout.alignment = "CENTER"
            layout.label(text="", icon_value=icon)


class SculptWheelCustomButtonSetsUIList(bl_types.UIList):
    """Named custom button sets (prefs); pick active set for editing buttons below."""

    bl_label = "Custom button sets"

    def draw_item(
        self,
        context: Context,
        layout: UILayout,
        data,
        item,
        icon,
        active_data,
        active_propname,
        index,
    ):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            if item:
                row = layout.row(align=True)
                ic = EVENT_SET_ICONS[index] if index < len(EVENT_SET_ICONS) else "DOT"
                row.label(text="", icon=ic)
                row.prop(item, "name", text="", emboss=False)
                row.label(text=f"({len(item.custom_buttons)})")
        elif self.layout_type in {"GRID"}:
            layout.alignment = "CENTER"
            layout.label(text="", icon_value=icon)
