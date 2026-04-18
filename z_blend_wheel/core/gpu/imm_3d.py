"""Immediate-mode 3D GPU drawing functions."""

import math
import os
from pathlib import Path
from typing import Tuple
import bpy
from bpy.types import Image
import gpu
from gpu.types import GPUTexture
from gpu.shader import create_from_info, from_builtin
from gpu_extras.batch import batch_for_shader
from mathutils import Color, Matrix, Vector
from gpu.texture import from_image
from .state_control import CM_GPU_BLEND, gpu_state


if not bpy.app.background:
    UNIFORM_COLOR_SHADER = from_builtin('UNIFORM_COLOR')
    POLYLINE_UNIFORM_COLOR_SHADER = from_builtin('POLYLINE_UNIFORM_COLOR')
else:
    UNIFORM_COLOR_SHADER = None
    POLYLINE_UNIFORM_COLOR_SHADER = None


def draw_circle_3d(center: Vector, normal: Vector, radius: float, color: Color, segments: int = 32, thickness: float = 1.0):
    """Draw a circle in 3D space."""
    # coords
    coords = []
    for i in range(segments):
        angle = i * (2 * math.pi) / segments
        x = math.cos(angle) * radius
        y = math.sin(angle) * radius
        z = 0.0
        # rotate and translate
        mat = Matrix.LocRotScale(center, normal, Vector((1.0, 1.0, 1.0)))
        x, y, z = mat @ Vector((x, y, z))
        coords.append((x, y, z))
    # batch creation
    batch = batch_for_shader(POLYLINE_UNIFORM_COLOR_SHADER, 'LINE_STRIP', {"pos": coords})
    # draw
    with CM_GPU_BLEND('ALPHA'):
        POLYLINE_UNIFORM_COLOR_SHADER.uniform_float("color", color)
        gpu.state.line_width_set(thickness)
        batch.draw(POLYLINE_UNIFORM_COLOR_SHADER)
        gpu.state.line_width_set(1.0)
