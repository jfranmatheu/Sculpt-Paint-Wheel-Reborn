"""Immediate-mode 2D GPU drawing functions."""

import os
from pathlib import Path
from typing import Literal, Tuple
import blf
import bpy
from bpy.types import Image
import gpu
from gpu.types import GPUTexture
from gpu.shader import create_from_info, from_builtin
from gpu_extras.batch import batch_for_shader
from gpu_extras.presets import draw_circle_2d as _draw_circle_2d, draw_texture_2d as _draw_texture_2d
from mathutils import Color, Vector
from gpu.texture import from_image
from .state_control import CM_GPU_BLEND, gpu_state


UNIFORM_COLOR_SHADER = from_builtin('UNIFORM_COLOR')
POLYLINE_UNIFORM_COLOR_SHADER = from_builtin('POLYLINE_UNIFORM_COLOR')

_gpu_tex_cache: dict[str | Image, GPUTexture] = {}


def draw_circle(x: int, y: int, radius: float, color: Color, segments: int = 16):
    """Draw a circle on the screen.

    Args:
        x (int): The x-coordinate of the center of the circle.
        y (int): The y-coordinate of the center of the circle.
        radius (float): The radius of the circle.
        color (Color): The color of the circle.
        segments (int, optional): The number of segments to use for the circle. Defaults to 16.
    """
    with CM_GPU_BLEND('ALPHA'):
        _draw_circle_2d((x, y), color, radius, segments=segments)


def draw_texture(texture: GPUTexture | Image | str | Path, x: int, y: int, width: int, height: int):
    """Draw a texture on the screen.

    Args:
    texture (GPUTexture | Image | str | Path): The texture to draw.
        x (int): The x-coordinate of the top-left corner of the texture.
        y (int): The y-coordinate of the top-left corner of the texture.
        width (int): The width of the texture.
        height (int): The height of the texture.
    """
    if isinstance(texture, Path):
        texture = str(texture) if isinstance(texture, Path) else texture
    if isinstance(texture, (str, Image)):
        if texture in _gpu_tex_cache:
            gpu_tex = _gpu_tex_cache[texture]
        else:
            if isinstance(texture, (str, Path)):
                assert os.path.exists(texture), f"Texture file not found: {texture}"
                image = bpy.data.images.load(texture, check_existing=True)
                # image.name = f".{image.name}" # hide it
            else:
                image = texture
            gpu_tex = from_image(image)
            _gpu_tex_cache[texture] = gpu_tex
    else:
        gpu_tex = texture

    with CM_GPU_BLEND('ALPHA'):
        _draw_texture_2d(gpu_tex, (x, y), width, height)


def draw_rect_fill(x: int, y: int, width: int, height: int, color: Color, corner_radius: float = 0.0):
    """Draw a filled rectangle on the screen.

    Args:
        x (int): The x-coordinate of the top-left corner of the rectangle.
        y (int): The y-coordinate of the top-left corner of the rectangle.
        width (int): The width of the rectangle.
        height (int): The height of the rectangle.
        color (Color): The color of the rectangle.
    """
    # Create a batch of vertices for the rectangle
    if corner_radius == 0.0:
        vertices = [
            (x, y),
            (x + width, y),
            (x + width, y + height),
            (x, y + height),
        ]
        indices = [
            (0, 1, 2),
            (2, 3, 0),
        ]
    else:
        # Create a batch of vertices for the rounded rectangle
        vertices = [
            (x + corner_radius, y),
            (x + width - corner_radius, y),
            (x + width, y + corner_radius),
            (x + width, y + height - corner_radius),
            (x + width - corner_radius, y + height),
            (x + corner_radius, y + height),
            (x, y + height - corner_radius),
            (x, y + corner_radius),
        ]
        indices = [
            (0, 1, 2),
            (2, 3, 4),
            (4, 5, 6),
            (6, 7, 0),
        ]
    batch = batch_for_shader(UNIFORM_COLOR_SHADER, 'TRIS', {"pos": vertices}, indices=indices)
    # Set the shader uniform color
    UNIFORM_COLOR_SHADER.bind()
    UNIFORM_COLOR_SHADER.uniform_float("color", color)
    # Draw the batch
    with CM_GPU_BLEND('ALPHA'):
        batch.draw(UNIFORM_COLOR_SHADER)


