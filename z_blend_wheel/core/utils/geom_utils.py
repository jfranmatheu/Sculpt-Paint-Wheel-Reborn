from math import cos, pi, sin
from typing import Tuple
import numpy as np

from bmesh.types import BMFace
from bpy.types import Object, Context
from mathutils import Vector
from mathutils.geometry import intersect_point_line, intersect_line_line_2d, intersect_point_quad_2d

from .math_utils import normalize
from .raycast_utils import get_view_vector


def is_face_facing_view(context: Context, obj: Object, bm_face: BMFace):
    rv3d = context.region_data

    # World-space face center and normal
    mw = obj.matrix_world
    face_normal = (mw.to_quaternion() @ bm_face.normal).normalized()

    if rv3d.view_perspective in {'PERSP', 'CAMERA'}:
        face_center = mw @ bm_face.calc_center_median()

        # Get view position (eye point)
        if rv3d.view_perspective == 'CAMERA' and context.scene.camera:
            view_pos = context.scene.camera.matrix_world.to_translation()
        else:
            view_pos = rv3d.view_location

        # Vector from face center to view position
        vec_to_view = (view_pos - face_center).normalized()

        # Dot product > 0 means normal points towards viewer
        return vec_to_view.dot(face_normal) > 0

    else:  # ORTHO
        # View looking direction (into the scene)
        view_dir = (rv3d.view_rotation @ Vector((0.0, 0.0, -1.0))).normalized()
        # Direction towards viewer is opposite
        dir_to_view = -view_dir

        return dir_to_view.dot(face_normal) > 0

def is_face_facing_view_vector(context: Context, obj: Object, bm_face: BMFace, region_coord: Vector):
    # Normal de la cara en mundo
    mw = obj.matrix_world
    face_normal = (mw.to_quaternion() @ bm_face.normal).normalized()

    # View vector desde la posición en pantalla (apunta hacia la escena)
    view_vector = get_view_vector(context, region_coord)

    # Dirección hacia el observador = opuesta al view vector
    towards_viewer = -view_vector

    # Si dot > 0 → el normal apunta hacia el observador
    return face_normal.dot(towards_viewer) > 0



def dist_to_segment(p: Vector, a: Vector, b: Vector) -> float:
    closest, percent = intersect_point_line(p, a, b)
    if percent < 0:
        return (p - a).length
    elif percent > 1:
        return (p - b).length
    else:
        return (p - closest).length

def closest_point_to_segment(segment_start: Vector, segment_end: Vector, points: list[Vector]) -> Tuple[int, float]:
    """ Get the index and distance of the closest point to the segment. """
    min_distance = float('inf')
    index = -1
    for i, point in enumerate(points):
        d = dist_to_segment(point, segment_start, segment_end)
        if d < min_distance:
            min_distance = d
            index = i
    return index, min_distance

def closest_point_on_segment(segment_start: Vector, segment_end: Vector, point: Vector) -> Vector | None:
    """ Get the closest point on the segment to the given point. """
    if not segment_start or not segment_end:
        return None
    if segment_start == segment_end:
        return segment_start
    closest, percent = intersect_point_line(point, segment_start, segment_end)
    # percent is the distance from the segment start to the closest point on segment as a percentage of the segment length
    if percent < 0:
        return segment_start
    elif percent > 1:
        return segment_end
    else:
        return closest

def closest_segment_to_point(point: Vector, segments: list[Tuple[Vector, Vector]], get_closest_point: bool = False) -> Tuple[int, float] | Tuple[int, float, Vector]:
    """ Get the index and distance of the closest segment to the point. """
    min_distance = float('inf')
    index = -1
    for i, segment in enumerate(segments):
        d = dist_to_segment(point, segment[0], segment[1])
        if d < min_distance:
            min_distance = d
            index = i
    if get_closest_point:
        closest_segment = segments[index]
        return index, min_distance, closest_point_on_segment(closest_segment[0], closest_segment[1], point)
    else:
        return index, min_distance

def plane_basis(normal: Vector) -> Tuple[Vector, Vector, Vector]:
    N = normal.normalized()

    # Elegir un vector que no sea paralelo a N
    if abs(N[0]) < 0.9:
        arbitrary = Vector((1.0, 0.0, 0.0))
    else:
        arbitrary = Vector((0.0, 1.0, 0.0))

    U = N.cross(arbitrary).normalized()
    V = N.cross(U)

    return U, V, N

def plane_project_point_3d_to_2d(P: Vector, P0: Vector, U: Vector, V: Vector) -> Vector:
    """
    P  : punto 3D
    P0 : origen del plano
    U,V: ejes del plano
    """
    d = P - P0
    x = d.dot(U)
    y = d.dot(V)
    return Vector((x, y))


def plane_project_point_2d_to_3d(p2d: Vector, P0: Vector, U: Vector, V: Vector) -> Vector:
    """
    p2d: coordenadas 2D (x, y)
    """
    return P0 + p2d[0] * U + p2d[1] * V


class CM_PlaneProject:
    """Class to project points between 3D and 2D on a plane.
    """
    plane_co: Vector = None
    plane_no: Vector = None

    def __init__(self, plane_co: Vector, plane_no: Vector):
        self.plane_co = plane_co
        self.U, self.V, self.plane_no = plane_basis(plane_no)

    def point_3d_to_2d(self, P: Vector) -> Vector:
        return plane_project_point_3d_to_2d(P, self.plane_co, self.U, self.V)

    def point_2d_to_3d(self, p2d: Vector) -> Vector:
        return plane_project_point_2d_to_3d(p2d, self.plane_co, self.U, self.V)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass


def get_n_points_around(center: Vector | tuple[float, float] | list[float], r: float, N: int, angle_offset: float = 0.0) -> list[Vector]:
    # Keep the ring generation in the same dimensionality as the input to avoid
    # Vector dimension mismatches (mouse coords are 2D for view2D raycasts).
    center_vec = Vector(center) if isinstance(center, (tuple, list)) else center.copy()
    dims = len(center_vec)
    if dims not in (2, 3):
        raise ValueError(f"points_around only supports 2D or 3D vectors, got {dims}D")
    points = []
    for i in range(N):
        angle = i * 2 * pi / N + angle_offset
        offset = Vector((cos(angle) * r, sin(angle) * r)) if dims == 2 else Vector((cos(angle) * r, sin(angle) * r, 0))
        points.append(center_vec + offset)
    return points
