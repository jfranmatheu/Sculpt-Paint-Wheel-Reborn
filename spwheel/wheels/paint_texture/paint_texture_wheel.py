from bpy.types import Context

from ..sculpt_paint_base import SculptPaintWheel

class PaintTextureWheel(SculptPaintWheel):
    bl_context_mode = 'PAINT_TEXTURE'


class VertexPaintWheel(SculptPaintWheel):
    bl_context_mode = 'PAINT_VERTEX'


class PaintGreasePencilWheel(SculptPaintWheel):
    bl_context_mode = 'PAINT_GREASE_PENCIL'


class VertexGreasePencilWheel(SculptPaintWheel):
    bl_context_mode = 'VERTEX_GREASE_PENCIL'