def draw_rect_outline(x: int, y: int, width: int, height: int, color: Color, line_width: float = 1.0, corner_radius: float = 0.0):
    """Draw an outline of a rectangle on the screen.

    Args:
        x (int): The x-coordinate of the top-left corner of the rectangle.
        y (int): The y-coordinate of the top-left corner of the rectangle.
        width (int): The width of the rectangle.
        height (int): The height of the rectangle.
        color (Color): The color of the rectangle outline.
        line_width (float, optional): The width of the outline line. Defaults to 1.0.
    """
    # Create a batch of vertices for the rectangle outline
    if corner_radius == 0.0:
        vertices = [
            (x, y),
            (x + width, y),
            (x + width, y + height),
            (x, y + height),
        ]
        indices = [
            (0, 1),
            (1, 2),
            (2, 3),
            (3, 0),
        ]
    else:
        # Create a batch of vertices for the rounded rectangle outline
        vertices = [
            (x + corner_radius, y),
            (x + width - corner_radius, y),
            (x + width, y + corner_radius),
            (x + width, y + height - corner_radius),
            (x + width - corner_radius, y + height),
            (x + corner_radius, y + height),
            (x, y + height - corner_radius),
            (x, y + corner_radius),
        ]
        indices = [
            (0, 1),
            (1, 2),
            (2, 3),
            (3, 4),
            (4, 5),
            (5, 6),
            (6, 7),
            (7, 0),
        ]
    batch = batch_for_shader(POLYLINE_UNIFORM_COLOR_SHADER, 'LINES', {"pos": vertices}, indices=indices)
    # Set the shader uniform color and line width
    x, y, w, h = gpu.state.active_framebuffer_get().viewport_get()
    POLYLINE_UNIFORM_COLOR_SHADER.bind()
    POLYLINE_UNIFORM_COLOR_SHADER.uniform_float("color", color)
    POLYLINE_UNIFORM_COLOR_SHADER.uniform_float("lineWidth", line_width)
    POLYLINE_UNIFORM_COLOR_SHADER.uniform_float('viewportSize', (w, h))
    # Draw the batch
    with CM_GPU_BLEND('ALPHA'):
        batch.draw(POLYLINE_UNIFORM_COLOR_SHADER)


def draw_rect(x: int, y: int, width: int, height: int, fill_color: Color, outline_color: Color, line_width: float = 1.0, corner_radius: float = 0.0):
    """Draw a rectangle on the screen.

    Args:
        x (int): The x-coordinate of the top-left corner of the rectangle.
        y (int): The y-coordinate of the top-left corner of the rectangle.
        width (int): The width of the rectangle.
        height (int): The height of the rectangle.
        fill_color (Color): The color of the rectangle fill.
        outline_color (Color): The color of the rectangle outline.
        line_width (float, optional): The width of the outline line. Defaults to 1.0.
    """
    with CM_GPU_BLEND('ALPHA'):
        draw_rect_fill(x, y, width, height, fill_color, corner_radius)
        draw_rect_outline(x, y, width, height, outline_color, line_width, corner_radius)


def draw_lines(lines: list[Vector], color: Color, line_width: float = 1.0, strip: bool = False):
    """Draw a series of lines on the screen.

    Args:
        lines (list[list[Vector]]): A list of lines, where each line is a list of vertices.
        color (Color): The color of the lines.
        line_width (float, optional): The width of the lines. Defaults to 1.0.
    """
    # Create a batch of vertices for the lines
    batch = batch_for_shader(POLYLINE_UNIFORM_COLOR_SHADER, 'LINE_STRIP' if strip else 'LINES', {"pos": lines})
    # Set the shader uniform color and line width
    x, y, w, h = gpu.state.active_framebuffer_get().viewport_get()
    POLYLINE_UNIFORM_COLOR_SHADER.bind()
    POLYLINE_UNIFORM_COLOR_SHADER.uniform_float("color", color)
    POLYLINE_UNIFORM_COLOR_SHADER.uniform_float("lineWidth", line_width)
    POLYLINE_UNIFORM_COLOR_SHADER.uniform_float('viewportSize', (w, h))
    # Draw the batch
    with CM_GPU_BLEND('ALPHA'):
        batch.draw(POLYLINE_UNIFORM_COLOR_SHADER)


