from dataclasses import dataclass
from typing import Any, Callable, Literal, Optional, Set, Tuple, Type, Dict
from bpy.types import WorkSpaceTool, Context, UILayout
from mathutils import Matrix, Quaternion, Vector

from ...debug import print_debug
from ....core import GLOBALS
from .._base import BType
from .tool_switch import add_tool_exit_callback, add_tool_enter_callback
from .tool_statusbar import add_draw_statusbar_callback
from .tool_draw import add_draw_2d_callback, add_draw_3d_callback
from ...utils.class_utils import is_method_overridden
from .common import get_btype_tool_by_id
from ...gpu.globals import RuntimeDrawGlobals
from ..gz.btype_gz_tool_widget import BType_ToolWidget
from ...utils.view_utils import is_navigating


tool_id_to_btype_tool: Dict[str, Type['BType_WorkSpaceTool']] = {}


@dataclass
class RegionView3DInfo:
    view_location: Vector = Vector((0.0, 0.0, 0.0))
    view_rotation: Quaternion = Quaternion((0.0, 0.0, 0.0, 1.0))
    view_matrix: Matrix = Matrix.Identity(4)
    view_distance: float = 0.0
    window_matrix: Matrix = Matrix.Identity(4)

    @classmethod
    def from_context(cls, context: Context) -> 'RegionView3DInfo':
        """Create a RegionView3DInfo object from the current context.

        Args:
            context (Context): The Blender context.

        Returns:
            RegionView3DInfo: The created RegionView3DInfo object.
        """
        rv3d = context.region_data
        view_matrix = rv3d.view_matrix
        window_matrix = rv3d.window_matrix
        view_location = rv3d.view_location
        view_rotation = rv3d.view_rotation
        view_distance = rv3d.view_distance
        return cls(view_location, view_rotation, view_matrix, view_distance, window_matrix)

    def has_changed(self, context: Context) -> bool:
        """Compare and replace the view information if it has changed.

        Args:
            context (Context): context view information to compare with.

        Returns:
            bool: True if any of the view information has changed, False otherwise.
        """
        rv3d = context.region_data
        view_matrix = rv3d.view_matrix
        window_matrix = rv3d.window_matrix
        view_location = rv3d.view_location
        view_rotation = rv3d.view_rotation
        view_distance = rv3d.view_distance
        return self.view_location != view_location or self.view_rotation != view_rotation or self.view_matrix != view_matrix or self.view_distance != view_distance or self.window_matrix != window_matrix


