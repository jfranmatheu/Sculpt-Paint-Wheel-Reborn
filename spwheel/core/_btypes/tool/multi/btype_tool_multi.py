from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple, Type, TypeVar

from bpy.types import Context, UILayout, Operator, WorkSpaceTool
from bpy.utils import unregister_class, register_class

from ..btype_tool import BType_WorkSpaceTool, is_method_overridden
from .tool_multi import Tool
from ..tool_specs import ToolRaycastSpecs, ToolPreselectionSpecs
from ...ops.btype_op_tool_multi import BType_OpToolMulti
from ...gz.btype_gz_tool_multi import BType_GZ_ToolMulti, BType_GZG_ToolMulti
from ..tool_statusbar import reload_draw_statusbar
from ....gpu.globals import RuntimeDrawGlobals
from ..tool_preselection import PRESELECTION_HIGHLLIGHT_VALUES, PreselectionInfo
from ....debug import print_debug


T = TypeVar('T', bound='Tool')



class BType_WorkSpaceToolMulti(BType_WorkSpaceTool):
    """Base class for multi-tool tools, with a dedicated toolbar in top/bottom position and horizontal alignment. """
    bl_space_type: str = 'VIEW_3D' # default
    bl_region_type: str = 'WINDOW' # default
    bl_context_mode: str = 'OBJECT' # default

    # Not using the toolbar means that all 'Tool' added to this multi-tool will mix their keymaps together.
    # And of course, no toolbar widget as it won't be needed.
    # True -> a wstool consisting in multiple sub-tools user can switch-to via a custom toolbar.
    # False -> a wstool consisting in 1 tool with multiple tool actions, user will access these actions organically throught the defined keymaps.
    use_toolbar: bool = True

    _operator_instance: Operator = None  # Runtime.
    _operator_cls: Type[Operator] = None
    _gzg_cls: Type['BType_GZG_ToolMulti'] = None
    _gz_cls: Type['BType_GZ_ToolMulti'] = None

    tool_classes: List[Type[Tool]] = None
    tools: List[Tool] = None
    active_tool: Tool = None
    last_active_tool: Tool = None

    Tool = Tool
    tool_classes_by_id: Dict[str, Type[Tool]] = {}

    @classmethod
    def tag_register(cls, **kwargs: Dict[str, Any]) -> Type['BType_WorkSpaceToolMulti']:
        cls = super().tag_register(**kwargs)
        cls._setup_operator()
        cls._setup_gizmo()
        return cls

    @classmethod
    def on_register(cls):
        cls._ensure_tools()

        callback_options = set()
        extra_callbacks = {}

        if cls.use_toolbar:
            if cls.bl_context_mode == 'EDIT_MESH' and any([tool.preselection_specs is not None and tool.preselection_specs.geom_types != set() for tool in cls.tools]):
                extra_callbacks['DRAW_3D'] = cls._draw_preselection_3d
            if any([is_method_overridden(tool_cls, "draw_2d", Tool) for tool_cls in cls.tools]):
                callback_options.add('DRAW_2D')
            if any([is_method_overridden(tool_cls, "draw_3d", Tool) for tool_cls in cls.tools]):
                callback_options.add('DRAW_3D')
        else:
            if is_method_overridden(cls, "draw_2d", BType_WorkSpaceToolMulti):
                callback_options.add('DRAW_2D')
            if is_method_overridden(cls, "draw_3d", BType_WorkSpaceToolMulti):
                callback_options.add('DRAW_3D')

        super().on_register(
            use_auto_callbacks=False,
            callback_options=callback_options,
            extra_callbacks=extra_callbacks,
        )

        # Register operator.
        if cls._operator_cls is not None:
            register_class(cls._operator_cls)

        # Register gizmo.
        if cls.use_toolbar:
            if cls._gzg_cls is not None:
                register_class(cls._gzg_cls)
            if cls._gz_cls is not None:
                register_class(cls._gz_cls)

        # Setup keymaps for every Tool.
        cls._setup_keymaps()

    @classmethod
    def on_unregister(cls):
        super().on_unregister()

        # Clearing tool instances.
        if cls.tools:
            for tool in cls.tools:
                tool._instance = None

        # Unregister gizmo.
        if cls._gzg_cls is not None:
            cls._gzg_cls._instance = None
            unregister_class(cls._gzg_cls)
            cls._gzg_cls = None
        if cls._gz_cls is not None:
            cls._gz_cls._instance = None
            unregister_class(cls._gz_cls)
            cls._gz_cls = None

        # Unregister operator.
        if cls._operator_cls is not None:
            unregister_class(cls._operator_cls)
            cls._operator_cls = None

    @classmethod
    def _setup_operator(cls):
        # We need to create an operator in order to use the tool, as we need a way to handle the events.
        # we create an internal operator for the multi-tool, spcially designed to work together with the multi-tool system.
        # Upon registration, we will link every 'Tool' to this operator via this multi-tool keymaps.
        if cls._operator_cls is None:
            # As this type is internally created in the core module (no cls.__module__ override as well),
            # we should handle the registration/unregistration more manually, at least would be more safely.
            cls._operator_cls = type(f'ToolMulti_{cls.__name__}', (BType_OpToolMulti,), {
                'bl_label': f'{cls.bl_label} Operator',
                'bl_description': f'Operator for {cls.bl_label} multi-tool',
                '_btype_tool_cls': cls,
                'tool_cls': None,
            })
            cls._operator_cls.tag_register()
            print_debug(f"🔵 setup_operator: '{cls._operator_cls.bl_idname}' for multi-tool '{cls.bl_idname}'", indent=-1)

    @classmethod
    def _setup_gizmo(cls):
        if not cls.use_toolbar:
            return

        # We need to create a gizmo group and gizmo in order to use the toolbar feature of the multi-tool.
        # As these types are internally created in the core module (no cls.__module__ override as well),
        # we should handle the registration/unregistration more manually, at least would be more safely.
        if cls._gz_cls is None:
            cls._gz_cls = type(f'GZ_ToolMulti_{cls.__name__}', (BType_GZ_ToolMulti,), {
                '_btype_tool_cls': cls,
            })
            cls._gz_cls.tag_register()
            print_debug(f"🔵 setup_gizmo: '{cls._gz_cls.bl_idname}' for multi-tool '{cls.bl_idname}'", indent=-1)

        if cls._gzg_cls is None:
            cls._gzg_cls = type(f'GZG_ToolMulti_{cls.__name__}', (BType_GZG_ToolMulti,), {
                'bl_label': f'{cls.bl_label} Toolbar',
                'bl_space_type': cls.bl_space_type,
                '_btype_tool_cls': cls,
                '_gizmos_cls': (cls._gz_cls, )
            })
            cls._gzg_cls.tag_register()
            print_debug(f"🔵 setup_gizmo: '{cls._gzg_cls.bl_idname}' for multi-tool '{cls.bl_idname}'", indent=-1)

    @classmethod
    def _setup_keymaps(cls):
        # We load the keymaps from every 'Tool' class for the multi-tool.
        # Use the multi-tool operator for every keymap.
        # Set the tool_cls so that the operator knows which 'Tool' is the caller!
        if cls._operator_cls is None:
            return

        if cls.tool_classes is None:
            cls.tool_classes = []

        keymaps: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
        op_id = cls._operator_cls.bl_idname
        cls.tool_classes_by_id = {}

        for tool_cls in cls.tool_classes:
            tool_cls_id = f"{tool_cls.__module__}.{tool_cls.__qualname__}"
            cls.tool_classes_by_id[tool_cls_id] = tool_cls
            for km_event in tool_cls.keymaps:
                # keymap = (op.bl_idname, km_event, km_op_props)
                km_event: dict = km_event.copy()
                km_event.pop('label', None)
                keymaps.append((op_id, km_event, {"properties": [("tool_cls_id", tool_cls_id)]}))
        cls.bl_keymap = tuple(keymaps)
        print_debug(f"🔵 setup_keymaps: {len(keymaps)} keymaps for multi-tool '{cls.bl_idname}': {keymaps}", indent=-1)

    @classmethod
    def get_tool_class(cls, tool_cls_id: str) -> Type[Tool] | None:
        if not cls.tool_classes_by_id:
            cls._setup_keymaps()
        return cls.tool_classes_by_id.get(tool_cls_id, None)

    @classmethod
    def _ensure_tools(cls):
        if cls.tool_classes is None:
            cls.tool_classes = []
        tools = []
        for tool_cls in cls.tool_classes:
            tool = tool_cls.get_instance()
            tool._btype_tool_cls = cls
            tool._is_modal = not is_method_overridden(tool_cls, 'action', Tool)
            tools.append(tool)
        cls.tools = tools

    @classmethod
    def add_tool(cls, name: str, icon: Any, keymaps: Tuple[Tuple[str, Dict[str, Any], Dict[str, Any]], ...], raycast_specs: ToolRaycastSpecs | None = None, preselection_specs: ToolPreselectionSpecs | None = None) -> Type[T]:
        """Add the decorated tool as a subtool for the referenced Multi-Tool.

        Args:
            name (str): tool name
            icon (Any): tool icon
            keymaps (Tuple[Tuple[str, Dict[str, Any], Dict[str, Any]], ...]): tool keymaps
            options (Set[str], optional): tool options. Defaults to set().

        Returns:
            Type[T]: tool class
        """
        if cls.tool_classes is None:
            cls.tool_classes = []
        def decorator(decorated_cls: Type[T]) -> Type[T]:
            assert issubclass(decorated_cls, Tool), f'{decorated_cls.__name__} must be a subclass of {Tool} - {Tool.__module__}'
            decorated_cls.name = name
            decorated_cls.icon = icon
            decorated_cls.keymaps = keymaps
            decorated_cls.raycast_specs = raycast_specs
            decorated_cls.preselection_specs = preselection_specs
            cls.tool_classes.append(decorated_cls)
            print_debug(f"🔵 add_tool: '{decorated_cls.__name__}' to multi-tool '{cls.__name__}'", indent=-1)
            return decorated_cls
        return decorator

    @classmethod
    def draw_cursor(cls, context: Context, tool: WorkSpaceTool, xy: Optional[Tuple[int, int]] = None):
        super().draw_cursor(context, tool, xy)
        if not cls.use_toolbar:
            cls.draw_tool_cursor(context, cls.mouse_reg_pos)
            return
        if active_tool := cls.active_tool:
            active_tool.draw_cursor(context, cls.mouse_reg_pos)
            if active_tool.can_draw_preselection(context):
                PreselectionInfo.update(context, cls.mouse_reg_pos, active_tool.preselection_specs)

    @classmethod
    def _draw_preselection_3d(cls, context: Context):
        if not cls.use_toolbar:
            return
        if active_tool := cls.active_tool:
            if active_tool.can_draw_preselection(context):
                PreselectionInfo.draw_3d(context, specs=active_tool.preselection_specs, callback=active_tool.draw_previz)

    @classmethod
    def select_tool(cls, context: Context, tool: Tool):
        if not cls.use_toolbar:
            return
        if cls.active_tool is not None:
            cls.active_tool.on_tool_exit(context)
        cls.active_tool = tool
        cls.active_tool.on_tool_enter(context)

        context.region.tag_redraw()
        reload_draw_statusbar(context, cls.bl_idname)

    @classmethod
    def select_tool_at_index(cls, context: Context, index: int):
        if 0 <= index < len(cls.tools):
            cls.select_tool(context, cls.tools[index].get_instance())

    @classmethod
    def _on_tool_enter(cls, context: Context):
        print_debug(f"ℹ️  on_tool_enter: multi-tool '{cls.__name__}'")
        # Ensure tools are instantiated.
        cls._ensure_tools()

        if not cls.use_toolbar:
            cls.on_tool_enter(context)
            return

        if cls.active_tool is None and len(cls.tools) > 0:
            if cls.last_active_tool is not None:
                cls.active_tool = cls.last_active_tool
            else:
                cls.active_tool = cls.tools[0].get_instance()
            cls.active_tool.on_tool_enter(context)

    @classmethod
    def _on_tool_exit(cls, context: Context):
        print_debug(f"ℹ️  on_tool_exit: multi-tool '{cls.__name__}'")
        if not cls.use_toolbar:
            cls.on_tool_exit(context)
        elif cls.active_tool is not None:
            cls.active_tool.on_tool_exit(context)
            cls.last_active_tool = cls.active_tool
            cls.active_tool = None

    @classmethod
    def draw_statusbar(cls, context: Context, layout: UILayout):
        if not cls.use_toolbar:
            cls._draw_statusbar(context, layout)
        elif cls.active_tool is not None:
            cls.active_tool.draw_statusbar(context, layout)

    @classmethod
    def _draw_statusbar(cls, context: Context, layout: UILayout):
        if not cls.use_toolbar:
            for tool in cls.tools:
                tool.draw_statusbar(context, layout)
        elif cls.active_tool is not None:
            cls.active_tool.draw_statusbar(context, layout)

    @classmethod
    def _draw_2d(cls, context: Context):
        if not cls.use_toolbar:
            cls.draw_2d(context)
        elif cls.active_tool is not None:
            cls.active_tool.draw_2d(context)

    @classmethod
    def _draw_3d(cls, context: Context):
        if not cls.use_toolbar:
            cls.draw_3d(context)
        elif cls.active_tool is not None:
            cls.active_tool.draw_3d(context)
