from typing import Union, Tuple
import math
from .vector import Vector2

def degrees_to_radians(degrees: float) -> float:
    """Convert degrees to radians."""
    return degrees * math.pi / 180.0

def radians_to_degrees(radians: float) -> float:
    """Convert radians to degrees."""
    return radians * 180.0 / math.pi

def normalize_angle_degrees(degrees: float) -> float:
    """Normalize angle to range [-180, 180]."""
    degrees = degrees % 360.0
    if degrees > 180.0:
        degrees -= 360.0
    return degrees

def normalize_angle_radians(radians: float) -> float:
    """Normalize angle to range [-π, π]."""
    return math.atan2(math.sin(radians), math.cos(radians))

def angle_difference_degrees(a: float, b: float) -> float:
    """Get the smallest difference between two angles in degrees."""
    diff = (b - a) % 360.0
    if diff > 180.0:
        diff -= 360.0
    return diff

def angle_difference_radians(a: float, b: float) -> float:
    """Get the smallest difference between two angles in radians."""
    diff = (b - a) % (2 * math.pi)
    if diff > math.pi:
        diff -= 2 * math.pi
    return diff
