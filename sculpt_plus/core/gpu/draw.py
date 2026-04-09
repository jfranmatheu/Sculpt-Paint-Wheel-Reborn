from __future__ import annotations
from typing import Any, Sequence
from gpu.types import GPUTexture
from .geom_specs import GeomSpec
from ._draw.draw_shader import draw_shader_auto, draw_shader_points, draw_shader_tris

@draw_shader_auto
def example_auto(primitives_coords: Sequence[tuple[float, ...]] | GeomSpec, *, color: tuple[float, float, float, float] = (0.2, 0.8, 0.4, 1.0), _cache_idname: str | None = None) -> None:
    ''' Example auto shader

    Parameters:
    - primitives_coords: For points and lines: sequence of primitives' (2D | 3D) coordinates. For shapes: use a (2D | 3D) GeomSpec or a tuple with (tris_coords, tris_indices)
    '''
    pass

@draw_shader_points
def example_points(points_coords: Sequence[tuple[float, float, float]], *, size: float = 10.0, color: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0), _cache_idname: str | None = None) -> None:
    ''' Example points shader

    Parameters:
    - points_coords: (3D) Point coordinates
    '''
    pass

@draw_shader_tris
def example_texture(geom_spec: GeomSpec, uv: Sequence[tuple[float, float]], tex: GPUTexture, *, _cache_idname: str | None = None) -> None:
    ''' Example texture shader

    Parameters:
    - geom_spec: (2D) GeomSpec or a tuple with (tris_coords, tris_indices)
    - uv: Texture coordinates
    - tex: Texture to sample
    '''
    pass
