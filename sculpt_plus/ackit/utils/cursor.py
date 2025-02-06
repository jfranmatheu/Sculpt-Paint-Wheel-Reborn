from enum import Enum

import bpy
from bpy.types import Context


__all__ = [
    'Cursor',
    'ModalCursor',
]

class Cursor(Enum):
    DEFAULT       =      'DEFAULT'
    NONE          =         'NONE'
    WAIT          =         'WAIT'
    CROSSHAIR     =    'CROSSHAIR'
    MOVE_X        =       'MOVE_X'
    MOVE_Y        =       'MOVE_Y'
    KNIFE         =        'KNIFE'
    TEXT          =         'TEXT'
    PAINT_BRUSH   =  'PAINT_BRUSH'
    PAINT_CROSS   =  'PAINT_CROSS'
    HAND          =         'HAND'
    SCROLL_X      =     'SCROLL_X'
    SCROLL_Y      =     'SCROLL_Y'
    SCROLL_XY     =    'SCROLL_XY'
    EYEDROPPER    =   'EYEDROPPER'
    DOT           =          'DOT'
    ERASER        =       'ERASER'

    def set_icon(self, context: Context | None = None) -> None:
        context = context if context is not None else bpy.context
        context.window.cursor_modal_set(self.value)

    @staticmethod
    def wrap(x: int, y: int, context: Context | None = None) -> None:
        context = context if context is not None else bpy.context
        context.window.cursor_warp(x, y)

    @staticmethod
    def restore(context: Context | None = None) -> None:
        context = context if context is not None else bpy.context
        context.window.cursor_modal_restore()


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
