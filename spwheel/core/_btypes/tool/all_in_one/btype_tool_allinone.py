from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type

from bpy.types import Context, Event, UILayout, WorkSpaceTool
from bpy.utils import register_class, unregister_class
from mathutils import Vector

from ....utils.op_return import OpReturn
from ..btype_tool import BType_WorkSpaceTool, add_draw_2d_callback, add_draw_3d_callback, add_tool_enter_callback, add_tool_exit_callback, add_draw_statusbar_callback, is_method_overridden
from ...data.btype_pg import BType_PGRoot
from ...ops.btype_op_modal import BType_OpModal
from ...ops.btype_op_action import BType_OpAction
from ..tool_preselection import PreselectionInfo
from ..tool_specs import ToolPreselectionSpecs, ToolRaycastSpecs
from ....utils.mouse_utils import ModalMouse
from ....utils.raycast_utils import RaycastInfo, BVHTreeRaycastInfo
from ....debug import print_debug
from ....utils.view_utils import is_navigating


keymaps_example = "keymaps = [{'type': 'LEFTMOUSE', 'value': 'PRESS', 'alt': True}, {'type': 'RIGHTMOUSE', 'value': 'PRESS', 'ctrl': True, 'shift': True}]"


class BType_WorkSpaceTool_AllInOne(BType_WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'EDIT_MESH'

    _operator_cls: Type[BType_OpModal | BType_OpAction] = None
    operator_instance: BType_OpModal | BType_OpAction = None

    preselection_specs: Optional[ToolPreselectionSpecs] = None
    raycast_specs: Optional[ToolRaycastSpecs] = None
    tool_settings: Optional[BType_PGRoot] = None

    keymaps: Optional[List[Dict[str, Any]]] = None
    _is_modal: bool = True

    # Runtime attributes.
    in_modal: bool = False

    # -----------------------------------------------------------------------------------
    # -- Registration and Setup --
    # -----------------------------------------------------------------------------------

    @classmethod
    def decorator(cls, after: Set[str], separator: bool = True, group: bool = True, keymaps: Optional[List[Dict[str, Any]]] = None, raycast_specs: Optional[ToolRaycastSpecs] = None, preselection_specs: Optional[ToolPreselectionSpecs] = None) -> Type['BType_WorkSpaceTool']:
        cls.keymaps = keymaps
        cls.raycast_specs = raycast_specs
        cls.preselection_specs = preselection_specs
        return super().decorator(after, separator, group, keymaps)

    @classmethod
    def tag_register(cls, **kwargs: Dict[str, Any]) -> Type['BType_WorkSpaceTool_AllInOne']:
        if cls.keymaps is None or len(cls.keymaps) == 0:
            raise ValueError(f"Keymaps need to be defined in {cls.__name__}. Please implement a custom 'keymaps' property of type `List[Dict[str, Any]]`,\n\t- Example: `{keymaps_example}`")
        cls: Type[BType_WorkSpaceTool_AllInOne] = super().tag_register(**kwargs)
        _MODAL_METHODS = ('modal_begin', 'modal_end', 'modal_step', 'modal_step_move', 'modal_step_timer')
        has_modal = any(is_method_overridden(cls, m, BType_WorkSpaceTool_AllInOne) for m in _MODAL_METHODS)
        has_action = is_method_overridden(cls, 'action', BType_WorkSpaceTool_AllInOne)
        cls._is_modal = has_modal or not has_action
        cls._setup_operator()
        cls._setup_keymaps()
        return cls

    @classmethod
    def _setup_operator(cls) -> None:
        if cls._operator_cls is not None:
            return

        # Only override operator methods which are overridden in its Tool representation.
        methods_to_override = (
            ('action', 'action', lambda self, context, event: cls.action(self, context, event)),
            ('draw_2d', 'modal_draw_2d', lambda self, context: cls.modal_draw_2d(self, context)),
            ('draw_3d_post', 'modal_draw_3d', lambda self, context: cls.modal_draw_3d(self, context)),
            ('modal_begin', '_modal_begin', lambda self, context, event, modal_mouse, raycast_info=None: cls._modal_begin(self, context, event, modal_mouse, raycast_info=raycast_info)),
            ('modal_step', 'modal_step', lambda self, context, event: cls.modal_step(self, context, event)),
            ('modal_step_move', 'modal_step_move', lambda self, context, event, modal_mouse, raycast_info=None: cls.modal_step_move(self, context, event, modal_mouse, raycast_info=raycast_info)),
            ('modal_step_timer', 'modal_step_timer', lambda self, context, event: cls.modal_step_timer(self, context, event)),
            ('modal_end', '_modal_end', lambda self, context, cancel, modal_mouse: cls._modal_end(self, context, cancel, modal_mouse)),
            ('poll', 'poll', classmethod(lambda op_cls, context: cls.poll(context))),
        )
        kwargs = {}
        for (op_method_name, tool_method_name, override_callback) in methods_to_override:
            overridable_tool_method_name = tool_method_name[1:] if tool_method_name.startswith('_') else tool_method_name
            if is_method_overridden(cls, overridable_tool_method_name, BType_WorkSpaceTool_AllInOne):
                kwargs[op_method_name] = override_callback

        # As this type is internally created in the core module (no cls.__module__ override as well),
        # we should handle the registration/unregistration more manually, at least would be more safely.
        op_base_cls = BType_OpModal if cls._is_modal else BType_OpAction
        cls._operator_cls = type(cls.__name__, (op_base_cls,), {
            'bl_label': f'{cls.bl_label} Operator',
            'bl_description': f'Operator for {cls.bl_label} All-in-1 Tool',
            'raycast_specs': cls.raycast_specs,
            'bl_context_mode': cls.bl_context_mode,
            **kwargs,
        })

        cls._operator_cls.tag_register()
        print_debug(f"- setup_operator: '{cls._operator_cls.bl_idname}' for all-in-1 tool '{cls.bl_idname}'", indent=-1)

    @classmethod
    def _setup_keymaps(cls):
        # We load the keymaps from every 'Tool' class for the multi-tool.
        # Use the multi-tool operator for every keymap.
        # Set the tool_cls so that the operator knows which 'Tool' is the caller!
        if cls._operator_cls is None:
            return
        keymaps: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
        non_modal_events: set[tuple] = set()
        op_id = cls._operator_cls.bl_idname
        for km_event in cls.keymaps:
            km_event = dict(km_event)
            is_km_modal = km_event.pop('modal', True)
            if not is_km_modal:
                non_modal_events.add((
                    km_event.get('type'),
                    km_event.get('value'),
                    km_event.get('ctrl', False),
                    km_event.get('shift', False),
                    km_event.get('alt', False),
                ))
            keymaps.append((op_id, km_event, {}))
        if non_modal_events:
            cls._operator_cls._non_modal_events = frozenset(non_modal_events)
        cls.bl_keymap = tuple(keymaps)
        print_debug(f"- setup_keymaps: ({len(keymaps)}) {keymaps}", indent=-1)

    @classmethod
    def on_register(cls):
        callback_options = {'TOOL_ENTER', 'TOOL_EXIT', 'DRAW_STATUSBAR'}
        if (cls.preselection_specs is not None and cls.preselection_specs.geom_types != set()) or is_method_overridden(cls, 'draw_3d', BType_WorkSpaceTool_AllInOne):
            callback_options.add('DRAW_3D')
        if is_method_overridden(cls, 'draw_2d', BType_WorkSpaceTool_AllInOne):
            callback_options.add('DRAW_2D')
        super().on_register(use_auto_callbacks=False, callback_options=callback_options)

        # Register operator.
        if cls._operator_cls is not None:
            register_class(cls._operator_cls)

    @classmethod
    def on_unregister(cls):
        super().on_unregister()

        # Unregister operator.
        if cls._operator_cls is not None:
            unregister_class(cls._operator_cls)
            cls._operator_cls = None

    @classmethod
    def draw_statusbar(cls, context: Context, layout: UILayout):
        return super().draw_statusbar(context, layout)

    @classmethod
    def draw_settings(cls, context: Context, layout: UILayout, tool):
        if cls.tool_settings is not None:
            cls.tool_settings._draw(context, layout)


    # -----------------------------------------------------------------------------------
    # -- Tool Previz and Cursor drawing --
    # -----------------------------------------------------------------------------------

    @classmethod
    def can_draw_preselection(cls, context: Context) -> bool:
        if cls.is_navigating:
            return False
        if context.active_object is None or context.active_object.type != 'MESH':
            return False
        if cls.preselection_specs is None or cls.preselection_specs.geom_types == set():
            return False
        if cls.operator_instance is not None and not cls.preselection_specs.use_in_modal:
            return False
        return True

    @classmethod
    def get_preselection_info(cls) -> Optional[PreselectionInfo]:
        if cls.preselection_specs is None:
            return None
        return PreselectionInfo.get()

    @classmethod
    def _draw_3d(cls, context: Context):
        if cls.can_draw_preselection(context):
            PreselectionInfo.draw_3d(context, specs=cls.preselection_specs, callback=cls.draw_previz)
        super()._draw_3d(context)

    @classmethod
    def draw_cursor(cls, context: Context, tool: WorkSpaceTool, xy: Optional[Tuple[int, int]] = None):
        super().draw_cursor(context, tool, xy)
        if cls.can_draw_preselection(context):
            mouse_reg_pos = Vector(xy) - Vector((context.area.x, context.area.y))
            PreselectionInfo.update(context, mouse_reg_pos, cls.preselection_specs, callback=cls.on_preselection_update)


    # -------------------------------------
    # -- Preselection Update and Drawing callbacks --

    @classmethod
    def on_preselection_update(cls, context: Context, mouse: Vector, info: PreselectionInfo):
        """Handle the update of the preselection.

        Args:
            context (Context): The Blender context.
            info (PreselectionInfo): The preselection information.
        """
        pass

    @classmethod
    def draw_previz(cls, context: Context, info: PreselectionInfo):
        """Draw the preview of the tool. (3D)

        Args:
            context (Context): The Blender context.
            info (PreselectionInfo): The preselection information.
        """
        pass


    # -----------------------------------------------------------------------------------
    # -- Modal Operator --
    # -----------------------------------------------------------------------------------

    @classmethod
    def poll(cls, context: Context) -> bool:
        return True

    @classmethod
    def _modal_begin(cls, op, context: Context, event: Event, modal_mouse: ModalMouse, *, raycast_info: RaycastInfo | BVHTreeRaycastInfo | None = None) -> None:
        cls.operator_instance = op
        cls.in_modal = True
        cls.modal_begin(op, context, event, modal_mouse, raycast_info=raycast_info)

    @classmethod
    def _modal_end(cls, op, context: Context, cancel: bool, modal_mouse: ModalMouse) -> None:
        cls.modal_end(op, context, cancel, modal_mouse)
        cls.operator_instance = None
        cls.in_modal = False
        PreselectionInfo.get().clear()
        PreselectionInfo.free()

    @classmethod
    def action(cls, op, context: Context, event: Event) -> bool | str:
        """Handle the action of the tool. (for non-modal tools)

        Args:
            op (BType_OpModal): The operator instance.
            context (Context): The Blender context.
            event (Event): The Blender event.

        Returns:
            bool | str: True if the action was successful, False otherwise.
        """
        return False

    @classmethod
    def modal_draw_2d(cls, op, context: Context) -> None:
        """Handle 2D drawing.

        Args:
            op (BType_OpModal): The operator instance.
            context (Context): The Blender context.
        """
        pass

    @classmethod
    def modal_draw_3d(cls, op, context: Context) -> None:
        """Handle 3D post-view drawing.

        Args:
            op (BType_OpModal): The operator instance.
            context (Context): The Blender context.
        """
        pass

    @classmethod
    def modal_begin(cls, op, context: Context, event: Event, modal_mouse: ModalMouse, *, raycast_info: RaycastInfo | BVHTreeRaycastInfo | None = None) -> None:
        """Handle modal begin events.

        Args:
            op (BType_OpModal): The operator instance.
            context (Context): The Blender context.
            event (Event): The Blender event.
            modal_mouse (ModalMouse): The modal mouse.
            raycast_info (RaycastInfo | BVHTreeRaycastInfo | None, optional): The raycast info. Defaults to None.
        """
        pass

    @classmethod
    def modal_step(cls, op, context: Context, event: Event) -> Set[str] | Callable[[Context, Event], bool]:
        """Handle modal update events.

        Args:
            op (BType_OpModal): The operator instance.
            context (Context): The Blender context.
            event (Event): The Blender event.

        Returns:
            Set[str] | Callable[[Context, Event], bool]: The result of the modal step.
        """
        return OpReturn.FINISH

    @classmethod
    def modal_step_move(cls, op, context: Context, event: Event, modal_mouse: ModalMouse, *, raycast_info: RaycastInfo | BVHTreeRaycastInfo | None = None) -> bool:
        """Handle mouse move events.

        Args:
            op (BType_OpModal): The operator instance.
            context (Context): The Blender context.
            event (Event): The Blender event.
            modal_mouse (ModalMouse): The modal mouse.
            raycast_info (RaycastInfo | BVHTreeRaycastInfo | None, optional): The raycast info. Defaults to None.

        Returns:
            bool: True if the event was handled, False otherwise.
        """
        return False

    @classmethod
    def modal_step_timer(cls, op, context: Context, event: Event) -> None:
        """Handle timer events.

        Args:
            op (BType_OpModal): The operator instance.
            context (Context): The Blender context.
            event (Event): The Blender event.
        """
        pass

    @classmethod
    def modal_end(cls, op, context: Context, cancel: bool, modal_mouse: ModalMouse) -> None:
        """Handle modal end finish and cancel events.

        Args:
            op (BType_OpModal): The operator instance.
            context (Context): The Blender context.
            cancel (bool): True if the modal was cancelled, False otherwise.
            modal_mouse (ModalMouse): The modal mouse.
        """
        pass
