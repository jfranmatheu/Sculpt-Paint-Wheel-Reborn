

from mathutils import Vector


def interpolate_linear(a: Vector, b: Vector, t: float) -> Vector:
    return a.lerp(b, t)

def interpolate_quadratic(a: Vector, b: Vector, c: Vector, t: float) -> Vector:
    return a.lerp(b, t).lerp(c, t)
