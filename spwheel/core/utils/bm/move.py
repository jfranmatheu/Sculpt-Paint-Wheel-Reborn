from math import exp
import bmesh
from mathutils import Vector
from bmesh.types import BMFace, BMVert

from ..falloff import FalloffType
from .snap import snap_verts_to_closest_object


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


def mouse_offset_to_3d(
    context,
    face: BMFace,
    mouse_offset_2d: Vector
) -> Vector:
    rv3d = context.region_data

    view_right = rv3d.view_rotation @ Vector((1, 0, 0))
    view_up    = rv3d.view_rotation @ Vector((0, 1, 0))

    move_3d = (
        view_right * mouse_offset_2d.x +
        view_up    * mouse_offset_2d.y
    )

    # Project onto face tangent plane
    n = face.normal.normalized()
    move_3d -= n * move_3d.dot(n)

    return move_3d


class QuadRetopoMoveTool:
    """
    Absolute move tool with smooth area influence.
    Fully reversible (no drift).
    """

    def __init__(self, bm: bmesh.types.BMesh):
        self.bm = bm

        self.hard_pinned: set[BMVert] = {
            v for v in bm.verts
            if v.is_boundary or len(v.link_edges) != 4
        }

        # Cached per action
        self.start_mouse: Vector | None = None
        self.start_positions: dict[BMVert, Vector] = {}
        self.faces: set[BMFace] = set()
        self.verts: set[BMVert] = set()
        self.face: BMFace | None = None

    # --------------------------------------------------
    # Call ONCE on mouse press
    # --------------------------------------------------

    def begin(
        self,
        context,
        face: BMFace,
        rings: int,
        mouse_pos: Vector,
        falloff_type: FalloffType = FalloffType.SHARP
    ):
        self.falloff = falloff_type

        self.face = face
        self.start_mouse = mouse_pos.copy()

        self.faces = collect_faces_topologically(face, rings)
        self.verts = {v for f in self.faces for v in f.verts}

        # Cache original vertex positions
        self.start_positions = {
            v: v.co.copy()
            for v in self.verts
        }

    # --------------------------------------------------
    # Call on every mouse move
    # --------------------------------------------------

    def update(
        self,
        context,
        mouse_pos: Vector,
        strength: float = 1.0,
        snap: bool = True
    ):
        print(f"QuadRetopoMoveTool.update: {mouse_pos} {strength} {snap}")
        strength = strength * 0.001
        
        if self.start_mouse is None or self.face is None:
            return

        # Absolute mouse offset
        mouse_offset = mouse_pos - self.start_mouse

        move_vec = mouse_offset_to_3d(
            context,
            self.face,
            mouse_offset
        )

        center = sum((v.co for v in self.face.verts), Vector()) / len(self.face.verts)

        dists = {v: (self.start_positions[v] - center).length for v in self.verts}
        max_dist = max(dists.values()) if dists else 0.0
        if max_dist == 0.0:
            return

        region_boundary = detect_region_boundary_verts(self.faces)

        for v in self.verts:
            if v in self.hard_pinned or v in region_boundary:
                v.co = self.start_positions[v]
                continue

            t = dists[v] / max_dist
            # falloff = exp(-(t * t) * 4.0)
            falloff = self.falloff.evaluate(t)

            v.co = (
                self.start_positions[v] +
                move_vec * strength * falloff
            )

        if snap:
            snap_verts_to_closest_object(
                context=context,
                mesh_object=context.edit_object,
                verts=self.verts
            )

        bmesh.update_edit_mesh(
            context.edit_object.data,
            loop_triangles=False,
            destructive=False
        )

    # --------------------------------------------------
    # Call on mouse release
    # --------------------------------------------------

    def end(self):
        self.start_mouse = None
        self.start_positions.clear()
        self.faces.clear()
        self.verts.clear()
        self.face = None
