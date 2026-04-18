from typing import TYPE_CHECKING, Set

from bpy.types import Context, Event
from bpy.props import StringProperty

from .btype_op_base import BType_Operator
from ...utils.op_return import OpReturn
from ...utils.class_utils import is_method_overridden
from ...utils.raycast_utils import raycast_scene, raycast_object, RaycastInfo, BVHTreeRaycaster
from ...utils.mouse_utils import ModalMouse


if TYPE_CHECKING:
    from ..tool.multi.btype_tool_multi import Tool
    from ..tool.multi.btype_tool_multi import BType_WorkSpaceToolMulti
else:
    BType_WorkSpaceToolMulti = None
    Tool = None


class BType_OpToolMulti(BType_Operator):
    _btype_tool_cls: 'BType_WorkSpaceToolMulti' = None
    tool_cls: Tool = None
    use_timer: bool = False
    timer_step: float = 0.1
    _timer = None
    raycast_info: RaycastInfo | None = None
    modal_mouse: ModalMouse | None = None

    tool_cls_id: StringProperty(
        name="Tool Class ID",
        description="ID of the Tool class to use.",
        default=""
    )

    @classmethod
    def poll(cls, context: Context) -> bool:
        if cls._btype_tool_cls is None:
            return False
        if cls._btype_tool_cls.use_toolbar and cls._btype_tool_cls.active_tool is None:
            return False
        # Unfortunately we can't know which multi-tool's 'Tool' is the single operator
        # trying to run a keymap for ('tool_cls_id'). So we allow all of them to run and block the 
        # event if the tool is found to not be the 'active_tool'.
        return True

    @property
    def tool(self) -> Tool:
        if self.tool_cls is None:
            self.tool_cls = self._btype_tool_cls.get_tool_class(self.tool_cls_id)
        return self.tool_cls.get_instance()

    def update_raycast(self, context: Context, event: Event, initial: bool = False) -> RaycastInfo | None:
        raycast_info = None
        match self.tool.raycast_specs.mode:
            case "SCENE":
                raycast_info = raycast_scene(context, event)
            case "OBJECT":
                raycast_info = raycast_object(context, event)
            case "BVHTREE":
                if not hasattr(self, 'bvhtree_raycaster'):
                    self.bvhtree_raycaster = BVHTreeRaycaster(context)
                raycast_info = self.bvhtree_raycaster.do_raycast(context, event)

        raycast_info = raycast_info if raycast_info is not None and raycast_info.hit else None
        self.raycast_info = raycast_info
        return raycast_info
    
    def update_modal_mouse(self, context: Context, event: Event) -> ModalMouse:
        if self.modal_mouse is None:
            self.modal_mouse = ModalMouse(context, event, delta_threshold=1.0, record_init=True)
        self.modal_mouse.update(context, event)
        return self.modal_mouse

    def invoke(self, context: Context, event: Event) -> Set[str]:
        if self.tool_cls_id == "":
            return OpReturn.CANCEL
        if self._btype_tool_cls.use_toolbar and self.tool != self._btype_tool_cls.active_tool:
            # NOTE: To avoid this at polling level we block the event 
            # if the tool is not active, as a HACK for now. This is not the ideal, but the
            # solution to the root issue would be to create and link each
            # multi-tool 'Tool' to a different operator type.
            # (currently we use only one and pass the 'Tool' identifier via operator's 'tool_cls_id')
            return OpReturn.PASS

        if not self.tool.poll(context, event):
            return OpReturn.CANCEL

        kwargs = {}
        if self.tool.use_raycast:
            raycast_info = self.update_raycast(context, event, initial=True)
            if raycast_info is None and self.tool.raycast_specs.block_tool_init:
                return OpReturn.CANCEL
            kwargs['raycast_info'] = raycast_info

        if not self.tool._is_modal:
            self.tool.action(context, event, **kwargs)
            return OpReturn.FINISH

        if not context.window_manager.modal_handler_add(self):
            return OpReturn.CANCEL

        self.modal_begin(context, event, **kwargs)
        return OpReturn.RUN

    def modal_begin(self, context: Context, event: Event, **kwargs):
        self.tool_cls._operator_instance = self
        self.use_modal_step_move = is_method_overridden(type(self.tool), 'modal_step_move', Tool)
        self.use_timer = is_method_overridden(type(self.tool), 'modal_timer', Tool)
        if self.use_timer:
            self._timer = context.window_manager.event_timer_add(self.timer_step, window=context.window)
        self.tool.in_modal = True
        self.tool.modal_begin(context, event, modal_mouse=self.update_modal_mouse(context, event), **kwargs)

    def modal(self, context: Context, event: Event) -> Set[str]:
        # Handle timer events.
        if self.use_timer and event.type == 'TIMER':
            self.tool.modal_step_timer(context, event)
            return OpReturn.RUN

        # Handle mousemove events.
        if self.use_modal_step_move and event.type in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'}:
            # Update modal mouse and raycast info.
            kwargs = {
                'modal_mouse': self.update_modal_mouse(context, event)
            }
            if self.tool.use_raycast and self.tool.raycast_specs.use_in_modal:
                raycast_info = self.update_raycast(context, event, initial=False)
                if raycast_info is None and self.tool.raycast_specs.block_tool_modal:
                    return OpReturn.CANCEL
                kwargs['raycast_info'] = raycast_info

            if self.tool.modal_step_move(context, event, **kwargs):
                return OpReturn.RUN
            return OpReturn.PASS

        res = self.tool.modal_step(context, event)
        if res is None:
            return OpReturn.FINISH
        if res == OpReturn.CANCEL:
            self.modal_end(context, event, cancel=True)
            return OpReturn.CANCEL
        if res == OpReturn.FINISH:
            self.modal_end(context, event, cancel=False)
            return OpReturn.FINISH
        return res

    def modal_end(self, context: Context, event: Event, cancel: bool):
        if self.use_timer and self._timer:
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None
        self.tool.modal_end(context, event, cancel=cancel)
        self.tool.in_modal = False
        self.tool_cls._operator_instance = None
        self.modal_mouse = None
        self.raycast_info = None
        if hasattr(self, 'bvhtree_raycaster'):
            del self.bvhtree_raycaster