def draw_points(points: list[Vector], color: Color, point_size: float = 1.0):
    """Draw a series of points on the screen.

    Args:
        points (list[Vector]): A list of points.
        color (Color): The color of the points.
        point_size (float, optional): The size of the points. Defaults to 1.0.
    """
    # Create a batch of vertices for the points
    batch = batch_for_shader(UNIFORM_COLOR_SHADER, 'POINTS', {"pos": points})
    # Set the shader uniform color and point size
    x, y, w, h = gpu.state.active_framebuffer_get().viewport_get()
    UNIFORM_COLOR_SHADER.bind()
    UNIFORM_COLOR_SHADER.uniform_float("color", color)
    # Draw the batch
    with CM_GPU_BLEND('ALPHA'):
        gpu_state.point_size_set(point_size)
        batch.draw(UNIFORM_COLOR_SHADER)
        gpu_state.point_size_set(1.0)


def draw_polygon(points: list[Vector], color: Color):
    """Draw a polygon on the screen.

    Args:
        points (list[Vector]): A list of points that define the polygon.
        color (Color): The color of the polygon.
    """
    indices = []
    # Simple fan triangulation - much faster than complex loop triangulation
    for i in range(1, len(points) - 1):
        indices.append([0, i, i + 1])

    # Create a batch of vertices for the polygon
    batch = batch_for_shader(UNIFORM_COLOR_SHADER, 'TRIS', {"pos": points}, indices=indices)

    UNIFORM_COLOR_SHADER.bind()
    UNIFORM_COLOR_SHADER.uniform_float("color", color)
    # Draw the batch
    with CM_GPU_BLEND('ALPHA'):
        batch.draw(UNIFORM_COLOR_SHADER)


def draw_text(
    text: str,
    x: float,
    y: float,
    *,
    size: float = 14.0,
    color: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0),
    font_id: int = 0,
    align: Literal['LEFT', 'CENTER', 'RIGHT'] = 'LEFT',
    valign: Literal['BOTTOM', 'MIDDLE', 'TOP'] = 'BOTTOM',
    shadow: bool = False,
    shadow_color: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.75),
    shadow_offset: tuple[float, float] = (1.0, -1.0),
    rotation: float = 0.0,
) -> tuple[float, float]:
    """Draw 2D text at a screen-space position using ``blf``.

    Args:
        text: String to render.
        x, y: Anchor position in screen pixels.
        size: Font size in points (UI scale is applied automatically by blf).
        color: RGBA text colour, each channel 0-1.
        font_id: blf font identifier. 0 = Blender's built-in UI font.
        align: Horizontal anchor. ``'LEFT'`` keeps *x* at the left edge,
            ``'CENTER'`` centres the text on *x*, ``'RIGHT'`` places the
            right edge at *x*.
        valign: Vertical anchor. ``'BOTTOM'`` keeps *y* at the baseline,
            ``'MIDDLE'`` centres vertically on *y*, ``'TOP'`` places the
            cap-height at *y*.
        shadow: When ``True`` a soft drop-shadow is rendered behind the text.
        shadow_color: RGBA colour of the drop-shadow.
        shadow_offset: ``(dx, dy)`` pixel displacement of the shadow relative
            to the text.
        rotation: Counter-clockwise rotation in radians.

    Returns:
        ``(width, height)`` of the rendered string in pixels.
    """
    blf.size(font_id, size)
    tw, th = blf.dimensions(font_id, text)

    draw_x = x
    draw_y = y

    if align == 'CENTER':
        draw_x -= tw * 0.5
    elif align == 'RIGHT':
        draw_x -= tw

    if valign == 'MIDDLE':
        draw_y -= th * 0.5
    elif valign == 'TOP':
        draw_y -= th

    if rotation != 0.0:
        blf.enable(font_id, blf.ROTATION)
        blf.rotation(font_id, rotation)

    if shadow:
        blf.enable(font_id, blf.SHADOW)
        blf.shadow(font_id, 3, *shadow_color)
        blf.shadow_offset(font_id, int(shadow_offset[0]), int(shadow_offset[1]))

    with CM_GPU_BLEND('ALPHA'):
        blf.color(font_id, *color)
        blf.position(font_id, draw_x, draw_y, 0.0)
        blf.draw(font_id, text)

    if shadow:
        blf.disable(font_id, blf.SHADOW)
    if rotation != 0.0:
        blf.disable(font_id, blf.ROTATION)

    return tw, th


def text_dimensions(text: str, size: float = 14.0, font_id: int = 0) -> tuple[float, float]:
    """Return the rendered dimensions ``(width, height)`` of *text* without drawing it.

    Args:
        text: The string to measure.
        size: Font size in points.
        font_id: blf font identifier (0 = built-in UI font).

    Returns:
        ``(width, height)`` in pixels.
    """
    blf.size(font_id, size)
    return blf.dimensions(font_id, text)
