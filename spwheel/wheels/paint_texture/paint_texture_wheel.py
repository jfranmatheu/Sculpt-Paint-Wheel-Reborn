from bpy.types import Context

from ..sculpt_paint_base import SculptPaintWheel

class PaintTextureWheel(SculptPaintWheel):
    bl_context_mode = 'PAINT_TEXTURE'
