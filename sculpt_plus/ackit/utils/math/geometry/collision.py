from typing import List, Tuple, Optional
from ..vector import Vector2
from .shapes import Circle, Rectangle, Triangle, Polygon
from .intersect import rect_rect_intersection

def get_collision_normal(shape1: Rectangle, shape2: Rectangle) -> Optional[Vector2]:
    """Calculate collision normal between two rectangles"""
    if not rect_rect_intersection(shape1, shape2):
        return None

    # Calculate overlap in each axis
    overlap_x = min(shape1.max_point.x - shape2.min_point.x,
                   shape2.max_point.x - shape1.min_point.x)
    overlap_y = min(shape1.max_point.y - shape2.min_point.y,
                   shape2.max_point.y - shape1.min_point.y)

    # Return normal in direction of minimum overlap
    if overlap_x < overlap_y:
        return Vector2(1, 0) if shape1.center.x < shape2.center.x else Vector2(-1, 0)
    else:
        return Vector2(0, 1) if shape1.center.y < shape2.center.y else Vector2(0, -1)

def get_collision_depth(shape1: Rectangle, shape2: Rectangle) -> Optional[Tuple[float, Vector2]]:
    """Calculate collision depth and normal between two rectangles"""
    if not rect_rect_intersection(shape1, shape2):
        return None

    overlap_x = min(shape1.max_point.x - shape2.min_point.x,
                   shape2.max_point.x - shape1.min_point.x)
    overlap_y = min(shape1.max_point.y - shape2.min_point.y,
                   shape2.max_point.y - shape1.min_point.y)

    if overlap_x < overlap_y:
        normal = Vector2(1, 0) if shape1.center.x < shape2.center.x else Vector2(-1, 0)
        return (overlap_x, normal)
    else:
        normal = Vector2(0, 1) if shape1.center.y < shape2.center.y else Vector2(0, -1)
        return (overlap_y, normal)
