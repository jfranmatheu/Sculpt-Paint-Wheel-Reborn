from typing import Tuple, List
from math import dist
from ..vector import Vector2
from .shapes import Circle, Rectangle, Triangle


Point2D = Tuple[float, float]

def point_to_point(p1: Point2D, p2: Point2D) -> float:
    """Calculate distance between two 2D points."""
    return dist(p1, p2) 
    return hypot(p1[0] - p2[0], p1[1] - p2[1])
    return ((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)**0.5

def point_to_line(point: Point2D, line_start: Point2D, line_end: Point2D) -> float:
    """Calculate shortest distance from point to line segment."""
    # Implementation here
    pass

def point_to_line_segment(point: Vector2, line_start: Vector2, line_end: Vector2) -> float:
    """Calculate shortest distance from point to line segment"""
    line_vec = line_end - line_start
    point_vec = point - line_start
    line_length = line_vec.length()
    
    if line_length == 0:
        return point_vec.length()
    
    t = max(0, min(1, point_vec.dot(line_vec) / (line_length * line_length)))
    projection = line_start + line_vec * t
    return point.distance_to(projection)

def point_to_polygon(point: Vector2, vertices: List[Vector2]) -> float:
    """Calculate shortest distance from point to polygon boundary"""
    min_dist = float('inf')
    for i in range(len(vertices)):
        dist = point_to_line_segment(point, vertices[i], 
                                   vertices[(i + 1) % len(vertices)])
        min_dist = min(min_dist, dist)
    return min_dist

def rect_to_rect(rect1: Rectangle, rect2: Rectangle) -> float:
    """Calculate shortest distance between two rectangles (0 if intersecting)"""
    x_overlap = max(0, min(rect1.max_point.x, rect2.max_point.x) - 
                      max(rect1.min_point.x, rect2.min_point.x))
    y_overlap = max(0, min(rect1.max_point.y, rect2.max_point.y) - 
                      max(rect1.min_point.y, rect2.min_point.y))
    
    if x_overlap > 0 and y_overlap > 0:
        return 0
    
    if x_overlap > 0:
        return min(abs(rect1.max_point.y - rect2.min_point.y),
                  abs(rect1.min_point.y - rect2.max_point.y))
    if y_overlap > 0:
        return min(abs(rect1.max_point.x - rect2.min_point.x),
                  abs(rect1.min_point.x - rect2.max_point.x))
    
    # No overlap in either direction - find closest corners
    corners1 = rect1.corners
    corners2 = rect2.corners
    min_dist = float('inf')
    for c1 in corners1:
        for c2 in corners2:
            dist = c1.distance_to(c2)
            min_dist = min(min_dist, dist)
    return min_dist
