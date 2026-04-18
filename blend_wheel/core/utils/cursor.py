from enum import Enum
from typing import Optional

import bpy
from bpy.types import Context


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

    def set(self, context: Optional[Context] = None) -> None:
        """ Set the cursor icon. """
        context = context if context is not None else bpy.context
        context.window.cursor_modal_set(self.value)

    @staticmethod
    def wrap(x: float, y: float, context: Optional[Context] = None) -> None:
        """ Wrap the cursor. """
        context = context if context is not None else bpy.context
        context.window.cursor_warp(x, y)

    @staticmethod
    def restore(context: Optional[Context] = None) -> None:
        """ Restore the cursor. """
        context = context if context is not None else bpy.context
        context.window.cursor_modal_restore()
