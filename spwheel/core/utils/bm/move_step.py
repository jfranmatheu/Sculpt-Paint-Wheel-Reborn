from math import exp
from mathutils import Vector
import bmesh
from bmesh.types import BMFace, BMVert

from .snap import snap_verts_to_closest_object


# --------------------------------------------------
# Utils
# --------------------------------------------------

def mouse_delta_to_3d(
    context,
    face: BMFace,
    mouse_delta_2d: Vector
) -> Vector:
    """
    Converts 2D mouse movement to a 3D vector projected
    onto the face tangent plane.
    """

    rv3d = context.region_data

    # View right & up vectors (camera space)
    view_right = rv3d.view_rotation @ Vector((1, 0, 0))
    view_up    = rv3d.view_rotation @ Vector((0, 1, 0))

    # Screen-space movement → world-space
    move_3d = (
        view_right * mouse_delta_2d.x +
        view_up    * mouse_delta_2d.y
    )

    # Project onto face tangent plane
    n = face.normal.normalized()
    move_3d -= n * move_3d.dot(n)

    return move_3d


def collect_faces_topologically(start_face: BMFace, rings: int) -> set[BMFace]:
    visited = {start_face}
    frontier = {start_face}

    for _ in range(rings):
        nxt = set()
        for f in frontier:
            for e in f.edges:
                for lf in e.link_faces:
                    if lf not in visited:
                        visited.add(lf)
                        nxt.add(lf)
        frontier = nxt

    return visited


def detect_region_boundary_verts(faces: set[BMFace]) -> set[BMVert]:
    face_set = set(faces)
    boundary_verts = set()

    for f in faces:
        for v in f.verts:
            for e in v.link_edges:
                for lf in e.link_faces:
                    if lf not in face_set:
                        boundary_verts.add(v)
                        break
    return boundary_verts


# --------------------------------------------------
# Move Tool Solver
# --------------------------------------------------

class QuadRetopoMoveTool:
    """
    Move tool with smooth area influence.
    - Pins boundary & poles.
    - Applies falloff based on distance from center.
    - Movement vector is defined by mouse direction and distance.
    """

    def __init__(self, bm: bmesh.types.BMesh):
        self.bm = bm

        # Hard pins: mesh boundary + poles
        self.hard_pinned: set[BMVert] = {
            v for v in bm.verts
            if v.is_boundary or len(v.link_edges) != 4
        }

    def move_step(
        self,
        verts: set[BMVert],
        faces: set[BMFace],
        center: Vector,
        move_vector: Vector,
        strength: float
    ):
        dists = {v: (v.co - center).length for v in verts}
        max_dist = max(dists.values()) if dists else 0.0
        if max_dist == 0.0:
            return

        region_boundary = detect_region_boundary_verts(faces)
        moves: dict[BMVert, Vector] = {}

        for v in verts:
            if v in self.hard_pinned or v in region_boundary:
                continue  # pinned

            # Distance-based falloff
            t = dists[v] / max_dist
            falloff = exp(-(t * t) * 4.0)

            moves[v] = move_vector * strength * falloff

        for v, m in moves.items():
            v.co += m

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def move(
        self,
        context,
        face: BMFace,
        rings: int,
        mouse_delta: Vector,
        strength: float = 1.0,
        snap: bool = True
    ):
        strength = strength * 0.0001

        faces = collect_faces_topologically(face, rings)
        verts = {v for f in faces for v in f.verts}

        # Center of region
        center = Vector()
        for v in face.verts:
            center += v.co
        center /= len(face.verts)

        move_vec_3d = mouse_delta_to_3d(
            context,
            face,
            mouse_delta
        )

        self.move_step(
            verts=verts,
            faces=faces,
            center=center,
            move_vector=move_vec_3d,
            strength=strength
        )

        if snap:
            snap_verts_to_closest_object(
                context=context,
                mesh_object=context.edit_object,
                verts=verts
            )

        bmesh.update_edit_mesh(context.edit_object.data, loop_triangles=False, destructive=False)

        return verts
