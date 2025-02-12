from typing import Set, Callable, Type

from bpy.types import Context, Event, Area, Region, Space, SpaceNodeEditor

from .generic import Generic
from ....enums.operator import OpsReturn, SubmodalReturn
from ....utils.cursor import Cursor
# from ...deco.ops_modal_flags import ModalFlags  # commented to fix circular import error

__all__ = ['Modal']


class ModalCursor:
    ''' Use at modal classes that. '''
    _current_cursor: Cursor | None = None
    _previous_cursor: Cursor | None = None

    def set_cursor(self, cursor_type: Cursor) -> None:
        """Set the cursor type for the modal operator.
        
        Args:
            cursor_type: The Cursor enum value to set
            context: Optional context override
        """
        # Store the current cursor type if we haven't stored one yet
        if self._current_cursor is not None:
            self._previous_cursor = self._current_cursor

        self._current_cursor = cursor_type
        cursor_type.set_icon(getattr(self, '_context', None))

    def restore_cursor(self) -> None:
        """Restore the cursor to its previous state.
        
        Args:
            context: Optional context override
        """
        if self._current_cursor is not None:
            Cursor.restore(getattr(self, '_context', None))

    def wrap_cursor(self, x: int, y: int) -> None:
        """Wrap the cursor to specified coordinates.
        
        Args:
            context: Optional context override
        """
        Cursor.wrap(x, y, getattr(self, '_context', None))


class Modal(ModalCursor, Generic):
    modal_finish_keymaps = {}
    modal_cancel_keymaps = {}

    _modal_instance: 'Modal' = None
    _context: Context
    _event: Event
    _submodal: Callable = None
    _region: Region = None
    _area: Area = None

    _modal_flags: Set[Type] = None  # ModalFlags
    _draw_postpixel_space: Space = None
    _draw_preview_space: Space = None
    _draw_postview_space: Space = None
    _draw_backdrop_treetype: str | None = None

    @classmethod
    def get_modal_instance(cls) -> 'Modal':
        return cls._modal_instance


    ''' Modal Start. '''
    def invoke(self, context: Context, event: Event) -> Set[str]:
        """ Internal method! """
        if not context.window_manager.modal_handler_add(self):
            print("WARN! Operator failed to add modal handler!")
            return OpsReturn.CANCEL
        self._modal_enter(context, event)
        return OpsReturn.RUN

    def execute(self, context: Context) -> Set[str]:
        """ Unused method! """
        raise NotImplementedError("Call modal via invoke!")

    def _modal_enter(self, context: Context, event: Event) -> None:
        """ Internal method! Use modal_enter() instead. """
        self._context = context
        self._event = event
        self._area = context.area
        self._region = context.region
        self.__class__._modal_instance = self
        self._start_drawing(context)
        context.area.tag_redraw()  # full editor redraw.
        self.modal_enter(context, event)

    def modal_enter(self, context: Context, event: Event) -> None:
        pass

    ''' Modal Update. '''
    def inject_submodal(self, submodal: Callable) -> None:
        """ Injects a submodal callable.
        This submodal function should return SubmodalReturn item.
        """
        self._submodal = submodal

    def modal(self, context: Context, event: Event) -> Set[str]:
        """ Internal method! Use modal_update() instead. """
        self._context = context
        self._event = event

        # Submodal processing.
        if self._submodal is not None:
            ret = self._submodal(context, event)
            assert ret is not None and isinstance(ret, SubmodalReturn), \
                "Submodal needs to return a {SubmodalReturn} type from {SubmodalReturn.__module__}."
            if ret == SubmodalReturn.STOP:
                self._submodal = None
            return OpsReturn.RUN

        # Modal processing.
        ret = self.modal_update(context, event)
        if ret is None:
            return OpsReturn.RUN
        if isinstance(ret, set):
            if ret == OpsReturn.FINISH:
                self._modal_exit(context, cancel=False)
            elif ret == OpsReturn.CANCEL:
                self._modal_exit(context, cancel=True)
            return ret
        return OpsReturn.FINISH

    def modal_update(self, context: Context, event: Event) -> OpsReturn | None:
        '''
            Return:
                OpsReturn | None.
        '''
        pass


    ''' Modal End. '''
    def _modal_exit(self, context: 'Context', cancel: bool) -> None:
        """ Internal method! Use modal_exit() instead. """
        self.restore_cursor()
        self._stop_drawing()
        context.area.tag_redraw()  # full editor redraw.
        self.modal_exit(context, cancel)

    def modal_exit(self, context: 'Context', cancel: bool) -> None:
        pass


    ''' Modal Draw. '''
    def tag_redraw(self, context: Context | None = None) -> None:
        region: Region = context.region if context is not None else self._region
        region.tag_redraw()

    def _start_drawing(self, context: Context) -> None:
        if self._modal_flags is None:
            return
        from ...flags.modal import ModalFlags
        if ModalFlags.DRAW_POST_PIXEL in self._modal_flags and self._draw_postpixel_space is not None:
            self._draw_handler_postpixel = self._draw_postpixel_space.draw_handler_add(self._draw_2d, (context, ), 'WINDOW', 'POST_PIXEL')
        if ModalFlags.DRAW_POST_VIEW in self._modal_flags and self._draw_postview_space is not None:
            self._draw_handler_postview = self._draw_postview_space.draw_handler_add(self._draw_2d, (context, ), 'WINDOW', 'POST_VIEW')
        if ModalFlags.DRAW_PRE_VIEW in self._modal_flags and self._draw_preview_space is not None:
            self._draw_handler_preview = self._draw_preview_space.draw_handler_add(self._draw_2d, (context, ), 'WINDOW', 'PRE_PIXEL')
        if ModalFlags.DRAW_BACKDROP in self._modal_flags and self._draw_backdrop_treetype is not None:
            self._draw_handler_backdrop = SpaceNodeEditor.draw_handler_add(self._draw_2d, (context, ), 'WINDOW', 'BACKDROP')

    def _stop_drawing(self) -> None:
        if self._modal_flags is None:
            return
        if hasattr(self, '_draw_handler_postpixel') and self._draw_handler_postpixel is not None:
            self._draw_postpixel_space.draw_handler_remove(self._draw_handler_postpixel, 'WINDOW')
        if hasattr(self, '_draw_handler_postview') and self._draw_handler_postview is not None:
            self._draw_postview_space.draw_handler_remove(self._draw_handler_postview, 'WINDOW')
        if hasattr(self, '_draw_handler_preview') and self._draw_handler_preview is not None:
            self._draw_preview_space.draw_handler_remove(self._draw_handler_preview, 'WINDOW')
        if hasattr(self, '_draw_handler_backdrop') and self._draw_handler_backdrop is not None:
            SpaceNodeEditor.draw_handler_remove(self._draw_handler_backdrop, 'WINDOW')

    def _draw_3d(self, context: Context, area: Area) -> None:
        """ Internal method! Use draw_3d() instead. """
        if context.area != self._area:
            return
        self.draw_3d(context)

    def _draw_2d(self, context: Context) -> None:
        """ Internal method! Use draw_2d() instead. """
        if context.area != self._area:
            return
        self.draw_2d(context)

    def _draw_backdrop(self, context: Context) -> None:
        """ Internal method! Use draw_backdrop() instead. """
        if context.area != self._area:
            return
        if context.space_data.tree_type != self._draw_backdrop_treetype:
            return
        self.draw_backdrop(context)

    def draw_3d(self, context: Context) -> None:
        pass

    def draw_2d(self, context: Context) -> None:
        pass

    def draw_backdrop(self, context: Context) -> None:
        pass
