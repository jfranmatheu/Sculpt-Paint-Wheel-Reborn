from bpy.types import Context

from ..sculpt_paint_base import SculptPaintWheel

class SculptWheel(SculptPaintWheel):
    bl_context_mode = 'SCULPT'
