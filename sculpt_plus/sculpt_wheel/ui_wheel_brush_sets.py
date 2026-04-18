"""UIList: brush library rows (read-only labels from index)."""

from __future__ import annotations

from bpy.types import Context, UIList, UILayout

from ..core import bl_types

from .brush_lib_config import blend_display_label
from .data import EVENT_SET_ICONS


class SculptWheelBrushLibsUIList(bl_types.UIList):
    """Brush libraries discovered from asset data (order fixed by index)."""

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
            row = layout.row(align=True)
            ix = row.row(align=True)
            ix.alignment = "RIGHT"
            ix.ui_units_x = 2.0
            ix.label(text=f"{index + 1}")
            row.label(text=blend_display_label(context, item.blend_key))
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
