
from mathutils import Vector


def segments_intersect(p1, p2, p3, p4) -> Vector | None:
    # Credits: https://gist.github.com/kylemcdonald/6132fc1c29fd3767691442ba4bc84018
    x1,y1 = p1
    x2,y2 = p2
    x3,y3 = p3
    x4,y4 = p4
    denom = (y4-y3)*(x2-x1) - (x4-x3)*(y2-y1)
    if denom == 0: # parallel
        return None
    ua = ((x4-x3)*(y1-y3) - (y4-y3)*(x1-x3)) / denom
    if ua < 0 or ua > 1: # out of range
        return None
    ub = ((x2-x1)*(y1-y3) - (y2-y1)*(x1-x3)) / denom
    if ub < 0 or ub > 1: # out of range
        return None
    x = x1 + ua * (x2-x1)
    y = y1 + ua * (y2-y1)
    return Vector((x,y))

def path_self_intersects(pts, return_intersection_point=False) -> bool | Vector | None:
    """Check if a path self-intersects.

    Args:
        pts (list of Vector): The path points.
        return_intersection_point (bool, optional): Whether to return the intersection point. Defaults to False.

    Returns:
        bool | Vector | None: True if the path self-intersects, False otherwise. If return_intersection_point is True,
        the intersection point is returned.
    """
    # basta con detectar cruce de segmentos no consecutivos
    for i in range(len(pts)-3):
        for j in range(i+2, len(pts)-1):
            if (intersect_point := segments_intersect(pts[i], pts[i+1], pts[j], pts[j+1])) is not None:
                if return_intersection_point:
                    return intersect_point
                return True
    return None if return_intersection_point else False 

def segment_intersection_2d(a: Vector, b: Vector, c: Vector, d: Vector, eps=1e-6) -> Vector | None:
    r = b - a
    s = d - c
    denom = r.cross(s)

    if abs(denom) < eps:
        return None

    t = (c - a).cross(s) / denom
    u = (c - a).cross(r) / denom

    if eps < t < 1.0 - eps and eps < u < 1.0 - eps:
        return a + t * r

    return None
