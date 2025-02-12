from typing import Tuple, Union
import math
from .vector import Vector2
from .angles import degrees_to_radians, radians_to_degrees

Point2D = Union[Tuple[float, float], Vector2]

def rotate_point_around_origin_rad(point: Point2D, 
                                 angle_rad: float, 
                                 origin: Point2D = (0, 0)) -> Vector2:
    """
    Rotate a point around a specific origin point using radians.
    Returns Vector2 with rotated coordinates.
    """
    if isinstance(point, tuple):
        point = Vector2.from_tuple(point)
    if isinstance(origin, tuple):
        origin = Vector2.from_tuple(origin)
    
    # Translate point to origin
    translated = point - origin
    
    # Rotate
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    x = translated.x * cos_a - translated.y * sin_a
    y = translated.x * sin_a + translated.y * cos_a
    
    # Translate back
    return Vector2(x, y) + origin

def rotate_point_around_origin_deg(point: Point2D, 
                                 angle_deg: float, 
                                 origin: Point2D = (0, 0)) -> Vector2:
    """
    Rotate a point around a specific origin point using degrees.
    Returns Vector2 with rotated coordinates.
    """
    return rotate_point_around_origin_rad(point, degrees_to_radians(angle_deg), origin)

def scale_point_around_origin(point: Point2D,
                            scale: Union[float, Vector2, Tuple[float, float]],
                            origin: Point2D = (0, 0)) -> Vector2:
    """
    Scale a point around a specific origin point.
    Scale can be uniform (single float) or non-uniform (Vector2 or tuple).
    """
    if isinstance(point, tuple):
        point = Vector2.from_tuple(point)
    if isinstance(origin, tuple):
        origin = Vector2.from_tuple(origin)
    if isinstance(scale, (int, float)):
        scale = Vector2(scale, scale)
    elif isinstance(scale, tuple):
        scale = Vector2.from_tuple(scale)
    
    # Translate to origin, scale, and translate back
    return (point - origin) * scale + origin
