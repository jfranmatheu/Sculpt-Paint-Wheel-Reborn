from typing import Any, Callable, Dict, Set, Type
from bpy.types import Context, Event

from .btype_op_base import BType_Operator
from ...utils.op_return import OpReturn
from ...utils.class_utils import is_method_overridden
from ...utils.callback_utils import CallbackList
from ...utils.mouse_utils import ModalMouse
from ...utils.raycast_utils import RaycastInfo, raycast_object, raycast_scene, BVHTreeRaycaster, BVHTreeRaycastInfo


class BType_OpModal(BType_Operator):
    _is_modal: bool = True
    _submodal: Callable[[Context, Event], bool] | None = None
    _draw_handler_types: Set[str] = set()
    _remove_draw_handlers: CallbackList
    _non_modal_events: frozenset = frozenset()

    use_timer: bool = False
    timer_interval: float = 0.1
    running: bool = False

    raycast_specs = None
    raycast_info: RaycastInfo | BVHTreeRaycastInfo | None = None
    modal_mouse: ModalMouse | None = None

    cancel_on: Set[str] = {"ESC", "RIGHTMOUSE"}
    confirm_on: Set[str] = {"RET", "NUMPAD_ENTER"}
    
    # Required context mode for modal execution (e.g. 'EDIT_MESH')
    bl_context_mode: str | None = None

    @classmethod
    def tag_register(cls, **kwargs: Dict[str, Any]) -> Type['BType_OpModal']:
        if is_method_overridden(cls, "modal_step_timer", BType_OpModal):
            cls.use_timer = True
        if is_method_overridden(cls, "draw_2d", BType_OpModal):
            cls._draw_handler_types.add("POST_PIXEL")
        if is_method_overridden(cls, "draw_3d_pre", BType_OpModal):
            cls._draw_handler_types.add("PRE_VIEW")
        if is_method_overridden(cls, "draw_3d_post", BType_OpModal):
            cls._draw_handler_types.add("POST_VIEW")
        return super().tag_register(**kwargs)

    @property
    def use_raycast(self) -> bool:
        return self.raycast_specs is not None

    def update_raycast(self, context: Context, event: Event, initial: bool = False) -> RaycastInfo | BVHTreeRaycastInfo | None:
        raycast_info = None
        match self.raycast_specs.mode:
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

    def get_update_modal_args(self, context: Context, event: Event, initial: bool = False) -> Dict[str, Any]:
        args = []
        args.append(self.update_modal_mouse(context, event))
        if self.use_raycast:
            args.append(self.update_raycast(context, event, initial))
        return args

    def _is_context_valid(self, context: Context) -> bool:
        """Validate that the context mode matches the required mode for modal execution.
        
        This prevents modal execution when the user switches modes (e.g., TAB key press
        during modal execution in EDIT_MESH mode).
        
        Args:
            context (Context): The Blender context.
            
        Returns:
            bool: True if context is valid, False otherwise.
        """
        if self.bl_context_mode is None:
            return True
        return context.mode == self.bl_context_mode

    def action(self, context: Context, event: Event) -> bool | str:
        return False

    def invoke(self, context: Context, event: Event) -> Set[str]:
        if self._non_modal_events:
            event_key = (event.type, event.value, event.ctrl, event.shift, event.alt)
            if event_key in self._non_modal_events:
                msg = self.action(context, event)
                if isinstance(msg, str):
                    self.report({"ERROR"}, msg)
                    return OpReturn.CANCEL
                elif isinstance(msg, bool):
                    return OpReturn.FINISH if msg else OpReturn.CANCEL
                elif msg is None:
                    return OpReturn.PASS
                return msg
        if not context.window_manager.modal_handler_add(self):
            return OpReturn.CANCEL
        try:
            self._modal_begin(context, event)
        except Exception:
            # Don't leak draw handlers/timers bound to a dead operator instance.
            if getattr(self, '_tm_timer', None) is not None:
                context.window_manager.event_timer_remove(self._tm_timer)
                self._tm_timer = None
            if handlers := getattr(self, '_remove_draw_handlers', None):
                handlers.call_callbacks()
                handlers.clear_callbacks()
            self.running = False
            raise
        return OpReturn.RUN

    def _modal_begin(self, context: Context, event: Event) -> None:
        self.running = True
        self._tm_timer = None
        self._submodal = None
        self._remove_draw_handlers: CallbackList = CallbackList()

        # Add Draw Handlers.
        if 'POST_PIXEL' in self._draw_handler_types:
            self.add_draw_handler(context, self.draw_2d, args=(context,), draw_type="POST_PIXEL")
        if 'POST_VIEW' in self._draw_handler_types:
            self.add_draw_handler(context, self.draw_3d_post, args=(context,), draw_type="POST_VIEW")
        if 'PRE_VIEW' in self._draw_handler_types:
            self.add_draw_handler(context, self.draw_3d_pre, args=(context,), draw_type="PRE_VIEW")

        if self._draw_handler_types:
            context.region.tag_redraw()

        args = self.get_update_modal_args(context, event, initial=True)

        self.modal_begin(context, event, *args)

        # Add Timer.
        if self.use_timer:
            self._tm_timer = context.window_manager.event_timer_add(self.timer_interval, window=context.window)

    def modal(self, context: Context, event: Event) -> Set[str]:
        res = self._modal(context, event)
        if res in (OpReturn.FINISH, OpReturn.CANCEL):
            return self._modal_end(context, cancel=(res == OpReturn.CANCEL))
        return res

    def _modal(self, context: Context, event: Event) -> Set[str]: 
        # Validate context mode. If invalid, cancel modal (e.g. mode switched via TAB).
        if not self._is_context_valid(context):
            return self._modal_end(context, cancel=True)
        
        # Handle Timer events.
        if self.use_timer and event.type == "TIMER":
            self.modal_step_timer(context, event)
            return OpReturn.RUN

        # Handle Sub-Modal.
        if self._submodal is not None:
            if not self._submodal(context, event):
                self._submodal = None
            return OpReturn.RUN

        # Handle op class cancel/confirm events.
        if event.type in self.cancel_on and event.value == "PRESS":
            return self._modal_end(context, cancel=True)
        if event.type in self.confirm_on and event.value == "PRESS":
            return self._modal_end(context, cancel=False)

        # Handle modal update.
        if event.type in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'}:
            args = self.get_update_modal_args(context, event)
            if res := self.modal_step_move(context, event, *args):
                if res in (OpReturn.FINISH, OpReturn.CANCEL):
                    return self._modal_end(context, cancel=(res == OpReturn.CANCEL))
                return OpReturn.RUN
            return OpReturn.PASS
        res = self.modal_step(context, event)
        if res in (OpReturn.FINISH, OpReturn.CANCEL):
            return self._modal_end(context, cancel=(res == OpReturn.CANCEL))
        if callable(res):
            # Next modal step will use the submodal!
            self._submodal = res
            return OpReturn.RUN
        return res

    def _modal_end(self, context: Context, *, cancel: bool) -> Set[str]:
        if not self.running:
            return OpReturn.CANCEL

        # Remove Timer.
        if self._tm_timer is not None:
            context.window_manager.event_timer_remove(self._tm_timer)
            self._tm_timer = None

        # Remove Draw Handlers.
        self._remove_draw_handlers.call_callbacks()
        self._remove_draw_handlers.clear_callbacks()

        if self._draw_handler_types:
            context.region.tag_redraw()

        self.modal_end(context, cancel, self.modal_mouse)

        self.running = False
        return OpReturn.CANCEL if cancel else OpReturn.FINISH

    def add_draw_handler(self, context: Context, callback, args=(), region_type: str = "WINDOW", draw_type: str = "POST_VIEW"):
        """Add a draw handler.

        Args:
            context (Context): The Blender context.
            callback (Callable): The draw handler callback.
            args (tuple, optional): The arguments to pass to the callback. Defaults to ().
            region_type (str, optional): The region type to draw in. Defaults to "WINDOW".
            draw_type (str, optional): The draw type. Defaults to "POST_VIEW". Possible values: {"POST_PIXEL", "PRE_VIEW", "POST_VIEW"}.

        Returns:
            Any: The draw handler.
        """
        # Wrap callback to validate context before execution
        def draw_handler_wrapper(*args, **kwargs):
            # Only draw if context is still valid (prevents errors when mode switched)
            if self._is_context_valid(args[0] if args and isinstance(args[0], Context) else context):
                return callback(*args, **kwargs)
        
        handler = context.space_data.draw_handler_add(draw_handler_wrapper, args, region_type, draw_type)
        self._remove_draw_handlers.add_callback(lambda handler=handler, region_type=region_type: context.space_data.draw_handler_remove(handler, region_type))
        return handler

    def draw_2d(self, context: Context) -> None:
        """Handle 2D drawing.

        Args:
            context (Context): The Blender context.
        """
        pass

    def draw_3d_pre(self, context: Context) -> None:
        """Handle 3D pre-view drawing.

        Args:
            context (Context): The Blender context.
        """
        pass

    def draw_3d_post(self, context: Context) -> None:
        """Handle 3D post-view drawing.

        Args:
            context (Context): The Blender context.
        """
        pass

    def modal_begin(self, context: Context, event: Event, modal_mouse: ModalMouse, *, raycast_info: RaycastInfo | BVHTreeRaycastInfo | None = None) -> None:
        """Handle modal begin events.

        Args:
            context (Context): The Blender context.
            event (Event): The Blender event.
            modal_mouse (ModalMouse): The modal mouse.
            raycast_info (RaycastInfo | BVHTreeRaycastInfo | None, optional): The raycast info. Defaults to None.
        """
        pass

    def modal_step(self, context: Context, event: Event) -> Set[str] | Callable[[Context, Event], bool]:
        """Handle modal update events.

        Returns:
            Set[str] | Callable[[Context, Event], bool]: The result of the modal step.
        """
        return OpReturn.FINISH

    def modal_step_move(self, context: Context, event: Event, mouse: ModalMouse, *, raycast_info: RaycastInfo | BVHTreeRaycastInfo | None = None) -> bool:
        """Handle mouse move events.
        
        Args:
            context (Context): The Blender context.
            event (Event): The Blender event.
            modal_mouse (ModalMouse): The modal mouse.
            raycast_info (RaycastInfo | BVHTreeRaycastInfo | None, optional): The raycast info. Defaults to None.

        Returns:
            bool: True if the event was handled, False otherwise.
        """
        return False

    def modal_step_timer(self, context: Context, event: Event) -> None:
        """Handle timer events.

        Args:
            context (Context): The Blender context.
            event (Event): The Blender event.
        """
        pass

    def modal_end(self, context: Context, cancel: bool, mouse: ModalMouse) -> None:
        """Handle modal end finish and cancel events.

        Args:
            context (Context): The Blender context.
            cancel (bool): True if the modal was cancelled, False otherwise.
            mouse (ModalMouse): The modal mouse.
        """
        pass
