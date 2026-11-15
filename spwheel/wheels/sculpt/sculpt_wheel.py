from bpy.types import Context

from ..sculpt_paint_base import SculptPaintWheel

class SculptWheel(SculptPaintWheel):
    bl_context_mode = 'SCULPT'


class SculptCurvesWheel(SculptPaintWheel):
    bl_context_mode = 'SCULPT_CURVES'


class SculptGreasePencilWheel(SculptPaintWheel):
    bl_context_mode = 'SCULPT_GREASE_PENCIL'
