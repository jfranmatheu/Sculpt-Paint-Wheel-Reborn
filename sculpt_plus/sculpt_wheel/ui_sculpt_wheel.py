"""N-panel UI: brush sets list, previews, add active brush."""

from __future__ import annotations

import bpy
from bpy.types import Context, Panel, UILayout

from ..core import bl_types

from .data import SculptWheelData, WheelToolset
from .brush_assets import find_brush_for_slot



class SculptWheelBrushSlotsUIList(bl_types.UIList):
    """List rows for brushes in the active toolset."""

    def draw_item(
        self,
        context: Context | None,
        layout: UILayout,
        data,
        item,
        icon,
        active_data,
        active_propname,
        index: int = 0,
    ) -> None:
        if self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
        if not item:
            layout.label(text="", icon='BLANK1')
            return
        brush = find_brush_for_slot(item)
        if brush is not None:
            layout.label(text=item.display_name or brush.name, icon_value=layout.icon(brush))
        else:
            layout.label(text=item.display_name or "Missing brush", icon='BRUSH_DATA')


class SculptWheelSidebarPanel(bl_types.PanelPresets.VIEW_3D_SIDEBAR):
    """Sculpt mode sidebar: manage wheel brush sets (mirrors legacy Sculpt Wheel toolsets UI)."""
    bl_label = "Sculpt Wheel"

    @classmethod
    def poll(cls, context: Context) -> bool:
        return context.mode == 'SCULPT'

    @classmethod
    def draw_ui(cls, context: Context, layout: UILayout) -> None:
        data = SculptWheelData.get(context)
        data.ensure_default_toolset(context)

        if len(data.toolsets) == 0:
            layout.label(text="No brush sets")
            return

        # --- Toolset selection (radio-style) ---
        box = layout.box()
        box.label(text="Brush Sets", icon='OUTLINER')
        col = box.column(align=True)
        for i, ts in enumerate(data.toolsets):
            row = col.row(align=True)
            icon = 'RADIOBUT_ON' if i == data.active_toolset_index else 'RADIOBUT_OFF'
            op = row.operator(
                "sculpt_plus.wheelselecttoolset",
                text=ts.name or f"Set {i + 1}",
                icon=icon,
                emboss=False,
            )
            op.index = i

        row = col.row(align=True)
        row.operator("sculpt_plus.wheeladdtoolset", text="", icon='ADD')
        row.operator("sculpt_plus.wheelremovetoolset", text="", icon='TRASH')

        ts: WheelToolset | None = data.active_toolset
        if ts is None:
            return

        name_row = layout.row(align=True)
        name_row.prop(ts, "name", text="Name")

        # --- Brush slots (preview names + brush icons) ---
        list_box = layout.box()
        list_box.label(text="Brushes in set", icon='BRUSH_DATA')
        SculptWheelBrushSlotsUIList.draw_list(list_box, ts, "slots", "active_slot_index")

        add_row = list_box.row(align=True)
        add_row.operator("sculpt_plus.wheeladdactivebrush", icon='ADD')

        if ts.active_slot_index >= 0 and ts.active_slot_index < len(ts.slots):
            rm = add_row.operator("sculpt_plus.wheelremovebrushslot", text="", icon='X')
            rm.index = ts.active_slot_index
