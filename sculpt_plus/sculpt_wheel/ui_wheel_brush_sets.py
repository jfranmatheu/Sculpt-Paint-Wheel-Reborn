"""UIList for brush library configuration (JSON-backed, inline editing)."""

from __future__ import annotations

from bpy.types import Context, UIList, UILayout

from ..core import bl_types

from .data import EVENT_SET_ICONS


class SculptWheelBrushLibsUIList(bl_types.UIList):
    """Brush libraries with inline display name, color, options, and custom-set picker."""

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
            ph = (item.blend_name or item.blend_key or "").strip() or "Brush Library"
            row.prop(item, "display_name", text="", emboss=False, placeholder=ph)
            color_l = row.row(align=True)
            color_l.ui_units_x = 1
            color_l.prop(item, "wheel_color", text="")
            cp_icon = "RESTRICT_COLOR_ON" if item.show_color_picker else "RESTRICT_COLOR_OFF"
            row.prop(
                item,
                "show_color_picker",
                text="",
                toggle=True,
                icon=cp_icon,
            )
            row.prop(item, "custom_button_set", text="", icon_only=True)
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