class BType_WorkSpaceTool(BType, WorkSpaceTool):
    register_kwargs: Dict[str, Any] = {}
    group = None

    mouse_wnd_pos: Optional[Vector] = None
    mouse_reg_pos: Optional[Vector] = None
    
    nav_skip_drawing = False
    is_navigating = False

    @classmethod
    def tag_register(cls, **kwargs: Dict[str, Any]) -> Type['BType_WorkSpaceTool']:
        cls = super().tag_register(**kwargs)
        global tool_id_to_btype_tool
        tool_id_to_btype_tool[cls.bl_idname] = cls
        return cls

    @classmethod
    def get_wstool_base(cls) -> Type['BType_WorkSpaceTool'] | None:
        for base in cls.__bases__:
            if issubclass(base, BType_WorkSpaceTool):
                return base
        return None

    @classmethod
    def decorator(cls, after: Set[str], separator: bool = True, group: bool = True, keymaps: Optional[dict] = None) -> Type['BType_WorkSpaceTool']:
        cls.register_kwargs = {
            'after': after,
            'separator': separator,
            'group': group
        }
        if keymaps:
            if hasattr(cls, 'bl_keymap') and isinstance(cls.bl_keymap, dict):
                cls.bl_keymap.update(keymaps)
            else:
                cls.bl_keymap = keymaps
        return super().decorator(after, separator, group)

    @classmethod
    def on_register(cls, *, use_auto_callbacks: bool = True, callback_options: Set[Literal['TOOL_ENTER', 'TOOL_EXIT', 'DRAW_2D', 'DRAW_3D', 'DRAW_STATUSBAR']] = set(), extra_callbacks: Dict[Literal['TOOL_ENTER', 'TOOL_EXIT', 'DRAW_2D', 'DRAW_3D', 'DRAW_STATUSBAR'], Callable] = {}):
        wstool_base = cls.get_wstool_base()
        if not wstool_base:
            raise ValueError(f"WorkSpaceTool base class not found for {cls.__name__}")

        for callback_type, callback_func in extra_callbacks.items():
            if callback_type == 'TOOL_ENTER':
                add_tool_enter_callback(cls.bl_idname, callback_func)
            elif callback_type == 'TOOL_EXIT':
                add_tool_exit_callback(cls.bl_idname, callback_func)
            elif callback_type == 'DRAW_2D':
                add_draw_2d_callback(cls.bl_idname, callback_func)
            elif callback_type == 'DRAW_3D':
                add_draw_3d_callback(cls.bl_idname, callback_func)
            elif callback_type == 'DRAW_STATUSBAR':
                add_draw_statusbar_callback(cls.bl_idname, callback_func)

        if 'TOOL_ENTER' in callback_options or (use_auto_callbacks and is_method_overridden(cls, "on_tool_enter", wstool_base)):
            add_tool_enter_callback(cls.bl_idname, cls._on_tool_enter)
        if 'TOOL_EXIT' in callback_options or (use_auto_callbacks and is_method_overridden(cls, "on_tool_exit", wstool_base)):
            add_tool_exit_callback(cls.bl_idname, cls._on_tool_exit)
        if 'DRAW_STATUSBAR' in callback_options or (use_auto_callbacks and is_method_overridden(cls, "draw_statusbar", wstool_base)):
            add_draw_statusbar_callback(cls.bl_idname, cls._draw_statusbar)

        if 'DRAW_2D' in callback_options or (use_auto_callbacks and is_method_overridden(cls, "draw_2d", BType_WorkSpaceTool)):
            add_draw_2d_callback(cls.bl_idname, cls._draw_2d)
        if 'DRAW_3D' in callback_options or (use_auto_callbacks and is_method_overridden(cls, "draw_3d", BType_WorkSpaceTool)):
            add_draw_3d_callback(cls.bl_idname, cls._draw_3d)

        cls._setup_widget()

    @classmethod
    def _setup_widget(cls) -> None:
        if hasattr(cls, 'widget') and cls.widget:
            if issubclass(cls.widget, BType_ToolWidget):
                print_debug(f"setup_widget: {cls.widget.__name__}", indent=-1)
                cls.widget.register()
                cls._widget = cls.widget
                cls._widget._tool_idname = cls.bl_idname
                cls._widget._tool_cls = cls
                cls.bl_widget = cls.widget = cls._widget._gzg_cls.bl_idname

    @classmethod
    def widget_instance(cls) -> Optional[BType_ToolWidget]:
        return cls._widget.get()
        if hasattr(cls, 'bl_widget') and cls.bl_widget:
            if wg_instance := cls.bl_widget._instance:
                if wg_instance.gizmos and len(wg_instance.gizmos) > 0:
                    return cls.widget.get()
        return None

    @classmethod
    def _draw_2d(cls, context: Context):
        if cls.nav_skip_drawing and cls.is_navigating:
            return
        cls.draw_2d(context)

    @classmethod
    def _draw_3d(cls, context: Context):
        if cls.nav_skip_drawing and cls.is_navigating:
            return
        cls.draw_3d(context)

    @classmethod
    def draw_cursor(cls, context: Context, tool: WorkSpaceTool, xy: Optional[Tuple[int, int]] = None):
        """ Internal. DO NOT OVERRIDE. Please USE `draw_tool_cursor` instead. """
        assert xy is not None, "(draw_cursor) Cursor position is invalid."
        # print(f"Draw cursor at: {xy}, for tool: {tool.idname}")
        is_nav = is_navigating(context)
        if cls.is_navigating:
            if not is_nav:
                cls.on_navigate_exit(context)
                cls.is_navigating = False
        else:
            if is_nav:
                cls.on_navigate_enter(context)
                cls.is_navigating = True

        if is_nav:
            return

        cls.mouse_wnd_pos = Vector(xy)
        cls.mouse_reg_pos = cls.mouse_wnd_pos - Vector((context.area.x, context.area.y))
        cls.draw_tool_cursor(context, cls.mouse_wnd_pos)

    @classmethod
    def _on_tool_enter(cls, context: Context):
        cls.on_tool_enter(context)
        
    @classmethod
    def _on_tool_exit(cls, context: Context):
        cls.on_tool_exit(context)

    @classmethod
    def _draw_statusbar(cls, context: Context, layout: UILayout):
        cls.draw_statusbar(context, layout)

    # ---------------------------------------------------
    # Navigation callbacks
        
    @classmethod
    def on_navigate_enter(cls, context: Context):
        pass

    @classmethod
    def on_navigate_exit(cls, context: Context):
        pass

    # ---------------------------------------------------

    @classmethod
    def on_tool_enter(cls, context: Context):
        pass

    @classmethod
    def on_tool_exit(cls, context: Context):
        pass

    @classmethod
    def draw_statusbar(cls, context: Context, layout: UILayout):
        pass

    @classmethod
    def draw_2d(cls, context: Context):
        pass

    @classmethod
    def draw_3d(cls, context: Context):
        pass

    @classmethod
    def draw_tool_cursor(cls, context: Context, xy: Vector):
        pass

    @classmethod
    def draw_settings(cls, context: Context, layout: UILayout, tool):
        """ Internal. DO NOT OVERRIDE. Please USE `draw_header` instead. """
        ## print(f"Draw settings for tool: {tool.idname}")
        cls.draw_header(context, layout)

    @classmethod
    def draw_header(cls, context: Context, layout: UILayout):
        pass

    


def _new_tool_type(space_type: str, context_mode: str):
    return type(
        f"BType_WorkSpaceTool_{space_type}_{context_mode}",
        (BType_WorkSpaceTool,),
        {
            "bl_space_type": space_type,
            "bl_context_mode": context_mode,
        },
    )

class BType_WorkSpaceToolTypes:
    """Predefined tool types."""
    CUSTOM = BType_WorkSpaceTool
    # ---
    OBJECT = _new_tool_type("VIEW_3D", "OBJECT")
    EDIT_MESH = _new_tool_type("VIEW_3D", "EDIT_MESH")
    SCULPT_MESH = _new_tool_type("VIEW_3D", "SCULPT")
    TEXTURE_PAINT = _new_tool_type("VIEW_3D", "TEXTURE_PAINT")
    NODE_EDITOR = _new_tool_type("NODE_EDITOR", "")
    IMAGE_EDITOR = _new_tool_type("IMAGE_EDITOR", "")
    UV_EDITOR = _new_tool_type("IMAGE_EDITOR", "UV")
