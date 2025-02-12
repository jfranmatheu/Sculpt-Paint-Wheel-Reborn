from typing import Optional, Tuple, List
from ..vector import Vector2
from .shapes import Circle, Rectangle, Triangle, Polygon
from .bounds import BoundingBox2D

Point2D = Tuple[float, float]

def point_in_rect(point: Point2D, rect_min: Point2D, rect_max: Point2D) -> bool:
    """Check if point is inside rectangle defined by min/max points."""
    return (rect_min[0] <= point[0] <= rect_max[0] and 
            rect_min[1] <= point[1] <= rect_max[1])

def line_line_intersection(a1: Vector2, a2: Vector2, b1: Vector2, b2: Vector2) -> Optional[Vector2]:
    """Returns intersection point of two line segments, or None if they don't intersect"""
    den = (b2.y - b1.y) * (a2.x - a1.x) - (b2.x - b1.x) * (a2.y - a1.y)
    
    if abs(den) < 1e-6:  # Lines are parallel
        return None

    ua = ((b2.x - b1.x) * (a1.y - b1.y) - (b2.y - b1.y) * (a1.x - b1.x)) / den
    ub = ((a2.x - a1.x) * (a1.y - b1.y) - (a2.y - a1.y) * (a1.x - b1.x)) / den

    if 0 <= ua <= 1 and 0 <= ub <= 1:
        return Vector2(
            a1.x + ua * (a2.x - a1.x),
            a1.y + ua * (a2.y - a1.y)
        )
    return None

def circle_circle_intersection(c1: Circle, c2: Circle) -> bool:
    """Check if two circles intersect"""
    return c1.center.distance_to(c2.center) <= c1.radius + c2.radius

def rect_rect_intersection(r1: Rectangle, r2: Rectangle) -> bool:
    """Check if two rectangles intersect"""
    return not (r1.max_point.x < r2.min_point.x or
                r1.min_point.x > r2.max_point.x or
                r1.max_point.y < r2.min_point.y or
                r1.min_point.y > r2.max_point.y)

def circle_rect_intersection(circle: Circle, rect: Rectangle) -> bool:
    """Check if a circle and rectangle intersect"""
    # Find closest point on rectangle to circle center
    closest_x = max(rect.min_point.x, min(circle.center.x, rect.max_point.x))
    closest_y = max(rect.min_point.y, min(circle.center.y, rect.max_point.y))
    closest_point = Vector2(closest_x, closest_y)

    # Check if closest point is within circle radius
    return circle.center.distance_to(closest_point) <= circle.radius
