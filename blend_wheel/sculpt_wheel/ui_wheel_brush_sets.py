"""UIList: brush library rows + custom button sets with expandable actions."""

from __future__ import annotations

from bpy.types import Context, UIList, UILayout

from ..core import bl_types

from .brush_lib_config import blend_display_label, get_active_page, page_rows_for_blend_item
from .data import MAX_CUSTOM_BUTTONS_PER_SET
from .op_custom_buttons import WheelMoveCustomButtonInSet, WheelRemoveCustomButton
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
                        pr.alignment = "LEFT"
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
    """One row per set (arrow + name + count). Expanded actions draw under the list in the panel."""

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
            if not item:
                return
            col = layout.column(align=True)
            row = col.row(align=True)
            tri = row.row(align=True)
            tri.ui_units_x = 1.25
            arr = "DOWNARROW_HLT" if item.custom_set_expanded else "RIGHTARROW"
            tri.prop(
                item,
                "custom_set_expanded",
                text="",
                toggle=True,
                icon=arr,
                emboss=False,
                icon_only=True,
            )
            row.prop(item, "name", text="", emboss=False)
            nb = len(item.custom_buttons)
            row.label(text=f"({nb}/{MAX_CUSTOM_BUTTONS_PER_SET})")

            if item.custom_set_expanded:
                if nb == 0:
                    sub = col.row(align=True)
                    sub.label(text="Empty set", icon="INFO")
                else:
                    for bi, cb in enumerate(item.custom_buttons):
                        br = col.row(align=True)
                        typ_ic = "CONSOLE" if cb.type == "OPERATOR" else "WINDOW"
                        br.label(text="", icon=typ_ic)
                        br.label(text=(cb.name or "Untitled").strip()[:42] or "Untitled")
                        ctr = br.row(align=True)
                        up_row = ctr.row(align=True)
                        up_row.enabled = bi > 0
                        o_up = up_row.operator(
                            WheelMoveCustomButtonInSet.bl_idname,
                            text="",
                            icon="TRIA_UP",
                        )
                        o_up.set_index = index
                        o_up.button_index = bi
                        o_up.direction = "UP"
                        dn_row = ctr.row(align=True)
                        dn_row.enabled = bi < nb - 1
                        o_dn = dn_row.operator(
                            WheelMoveCustomButtonInSet.bl_idname,
                            text="",
                            icon="TRIA_DOWN",
                        )
                        o_dn.set_index = index
                        o_dn.button_index = bi
                        o_dn.direction = "DOWN"
                        rm = ctr.operator(WheelRemoveCustomButton.bl_idname, text="", icon="X")
                        rm.index = bi
                        rm.set_index = index

        elif self.layout_type in {"GRID"}:
            layout.alignment = "CENTER"
            layout.label(text="", icon_value=icon)
