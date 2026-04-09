from typing import TYPE_CHECKING, Any, Dict, Literal, Set, Tuple, Type, TypeVar, overload

from bpy.types import Context, Event, UILayout, Operator

from ..tool_preselection import PreselectionInfo
from ..tool_specs import ToolRaycastSpecs, ToolPreselectionSpecs
from ....utils.raycast_utils import RaycastInfo, BVHTreeRaycastInfo
from ....utils.mouse_utils import ModalMouse

from ..common import draw_km_event

if TYPE_CHECKING:
    from .btype_tool_multi import BType_WorkSpaceToolMulti
else:
    BType_WorkSpaceToolMulti = None


T = TypeVar('T', bound='Tool')


class Tool:
    _instance = None
    _btype_tool_cls: 'BType_WorkSpaceToolMulti' = None
    _operator_instance: Operator = None

    name: str = ""
    icon: Any = None
    keymaps: Tuple[Tuple[str, Dict[str, Any], Dict[str, Any]], ...] = ()
    raycast_specs: ToolRaycastSpecs | None = None
    preselection_specs: ToolPreselectionSpecs | None = None
    _is_modal: bool = False

    # Runtime attributes.
    in_modal: bool = False
    # raycast_info: RaycastInfo | BVHTreeRaycastInfo | None = None

    @property
    def use_raycast(self) -> bool:
        return self.raycast_specs is not None

    @property
    def use_preselection(self) -> bool:
        return self.preselection_specs is not None

    def can_draw_preselection(self, context: Context) -> bool:
        if context.active_object is None or context.active_object.type != 'MESH':
            return False
        if not self.use_preselection or self.preselection_specs.geom_types == set():
            return False
        if self.in_modal and not self.preselection_specs.use_in_modal:
            return False
        # if self.raycast_specs.mode == 'BVHTREE' and context.mode != 'EDIT_MESH':
        #     return False
        return True

    @classmethod
    def get_instance(cls) -> 'Tool':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @staticmethod
    def set_raycast_specs(mode: Literal['SCENE', 'OBJECT', 'BVHTREE'],
                          use_in_modal: bool = True,
                          block_tool_init: bool = True,
                          block_tool_modal: bool = True) -> Type[T]:
        """Set the raycast specs for the decorated tool.

        Args:
            mode (Literal['SCENE', 'OBJECT', 'BVHTREE']): The raycast mode.
            use_in_modal (bool, optional): Whether to use raycast in modal. Defaults to False.
            block_tool_init (bool, optional): Whether to block tool init when first hit is invalid. Defaults to True.
            block_tool_modal (bool, optional): Whether to block tool modal when hit is invalid. Defaults to True.
        """
        def decorator(cls: Type[T]) -> Type[T]:
            cls.raycast_specs = ToolRaycastSpecs(mode=mode, use_in_modal=use_in_modal, block_tool_init=block_tool_init, block_tool_modal=block_tool_modal)
            return cls
        return decorator

    @staticmethod
    def set_preselection_specs(geom_types: Set[Literal['FACE', 'EDGE', 'VERT']],
                               use_in_modal: bool = False,
                               color: Tuple[float, float, float, float] = (0.9, 0.5, 0.05, 0.5),
                               point_size: float = 8.0,
                               line_width: float = 3.0) -> Type[T]:
        """Set the preselection specs for the decorated tool.

        Args:
            geom_types (Set[Literal['FACE', 'EDGE', 'VERT']]): The preselection types.
            use_in_modal (bool, optional): Whether to use preselection in modal. Defaults to False.
            color (Tuple[float, float, float, float], optional): The preselection color. Defaults to (0.9, 0.5, 0.05, 0.5).
            point_size (float, optional): The preselection point size. Defaults to 8.0.
            line_width (float, optional): The preselection line width. Defaults to 3.0.
        """
        def decorator(cls: Type[T]) -> Type[T]:
            cls.preselection_specs = ToolPreselectionSpecs(geom_types=geom_types, use_in_modal=use_in_modal, color=color, point_size=point_size, line_width=line_width)
            return cls
        return decorator

    # Tool Methods ----------------------------------------------------
    def draw_header(self, context: Context, layout: UILayout):
        pass

    def draw_cursor(self, context: Context, xy: Tuple[int, int]):
        pass

    def draw_statusbar(self, context: Context, layout: UILayout):
        for km in self.keymaps:
            draw_km_event(layout, km)

    def on_tool_enter(self, context: Context):
        pass

    def on_tool_exit(self, context: Context):
        pass

    def draw_2d(self, context: Context):
        pass

    def draw_3d(self, context: Context):
        pass

    def draw_previz(self, context: Context, info: PreselectionInfo) -> None:
        pass

    # Operator Methods ----------------------------------------------------

    @classmethod
    def poll(cls, context: Context, event: Event) -> bool:
        """Polling for non-modal tools."""
        return True

    def action(self, context: Context, event: Event) -> None:
        """Action to perform when the tool keymap is actioned. WITHOUT raycast capabilities."""
        pass

    @overload
    def action(self, context: Context, event: Event, raycast_info: RaycastInfo | BVHTreeRaycastInfo | None = None) -> None:
        """Action to perform when the tool keymap is actioned. WITH raycast capabilities."""
        pass

    def modal_begin(self, context: Context, event: Event, modal_mouse: ModalMouse) -> None:
        """Modal begin WITHOUT raycast capabilities."""
        pass

    @overload
    def modal_begin(self, context: Context, event: Event, modal_mouse: ModalMouse, raycast_info: RaycastInfo | BVHTreeRaycastInfo | None = None) -> None:
        """Modal begin WITH raycast capabilities."""
        pass

    def modal_step_timer(self, context: Context, event: Event) -> None:
        pass

    def modal_step_move(self, context: Context, event: Event, modal_mouse: ModalMouse) -> bool | None:
        """Modal step mousemove WITHOUT raycast capabilities."""
        pass

    @overload
    def modal_step_move(self, context: Context, event: Event, modal_mouse: ModalMouse, raycast_info: RaycastInfo | BVHTreeRaycastInfo | None = None) -> bool | None:
        """Modal step mousemove WITH raycast capabilities."""
        pass

    def modal_step(self, context: Context, event: Event) -> bool | None:
        """Modal step mousemove WITHOUT raycast capabilities."""
        pass

    def modal_end(self, context: Context, event: Event, cancel: bool) -> None:
        pass
