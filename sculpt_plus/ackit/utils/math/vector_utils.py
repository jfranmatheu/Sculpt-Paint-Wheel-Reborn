from typing import Union, Tuple
import math
from .vector import Vector2
from .angles import normalize_angle_radians, normalize_angle_degrees


def angle_between_vectors(v1: Vector2, v2: Vector2, signed: bool = True) -> float:
    """
    Calculate angle between two vectors in radians.
    If signed is True, returns signed angle (-π to π).
    If signed is False, returns unsigned angle (0 to π).
    """
    if signed:
        return math.atan2(v1.cross(v2), v1.dot(v2))
    else:
        return math.acos(
            max(-1.0, min(1.0, v1.dot(v2) / (v1.length() * v2.length())))
        )

def angle_between_vectors_degrees(v1: Vector2, v2: Vector2, signed: bool = True) -> float:
    """Calculate angle between two vectors in degrees."""
    return math.degrees(angle_between_vectors(v1, v2, signed))

def vector_from_angle(angle_rad: float, length: float = 1.0) -> Vector2:
    """Create a vector from an angle (in radians) and length."""
    return Vector2(math.cos(angle_rad) * length, math.sin(angle_rad) * length)

def vector_from_angle_degrees(angle_deg: float, length: float = 1.0) -> Vector2:
    """Create a vector from an angle (in degrees) and length."""
    return vector_from_angle(math.radians(angle_deg), length)

def perpendicular(vector: Vector2, clockwise: bool = True) -> Vector2:
    """Get perpendicular vector (90-degree rotation)."""
    if clockwise:
        return Vector2(vector.y, -vector.x)
    return Vector2(-vector.y, vector.x)

def project_vector(v1: Vector2, v2: Vector2) -> Vector2:
    """Project v1 onto v2."""
    v2_normalized = v2.normalized()
    return v2_normalized * v1.dot(v2_normalized)
