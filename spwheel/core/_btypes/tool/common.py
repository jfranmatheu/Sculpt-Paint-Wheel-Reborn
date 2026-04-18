from typing import Optional
from bpy.types import Context, UILayout
from bl_ui.space_toolsystem_common import ToolSelectPanelHelper

from ...globals import GLOBALS


def is_self_tool(tool_id: str) -> bool:
    return tool_id.split('.')[0] == GLOBALS.ADDON.ID


def get_btype_tool_by_id(tool_id: str):
    from .btype_tool import tool_id_to_btype_tool
    return tool_id_to_btype_tool.get(tool_id, None)


def get_active_tool(context: Context, space_type: Optional[str] = None):
    if space_type is None:
        space_type = context.space_data.type
    tool_active = ToolSelectPanelHelper._tool_active_from_context(context, space_type)
    return tool_active

def get_active_tool_item(context: Context, space_type: Optional[str] = None):
    if space_type is None:
        space_type = context.space_data.type
    tool_cls = ToolSelectPanelHelper._tool_class_from_space_type(space_type)
    tool_active = ToolSelectPanelHelper._tool_active_from_context(context, space_type)
    item, index = tool_cls._tool_get_by_id(context, getattr(tool_active, "idname", None))
    return item

def get_active_tool_index(context: Context, space_type: Optional[str] = None):
    if space_type is None:
        space_type = context.space_data.type
    tool_cls = ToolSelectPanelHelper._tool_class_from_space_type(space_type)
    tool_active = ToolSelectPanelHelper._tool_active_from_context(context, space_type)
    item, index = tool_cls._tool_get_by_id(context, getattr(tool_active, "idname", None))
    return index


def parse_km_event_to_icons(km: dict) -> list:
    icons = []
    type: str = km['type']
    value: str = km['value']
    alt = km.get('alt', False) or type in {'LEFT_ALT', 'RIGHT_ALT'}
    shift = km.get('shift', False) or type in {'LEFT_SHIFT', 'RIGHT_SHIFT'}
    ctrl = km.get('ctrl', False) or type in {'LEFT_CTRL', 'RIGHT_CTRL'}

    if alt:
        icons.append('EVENT_ALT')
        icons.append(None) # separator
    if shift:
        icons.append('EVENT_SHIFT')
    if ctrl:
        icons.append('EVENT_CTRL')
        icons.append(None) # separator

    if type in {'LEFTMOUSE', 'RIGHTMOUSE', 'MIDDLEMOUSE'}:
        id = f"MOUSE_{type[0]}MB"
        if value == 'DOUBLE_CLICK':
            id += '_2X'
        elif value == 'CLICK_DRAG':
            id += '_DRAG'
        icons.append(id)
    elif type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
        icons.append('MOUSE_MMB_SCROLL')
    elif type.startswith('EVENT_'):
        icons.append(type)
    return icons


def draw_km_event(layout: UILayout, km_event: dict):
    icons = parse_km_event_to_icons(km_event)
    if len(icons) == 0:
        return
    row = layout.row(align=True)
    for icon in icons:
        if icon is None:
            row.separator(factor=0.5)
            continue
        row.label(text="", icon=icon)
    row.label(text=km_event.get('label', ''))
