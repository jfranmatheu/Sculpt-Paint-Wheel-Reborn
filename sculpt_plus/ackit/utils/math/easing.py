from typing import Callable
from .basic import clamp

def ease_linear(t: float) -> float:
    """Linear interpolation."""
    return clamp(t)

def ease_in_quad(t: float) -> float:
    """Quadratic ease in."""
    t = clamp(t)
    return t * t

def ease_out_quad(t: float) -> float:
    """Quadratic ease out."""
    t = clamp(t)
    return -t * (t - 2)
