from typing import Optional
from bpy.types import Panel, UILayout, Context

from ...globals import GLOBALS

from .btype_ui_base import BType_UIExtra


class BType_Panel(BType_UIExtra, Panel):
    bl_icon: Optional[str | int] = None
    bl_space_type: str = GLOBALS.ADDON.DEFAULT_PANELS_SPACE_TYPE
    bl_region_type: str = GLOBALS.ADDON.DEFAULT_PANELS_REGION_TYPE
    bl_context: str = GLOBALS.ADDON.DEFAULT_PANELS_CONTEXT
    bl_category: str = GLOBALS.ADDON.DEFAULT_PANELS_CATEGORY
    is_popover: bool = False

    @classmethod
    def draw_as_collapsable_panel(cls, layout: UILayout, *, title: Optional[str] = None, icon: Optional[str | int] = None, default_closed: bool = False):
        icon = icon or cls.bl_icon
        header, content = layout.panel(cls.bl_idname, default_closed=default_closed)
        header.label(text=title or cls.bl_label, icon=icon if isinstance(icon, str) else 'NONE', icon_value=icon if isinstance(icon, int) else 0)
        return content

    @classmethod
    def draw_as_popover_panel(cls, layout: UILayout, *, title: Optional[str] = None, icon: Optional[str | int] = None):
        icon = icon or cls.bl_icon
        layout.popover(cls.bl_idname, title=title or cls.bl_label, icon=icon if isinstance(icon, str) else 'NONE', icon_value=icon if isinstance(icon, int) else 0)

    @classmethod
    def invoke_popover(cls, context: Context, ui_units_x: Optional[int] = 0, keymaps = None, from_active_button: bool = False):
        context.window_manager.popover(lambda menu, context: cls.draw_ui(context, menu.layout), ui_units_x=ui_units_x, keymaps=keymaps, from_active_button=from_active_button)


def _new_panel_type(space_type: str, region_type: str, **kwargs: dict) -> BType_Panel:
    return type(f"BType_Panel_{space_type}_{region_type}", (BType_Panel,), {
        "bl_space_type": space_type,
        "bl_region_type": region_type,
        **kwargs
    })


class BType_PanelTypes:
    """Predefined panel types."""
    CUSTOM = BType_Panel
    # ---
    POPOVER = _new_panel_type('VIEW_3D', 'HEADER', bl_options={'INSTANCED'}, is_popover=True)

    VIEW_3D_SIDEBAR = _new_panel_type('VIEW_3D', 'UI')
    VIEW_3D_TOOLBAR = _new_panel_type('VIEW_3D', 'TOOLS')

    PROPERTIES = _new_panel_type('PROPERTIES', 'WINDOW')

    NODE_EDITOR_SIDEBAR = _new_panel_type('NODE_EDITOR', 'UI')
    IMAGE_EDITOR_SIDEBAR = _new_panel_type('IMAGE_EDITOR', 'UI')

    GRAPH_EDITOR_SIDEBAR = _new_panel_type('GRAPH_EDITOR', 'UI')
    DOPESHEEP_EDITOR_SIDEBAR = _new_panel_type('DOPESHEET_EDITOR', 'UI')
