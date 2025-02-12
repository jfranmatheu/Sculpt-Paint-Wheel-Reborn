from enum import Enum

import bpy
from bpy.types import Context


__all__ = [
    'Cursor',
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
