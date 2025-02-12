from typing import Union, Tuple, Callable
import math
from .vector import Vector2
from .basic import clamp

def lerp_angle_rad(start: float, end: float, t: float) -> float:
    """
    Interpolate between two angles (in radians) taking the shortest path.
    """
    diff = ((end - start + math.pi) % (2 * math.pi)) - math.pi
    return start + diff * clamp(t)

def lerp_angle_deg(start: float, end: float, t: float) -> float:
    """
    Interpolate between two angles (in degrees) taking the shortest path.
    """
    diff = ((end - start + 180) % 360) - 180
    return start + diff * clamp(t)

def smooth_step(t: float) -> float:
    """Smooth step interpolation (3t² - 2t³)."""
    t = clamp(t)
    return t * t * (3 - 2 * t)

def smoother_step(t: float) -> float:
    """Smoother step interpolation (6t⁵ - 15t⁴ + 10t³)."""
    t = clamp(t)
    return t * t * t * (t * (t * 6 - 15) + 10)

def slerp(start: Vector2, end: Vector2, t: float) -> Vector2:
    """
    Spherical linear interpolation between two vectors.
    Maintains constant angular velocity.
    """
    dot = start.dot(end)
    dot = clamp(dot, -1.0, 1.0)
    theta = math.acos(dot)
    
    if abs(theta) < 1e-6:
        return start.lerp(end, t)
    
    sin_theta = math.sin(theta)
    return (start * math.sin((1 - t) * theta) + 
            end * math.sin(t * theta)) / sin_theta
