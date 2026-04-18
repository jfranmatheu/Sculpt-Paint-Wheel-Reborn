from math import exp
from mathutils import Vector
import bmesh
from bmesh.types import BMFace, BMVert

from .snap import snap_verts_to_closest_object


# --------------------------------------------------
# Utils
# --------------------------------------------------

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
# Solver
# --------------------------------------------------

class QuadRetopoRelaxSolver:
    """
    Stable tangential Laplacian relax solver for retopology.
    Region boundary is HARD pinned → no shrink.
    """

    def __init__(self, bm: bmesh.types.BMesh):
        self.bm = bm

        # Hard pins: mesh boundary + poles
        self.hard_pinned: set[BMVert] = {
            v for v in bm.verts
            if v.is_boundary or len(v.link_edges) != 4
        }

    # --------------------------------------------------

    def relax_step(
        self,
        verts: set[BMVert],
        faces: set[BMFace],
        center: Vector,
        strength: float
    ):
        dists = {v: (v.co - center).length for v in verts}
        max_dist = max(dists.values()) if dists else 0.0
        if max_dist == 0.0:
            return

        # HARD region boundary pins
        region_boundary = detect_region_boundary_verts(faces)

        deltas: dict[BMVert, Vector] = {}

        for v in verts:
            if v in self.hard_pinned:
                continue
            if v in region_boundary:
                continue  # THIS IS THE FIX

            neigh = [
                e.other_vert(v)
                for e in v.link_edges
                if e.other_vert(v) in verts
            ]
            if not neigh:
                continue

            # Laplacian
            avg = Vector()
            for n in neigh:
                avg += n.co
            avg /= len(neigh)

            delta = avg - v.co

            # Tangential projection
            nrm = v.normal
            delta -= nrm * delta.dot(nrm)

            # Distance falloff
            t = dists[v] / max_dist
            falloff = exp(-(t * t) * 4.0)

            deltas[v] = delta * strength * falloff

        for v, d in deltas.items():
            v.co += d

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def smooth(
        self,
        context,
        face: BMFace,
        rings: int,
        strength: float,
        iterations: int = 1,
        snap: bool = True
    ):
        faces = collect_faces_topologically(face, rings)
        verts = {v for f in faces for v in f.verts}

        center = Vector()
        for v in face.verts:
            center += v.co
        center /= len(face.verts)

        for _ in range(iterations):
            self.relax_step(
                verts=verts,
                faces=faces,
                center=center,
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
