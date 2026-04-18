from collections import defaultdict
from math import atan2, dist, cos, radians, sin, pi
from typing import Callable, Literal
from dataclasses import dataclass

import bpy
from bpy.types import Context, Mesh, Object, RegionView3D
import bmesh
from bmesh.types import BMEdge, BMFace, BMVert, BMesh
from mathutils import Matrix, Vector, kdtree
from bpy_extras.view3d_utils import region_2d_to_location_3d
from mathutils.geometry import intersect_line_line_2d

from .math_utils import angle_v3v3, angle_signed

from .geometry.shapely import union_bmvert_boundaries_2d
from .raycast_utils import BVHTreeRaycaster, raycast_scene
from .view_utils import location_3d_to_region_2d, is_vector_pointing_away_from_view, get_view_vector
from .geom_utils import CM_PlaneProject, plane_basis, dist_to_segment
from .geometry.interpolate import interpolate_linear
from .geometry.intersect import segment_intersection_2d
from .bm.shortest_path import get_edge_loop_between_verts


def remove_duplicates_keep_order(items: list) -> list:
    """Remove duplicates from a list while keeping the original order."""
    seen = set()
    return [
        item
        for item in items
        if not (item in seen or seen.add(item))
    ]


# MARK: Adjacency

def face_face_adjacent(f1: BMFace, f2: BMFace) -> bool:
    """Check if two faces are adjacent to each other."""
    return any(
        e in f2.edges
        for e in f1.edges
    )

def edge_edge_adjacent(e1: BMEdge, e2: BMEdge) -> bool:
    """Check if two edges are adjacent to each other."""
    return any(
        v in e2.verts
        for v in e1.verts
    )


def build_edge_adjacency(edges: set[BMEdge]) -> dict[BMVert, set[BMEdge]]:
    adj = defaultdict(set)
    for e in edges:
        v1, v2 = e.verts
        adj[v1].add(e)
        adj[v2].add(e)
    return adj

build_edge_graph = build_edge_adjacency


# -----------------------------------------------------------------------------------------


def split_edge_at_point(bm: bmesh.types.BMesh, edge: BMEdge, point: Vector) -> BMVert:
    res = bmesh.ops.subdivide_edges(
        bm,
        edges=[edge],
        cuts=1,
        use_grid_fill=False
    )

    new_verts = [
        v for v in res["geom_split"]
        if isinstance(v, BMVert)
    ]

    new_vert = min(
        new_verts,
        key=lambda v: (v.co - point).length
    )

    new_vert.co = point
    return new_vert


def extract_closed_loop(start_vert: BMVert, edges: set[BMEdge]) -> list[BMVert] | None:
    adj = build_edge_adjacency(edges)

    loop = [start_vert]
    current = start_vert
    prev_edge = None

    while True:
        candidates = [
            e for e in adj[current]
            if e != prev_edge
        ]
        if not candidates:
            return None

        edge = candidates[0]
        next_vert = edge.other_vert(current)

        if next_vert == start_vert:
            break

        loop.append(next_vert)
        prev_edge = edge
        current = next_vert

    return loop


#MARK: Vertex Finder
class VertexFinder:
    """
    Finds vertices in a Blender mesh using a KDTree.
    Recommended to use as a context manager, the return value will be the find method.
    """
    bm: BMesh
    kd: kdtree.KDTree | None
    type: Literal['2D', '3D', 'HYBRID']
    v_filter: Callable[[BMVert], bool] | None
    is_valid: bool

    def __init__(self, bm: BMesh, type: Literal['2D', '3D', 'HYBRID'], v_filter=None):
        if bm is None or not bm.is_valid:
            raise ValueError("VertexFinder: input BMesh is None or invalid")
        self.bm = bm
        self.kd = None
        self.type = type
        self.v_filter = v_filter
        self.is_valid = True
        bm.verts.ensure_lookup_table()
        bm.verts.index_update()

    @classmethod
    def create_kdtree_from_bmesh_verts(cls, context: Context, bm: BMesh, type: Literal['2D', '3D'], v_filter=None) -> kdtree.KDTree:
        obj = context.edit_object if context.mode == 'EDIT_MESH' else context.active_object
        mw = obj.matrix_world if obj is not None else Matrix.Identity(4)
        kd = kdtree.KDTree(len(bm.verts))
        if type == '3D':
            for i, v in enumerate(bm.verts):
                if v_filter is not None and not v_filter(v):
                    continue
                kd.insert(mw @ v.co, i)
        else:
            for i, v in enumerate(bm.verts):
                if v_filter is not None and not v_filter(v):
                    continue
                if co_2d := location_3d_to_region_2d(context.region, context.region_data, mw @ v.co, default=None):
                    kd.insert(co_2d, i)
        kd.balance()
        return kd

    def _setup_kdtree(self, context: Context):
        if self.bm is None or not self.bm.is_valid:
            self.bm = bmesh.from_edit_mesh(context.edit_object.data)
        if self.kd is None:
            self.kd = VertexFinder.create_kdtree_from_bmesh_verts(context, self.bm, '3D' if self.type in {'3D', 'HYBRID'} else '2D', v_filter=self.v_filter)

    def _find(self, context: Context, location: Vector, dist: float = 0.1):
        self._setup_kdtree(context)
        if self.kd is None:
            return None
        if len(location) == 2:
            result = raycast_scene(context, location)
            if result is None:
                return None
            location = result.location
        closest_co, index, hit_dist = self.kd.find(location)
        if hit_dist is None or hit_dist > dist:
            ## print("VertexFinder.find: closest_point_on_mesh too away from hit location")
            return None
        # Finally, return the closest vert in the bmesh.
        try:
            return self.bm.verts[index]
        except IndexError:
            self.bm = None
            self.kd = None
            self.is_valid = False
            return None

    def _find_hybrid(self, context: Context, location_2d: Vector, location_3d: Vector | None = None, dist_2d: float = 10, dist_3d: float = 0.1) -> BMVert | None:
        self._setup_kdtree(context)
        if self.bm is None or not self.bm.is_valid:
            return None
        if self.kd is None:
            return None
        if location_3d is None:
            raycast_info = raycast_scene(context, location_2d)
            if raycast_info is None or not raycast_info.hit:
                return None
            location_3d = raycast_info.location
        closest_co, index, hit_dist = self.kd.find(location_3d)
        if hit_dist is None:
            return None
        if hit_dist > dist_3d:
            print("VertexFinder.find: closest_point_on_mesh too away from hit location")
            return None
        projected_co_2d = location_3d_to_region_2d(context.region, context.region_data, closest_co, default=None)
        if projected_co_2d is None:
            return None
        if dist(projected_co_2d, location_2d) > dist_2d:
            print("VertexFinder.find: hit-projected location_2d too away from input location_2d")
            return None
        # Finally, return the closest vert in the bmesh.
        try:
            return self.bm.verts[index]
        except IndexError:
            self.bm = None
            self.kd = None
            self.is_valid = False
            return None

    def __enter__(self):
        if self.type == 'HYBRID':
            return self._find_hybrid
        else:
            return self._find

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.kd = None
        
    def __del__(self):
        self.kd = None


class EdgeFinder:
    """
    Finds edges in a Blender mesh using a 2D KDTree of midpoints and 2D distance to segment filtering.
    Recommended to use as a context manager, the return value will be the find method.
    """
    bm: BMesh
    kd: kdtree.KDTree | None
    e_filter: Callable[[BMEdge], bool] | None
    is_valid: bool

    def __init__(self, bm: BMesh, samples: int = 5, e_filter=None):
        if bm is None or not bm.is_valid:
            raise ValueError("EdgeFinder: input BMesh is None or invalid")
        self.bm = bm
        self.kd = None
        self.e_filter = e_filter
        self.is_valid = True
        self.sample_count = samples
        bm.edges.ensure_lookup_table()
        bm.edges.index_update()

    @classmethod
    def create_kdtree_from_bmesh_edges(cls, context: Context, bm: BMesh, edge_samples=3, edge_corner_factor=0.092, e_filter=None) -> kdtree.KDTree:
        obj = context.edit_object if context.mode == 'EDIT_MESH' else context.active_object
        mw = obj.matrix_world if obj is not None else Matrix.Identity(4)
        kd = kdtree.KDTree(len(bm.edges))
        
        for i, e in enumerate(bm.edges):
            if e_filter is not None and not e_filter(e):
                continue
            if edge_samples == 1:
                # Calculate midpoint in 3D
                mid_3d = mw @ ((e.verts[0].co + e.verts[1].co) / 2.0)
                kd.insert(mid_3d, i)
            else:
                # Samples along edge.
                edge_start = mw @ e.verts[0].co
                edge_end = mw @ e.verts[1].co
                edge_startend = edge_start - edge_end
                edge_a = edge_start + edge_startend.length * edge_corner_factor
                edge_b = edge_end - edge_startend.length * edge_corner_factor
                edge_ab = edge_a - edge_b
                for j in range(edge_samples):
                    kd.insert(edge_a + edge_ab * j / (edge_samples - 1) * (1.0 - edge_samples), i)

        kd.balance()
        return kd

    def _setup_kdtree(self, context: Context):
        if self.bm is None or not self.bm.is_valid:
            self.bm = bmesh.from_edit_mesh(context.edit_object.data)
        if self.kd is None:
            self.kd = EdgeFinder.create_kdtree_from_bmesh_edges(context, self.bm, edge_samples=self.sample_count, e_filter=self.e_filter)

    def _find(self, context: Context, location_2d: Vector, max_dist_2d: float = 20.0, search_n: int = 6) -> BMEdge | None:
        """
        Find the closest edge to a 2D mouse location by searching nearest 3D midpoints,
        then filtering by 2D projected distance.
        """
        self._setup_kdtree(context)
        if self.kd is None:
            return None
            
        raycast_info = raycast_scene(context, location_2d)
        if raycast_info is None or not raycast_info.hit:
            return None
        location_3d = raycast_info.location
            
        obj = context.edit_object if context.mode == 'EDIT_MESH' else context.active_object
        mw = obj.matrix_world if obj is not None else Matrix.Identity(4)
        
        # Search the N nearest midpoints in 3D
        nearest = self.kd.find_n(location_3d, search_n)
        
        best_edge = None
        best_dist = max_dist_2d
        
        for kd_co, index, kd_dist in nearest:
            try:
                edge = self.bm.edges[index]
            except IndexError:
                self.bm = None
                self.kd = None
                self.is_valid = False
                return None
                
            # Project edge vertices to 2D
            v1_3d = mw @ edge.verts[0].co
            v2_3d = mw @ edge.verts[1].co
            
            v1_2d = location_3d_to_region_2d(context.region, context.region_data, v1_3d, default=None)
            v2_2d = location_3d_to_region_2d(context.region, context.region_data, v2_3d, default=None)
            
            if v1_2d is None or v2_2d is None:
                continue
                
            # Calculate actual 2D distance to segment
            dist = dist_to_segment(location_2d, v1_2d, v2_2d)
            
            if dist < best_dist:
                best_dist = dist
                best_edge = edge
                
        return best_edge

    def __enter__(self):
        return self._find

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.kd = None
        
    def __del__(self):
        self.kd = None


def is_face_normal_away_from_view(context: Context | RegionView3D, face: BMFace) -> bool:
    """
    Checks if the normal of a face is pointing away from the view.
    
    Params:
    - context: The Blender context.
    - face: The face to check.
    
    Returns:
    - True if the face normal is pointing away from the view, False otherwise.
    """
    return is_vector_pointing_away_from_view(context.region_data if isinstance(context, Context) else context, face.normal)


def is_wire_or_boundary(prim: BMVert | BMEdge | BMFace) -> bool:
    """
    Checks if a vertex or edge or face is on a wire or boundary.
    
    Params:
    - prim: The vertex or edge or face to check.
    
    Returns:
    - True if the vertex or edge or face is on a wire or boundary, False otherwise.
    """
    if isinstance(prim, (BMVert, BMEdge)):
        return prim.is_wire or prim.is_boundary
    elif isinstance(prim, BMFace):
        return any([e.is_boundary for e in prim.edges])
    else:
        raise ValueError("is_wire_or_boundary: input must be a vertex or edge or face")


def get_boundary_edge_loop(prim: BMEdge, min_linked_edges: int = 3, max_linked_edges: int = 3, wire_walk: bool = False, face_walk_around: bool = False, limit_angle: float = 0.0, get_coords: bool = False) -> list[BMEdge] | tuple[list[BMEdge], list[Vector]]:
    """
    Finds the boundary edge loop starting from an edge.

    Params:
    - prim: The starting edge.
    - min_linked_edges: The min number of linked edges to follow.
    - max_linked_edges: The maximum number of linked edges to follow.
    - wire_walk: Whether to walk on wire edges.
    - face_walk_around: whether to walk around a face always that other edges are in the boundary.
    - limit_angle: angle to limit the edge loop selection. =0 means this feature is disabled.
    - get_coords: Whether to return the coordinates of the vertices in the loop, in order end to end of the edge loop itself.
    
    Returns:
    - A list of edges in the boundary loop.
    """
    use_limit_angle = limit_angle > 0.0
    def _coords_from_edges(edges: list[BMEdge]) -> list[Vector]:
        if not edges:
            return []
        if len(edges) == 1:
            v1, v2 = edges[0].verts
            return [v1.co.copy(), v2.co.copy()]
        def _walk_from_start(start_vert: BMVert) -> list[Vector] | None:
            coords: list[Vector] = [start_vert.co.copy()]
            current = start_vert
            for e in edges:
                if current not in e.verts:
                    return None
                current = e.other_vert(current)
                coords.append(current.co.copy())
            return coords
        e0, e1 = edges[0], edges[1]
        shared: BMVert | None = None
        for v in e0.verts:
            if v in e1.verts:
                shared = v
                break
        if shared is None:
            return _walk_from_start(e0.verts[0]) or _walk_from_start(e0.verts[1]) or []
        return _walk_from_start(e0.other_vert(shared)) or _walk_from_start(shared) or []
    def _walk_from(vert: BMVert, incoming: BMEdge, edges: set[BMEdge]) -> list[BMEdge]:
        path: list[BMEdge] = []
        current_vert = vert
        current_edge = incoming
        current_loop = incoming.link_loops[0] if len(incoming.link_loops) > 0 else None
        current_face: BMFace = incoming.link_faces[0] if len(incoming.link_faces) > 0 else None
        while True:
            lk_edges = current_vert.link_edges
            lk_edge_count = len(lk_edges)
            if lk_edge_count == 0 or lk_edge_count > max_linked_edges or lk_edge_count < min_linked_edges:
                break
            candidates: list[BMEdge] = []
            for e in lk_edges:
                if e == current_edge or e in edges:
                    continue
                if not (e.is_boundary or (wire_walk and e.is_wire)):
                    continue
                if face_walk_around and current_face is not None and e.link_faces and e.link_faces[0] == current_face:
                    continue
                if use_limit_angle and current_loop is not None and len(e.link_loops) > 0 and angle_signed(current_edge.calc_tangent(current_loop), e.calc_tangent(e.link_loops[0]), as_degrees=True) > limit_angle:
                    continue
                candidates.append(e)
            if len(candidates) != 1:
                break
            next_edge = candidates[0]
            edges.add(next_edge)
            path.append(next_edge)
            current_vert = next_edge.other_vert(current_vert)
            current_edge = next_edge
        return path
    walked_edges: set[BMEdge] = set([prim])
    a_vert, b_vert = prim.verts
    a_path = _walk_from(a_vert, prim, walked_edges)
    b_path = _walk_from(b_vert, prim, walked_edges)
    a_path.reverse()
    edge_loop = a_path + [prim] + b_path
    if get_coords:
        return (edge_loop, _coords_from_edges(edge_loop))
    return edge_loop


def walk_boundary(a_vert: BMVert, b_vert: BMVert, max_walk: int = 100, wire_walk: bool = False) -> tuple[list[BMVert], list[BMEdge]]:
    """
    Finds the shortest path between two boundary vertices using boundary edges.
    
    Params:
    - a_vert: The starting boundary vertex.
    - b_vert: The target boundary vertex.
    - max_walk: The maximum number of vertices to visit.
    - wire_walk: Whether to walk on wire edges.
    
    Returns:
    - A tuple containing two lists:
        - The first list contains the vertices in the path from a_vert to b_vert.
        - The second list contains the edges in the path from a_vert to b_vert.
    """
    if a_vert == b_vert:
        return ([], [])
    if not a_vert.is_boundary or not b_vert.is_boundary:
        if wire_walk:
            if not a_vert.is_wire and not b_vert.is_wire:
                print("walk_boundary: a_vert and b_vert are not wire vertices")
                return ([], [])
        else:
            return ([], [])
    visited: set[BMVert] = set([a_vert])
    parent: dict[BMVert, BMVert] = {}
    parent_edge: dict[BMVert, BMEdge] = {}
    queue: list[BMVert] = [a_vert]
    while queue and len(visited) <= max_walk:
        v = queue.pop(0)
        if v == b_vert:
            verts_path: list[BMVert] = []
            edges_path: list[BMEdge] = []
            cur = b_vert
            while cur != a_vert:
                verts_path.append(cur)
                edges_path.append(parent_edge[cur])
                cur = parent[cur]
            verts_path.reverse()
            edges_path.reverse()
            if verts_path:
                return (verts_path[:-1], edges_path)
            return ([], edges_path)
        for e in v.link_edges:
            if not (e.is_boundary or (wire_walk and e.is_wire)):
                continue
            u = e.other_vert(v)
            if u in visited:
                continue
            visited.add(u)
            parent[u] = v
            parent_edge[u] = e
            queue.append(u)
    return ([], [])


def walk_closed_boundary(start_end_edge: BMEdge) -> tuple[list[BMVert], list[BMEdge]]:
    """
    Finds a closed path starting and ending at the given edge using boundary edges.
    
    Params:
    - start_end_edge: The starting/ending boundary edge.
    
    Returns:
    - A tuple containing two lists:
        - The first list contains the vertices in the path.
        - The second list contains the edges in the path.
        - The path is closed, meaning the last edge connects the last vertex to the first vertex.
    """
    if not start_end_edge.is_wire:
        print("walk_closed_boundary: start_end_edge is not a boundary edge")
        return ([], [])
    start_vert = start_end_edge.verts[0]
    visited: set[BMVert | BMEdge] = set([start_vert, start_end_edge])
    vert_path: list[BMVert] = [start_vert]
    edge_path: list[BMEdge] = [start_end_edge]
    n_loops = 0
    max_walk = len(vert_path)
    current_vert = start_end_edge.other_vert(start_vert)
    lk_edges = current_vert.link_edges
    current_edge = lk_edges[0] if lk_edges[1] == start_end_edge else lk_edges[1]

    while current_vert != start_vert and n_loops < max_walk:
        print(f"CurrentVertex: {current_vert.index}")
        if current_edge in visited:
            print("\t- Edge is already visited")
            continue
        visited.add(current_edge)
        other = current_edge.other_vert(current_vert)
        edge_path.append(current_edge)
        current_vert = other
        if current_vert == start_vert:
            break
        vert_path.append(current_vert)
        lk_edges = current_vert.link_edges
        current_edge = lk_edges[0] if lk_edges[1] == current_edge else lk_edges[1]
        n_loops += 1

    print(f"walk_closed_boundary: n_loops = {n_loops}")
    return (vert_path, edge_path)



def find_all_boundaries(edges: list[BMEdge]) -> list[tuple[list[BMVert], list[BMEdge]]]:
    """
    Finds all different/disconnected closed paths from the given boundary vertices.

    Params:
    - verts: The list of boundary vertices.
    
    Returns:
    - A list of tuples, each containing two lists:
        - The first list contains the vertices in the path.
        - The second list contains the edges in the path.
    """
    walked_edges: set[BMEdge] = set()
    paths: list[tuple[list[BMVert], list[BMEdge]]] = []
    for e in edges:
        if e in walked_edges:
            continue
        path_verts, path_edges = walk_closed_boundary(e)
        if path_verts and path_edges:
            paths.append((path_verts, path_edges))
            walked_edges.update(path_edges)
    return paths


def get_closed_boundary_loop(
    edge: BMEdge,
    wire_walk: bool = True,
) -> tuple[list[BMEdge], list[Vector]] | None:
    """Walk the boundary/wire loop from *edge* and return it only if it is a closed cycle.

    A loop is considered closed when every vertex in the collected edges has
    exactly degree 2 (appears in exactly two of the loop edges), which is the
    graph-theoretic definition of a cyclic path.

    Params:
    - edge: Starting edge.  Must be a boundary or wire edge; returns ``None``
      for interior edges (unless *wire_walk* covers them).
    - wire_walk: Whether to follow wire edges as well as boundary edges.

    Returns:
    - ``(edges, coords)`` if a closed loop was found, ``None`` otherwise.
    """
    if not (edge.is_boundary or (wire_walk and edge.is_wire)):
        return None
    loop_edges, loop_coords = get_boundary_edge_loop(edge, wire_walk=wire_walk, get_coords=True)
    if not loop_edges or len(loop_edges) < 3:
        return None
    degree: dict[BMVert, int] = {}
    for e in loop_edges:
        for v in e.verts:
            degree[v] = degree.get(v, 0) + 1
    if all(d == 2 for d in degree.values()):
        return loop_edges, loop_coords
    return None


#MARK: Grid from ABC
def create_grid_from_ABC(
                    context: Context,
                    bm: BMesh,
                    a_vert: BMVert,
                    b_vert: BMVert,
                    c_vert: BMVert):
    """
    Create an interpolated grid between three vertices:
    A (existing), B (loose), C (existing)
    - Finds D using shortest-path by boundary edges.
    """
    path_verts, path_edges = walk_boundary(a_vert, c_vert, wire_walk=True)
    if not path_edges:
        print("No se pudo encontrar un path boundary entre A y C.")
        return False

    # Combine verts and edges in path so that it looks like (BMVert, BMEdge, BMVert, ..., BMEdge, BMVert)
    _path_verts = [a_vert] + path_verts
    path = []
    for i in range(len(_path_verts)):
        path.append(_path_verts[i])
        path.append(path_edges[i])
    path.append(c_vert)

    # Get all edge loops between path ends and intermediate pole vertices (vertices in path with more than 3 linked edges).
    paths_between_end_and_poles: list[list[BMVert | BMEdge]] = []
    curr_edge_path = []
    vert_ends = {a_vert, c_vert}
    for prim in path:
        if isinstance(prim, BMVert):
            curr_edge_path.append(prim)
            if len(curr_edge_path) >= 3 and (prim in vert_ends or len(prim.link_edges) > 3):
                paths_between_end_and_poles.append(curr_edge_path) # end current sub-path
                curr_edge_path = [prim] # start new potential sub-path
        elif isinstance(prim, BMEdge):
            curr_edge_path.append(prim)

    if len(paths_between_end_and_poles) == 1:
        if len(path_edges) < 2:
            return False
        split_index = 2
        if split_index < len(path) - 1:
            paths_between_end_and_poles = [path[:split_index + 1], path[split_index:]]

    ## 3. dicard if more than 2 edge loops in the walk-path.
    if len(paths_between_end_and_poles) > 2:
        print("More than 2 edge loops between path ends, that case is still not supported")
        return False

    d_vert = paths_between_end_and_poles[0][-1]  # also: paths_between_end_and_poles[1][0]

    def path_end_vert(path: list[BMVert | BMEdge]) -> BMVert | None:
        for prim in reversed(path):
            if isinstance(prim, BMVert):
                return prim
        return None

    if len(paths_between_end_and_poles) == 2 and len(paths_between_end_and_poles[0]) == len(paths_between_end_and_poles[1]):
        end0 = path_end_vert(paths_between_end_and_poles[0])
        end1 = path_end_vert(paths_between_end_and_poles[1])
        if end0 is a_vert:
            short_side_path = paths_between_end_and_poles[0]
            long_side_path = paths_between_end_and_poles[1]
        elif end1 is a_vert:
            short_side_path = paths_between_end_and_poles[1]
            long_side_path = paths_between_end_and_poles[0]
        else:
            short_side_path = paths_between_end_and_poles[0]
            long_side_path = paths_between_end_and_poles[1]
    else:
        long_side_path = max(paths_between_end_and_poles, key=len)
        short_side_path = min(paths_between_end_and_poles, key=len)

    long_side_edge_path = [e for e in long_side_path if isinstance(e, BMEdge)]
    short_side_edge_path = [e for e in short_side_path if isinstance(e, BMEdge)]
    long_side_len = len(long_side_edge_path)
    short_side_len = len(short_side_edge_path)

    # SHORT, LONG.
    grid_steps = (short_side_len, long_side_len)
    grid_size = (short_side_len + 1, long_side_len + 1)

    grid_corner_indices = {
        (0, 0),
        (grid_steps[0], 0),
        (0, grid_steps[1]),
        (grid_steps[0], grid_steps[1]),
    }

    denom_short = max(grid_steps[0], 1)
    denom_long = max(grid_steps[1], 1)

    print("Grid Size:", grid_steps)
    print("Grid Vert Size:", grid_size)
    print("Grid Corner Indices:", grid_corner_indices)
    print("Denominators:", denom_short, denom_long)

    @dataclass
    class GridVertex:
        vert: BMVert
        index: int
        co: Vector
        co_2d: Vector
        face_id: int = -1
        reg_index: int = -1
        grid_index: tuple[int, int] = (-1, -1)
        
        @property
        def type(self) -> Literal['CORNER', '`BOUNDARY', 'INNER']:
            if self.is_corner:
                return 'CORNER'
            if self.is_boundary:
                return 'BOUNDARY'
            return 'INNER'

        @property
        def is_corner(self) -> bool:
            nonlocal grid_corner_indices
            return self.grid_index in grid_corner_indices
        
        @property
        def is_boundary(self) -> bool:
            nonlocal denom_short, denom_long
            return self.grid_index[0] in (0, denom_short) or self.grid_index[1] in (0, denom_long)
        
        @property
        def is_inner(self) -> bool:
            return not self.is_corner and not self.is_boundary

        @classmethod
        def from_bm_vert(cls, context: Context, bm_vert: BMVert, grid_index: tuple[int, int]) -> 'GridVertex':
            if gv := fetch_grid_vert(grid_index):
                return gv
            new_gv = cls(
                bm_vert,
                bm_vert.index,
                bm_vert.co,
                location_3d_to_region_2d(context.region, context.region_data, bm_vert.co, default=Vector((0, 0))).freeze(),
                grid_index=grid_index
            )
            register_grid_vert(new_gv)
            return new_gv

        @classmethod
        def from_co2d(cls, context: Context, co2d: Vector, grid_index: tuple[int, int]) -> 'GridVertex':
            if gv := fetch_grid_vert(grid_index):
                return gv
            hit_info = raycast_scene(context, co2d)
            if not hit_info.hit:
                raise ValueError("No se pudo encontrar una intersección en la escena para el punto 2D.")
            new_gv = cls(
                None,
                -1,
                hit_info.location,
                co2d.freeze(),
                grid_index=grid_index
            )
            register_grid_vert(new_gv)
            return new_gv

        def realize_bm_vert(self, bm: BMesh) -> None:
            if self.vert is not None:
                return
            vert = bm.verts.new(self.co)
            self.vert = vert
            self.index = vert.index

    grid_vertices: dict[tuple[int, int], GridVertex] = {}
    grid_vertices_count = 0
    def register_grid_vert(gv: GridVertex) -> None:
        print(f"Register new GridVertex of type '{gv.type}' at index: {gv.grid_index}")
        nonlocal grid_vertices_count, grid_vertices
        gv.reg_index = grid_vertices_count
        grid_vertices[gv.grid_index] = gv
        grid_vertices_count += 1

    def fetch_grid_vert(grid_index: tuple[int, int]) -> GridVertex:
        return grid_vertices.get(grid_index, None)

    # A, B, C, D.
    grid_corner_verts = [a_vert, b_vert, c_vert, d_vert]
    # This is just to create the grid vertices corresponding to the corners.
    gv_corner_d = GridVertex.from_bm_vert(context, d_vert, grid_index=(0, 0))
    gv_corner_b = GridVertex.from_bm_vert(context, b_vert, grid_index=(denom_short, denom_long))
    print("Grid Corners:", (a_vert, b_vert, c_vert, d_vert))

    # IMPORTANT! gv_short_ends and gv_long_ends should start with D corner.
    # so that they are both aligned! as D vert is the origin of the grid (0, 0) grid index.
    if short_side_path[0] is not d_vert:
        short_side_path.reverse()
    if long_side_path[0] is not d_vert:
        long_side_path.reverse()

    corner_ids_in_short_side = ['D', 'A' if short_side_path[-1] == a_vert else 'C']
    corner_ids_in_long_side = ['D', 'C' if long_side_path[-1] == c_vert else 'A']
    corner_ids_in_short_side_opp = ['C' if long_side_path[-1] == c_vert else 'A', 'B'] # corner flipped for the opposite side
    corner_ids_in_long_side_opp = ['A' if short_side_path[-1] == a_vert else 'C', 'B'] # corner flipped for the opposite side

    print("Short Side Path:", [v for v in short_side_path if isinstance(v, BMVert)])
    print("Long Side Path:", [v for v in long_side_path if isinstance(v, BMVert)])

    print("Corner IDs in Short Side:", corner_ids_in_short_side)
    print("Corner IDs in Long Side:", corner_ids_in_long_side)
    print("Corner IDs in Short Side Opp:", corner_ids_in_short_side_opp)
    print("Corner IDs in Long Side Opp:", corner_ids_in_long_side_opp)
    print("Grid Corners Diagram:")
    print(f"  {corner_ids_in_short_side_opp[0]} ──(short_side_opp)── {corner_ids_in_short_side_opp[1]}")
    print("  │                      │")
    print("  │ (long_side)          │ (long_side_opp)")
    print("  │                      │")
    print(f"  {corner_ids_in_short_side[0]} ────(short_side)──── {corner_ids_in_short_side[1]}")

    # D -> A and D -> B.
    short_side_verts = [vert for vert in short_side_path if isinstance(vert, BMVert)]
    long_side_verts = [vert for vert in long_side_path if isinstance(vert, BMVert)]
    gv_short_side: list[GridVertex] = [GridVertex.from_bm_vert(context, vert, grid_index=(i, 0)) for i, vert in enumerate(short_side_verts)]
    gv_long_side: list[GridVertex] = [GridVertex.from_bm_vert(context, vert, grid_index=(0, i)) for i, vert in enumerate(long_side_verts)]

    gv_short_ends: tuple[GridVertex, GridVertex] = (gv_short_side[0], gv_short_side[-1])
    gv_long_ends: tuple[GridVertex, GridVertex] = (gv_long_side[0], gv_long_side[-1])

    # This is just to generate the opposite vertices for the short and long sides.
    gv_short_end = GridVertex.from_bm_vert(context, gv_short_side[-1].vert, grid_index=(denom_short, 0))
    gv_long_end = GridVertex.from_bm_vert(context, gv_long_side[-1].vert, grid_index=(0, denom_long))

    gv_short_side_opp = [
        GridVertex.from_co2d(
            context,
            interpolate_linear(gv_long_end.co_2d, gv_corner_b.co_2d, t=i/denom_short),
            grid_index=(i, denom_long)
        )
        for i in range(grid_size[0])
    ]
    gv_long_side_opp = [
        GridVertex.from_co2d(
            context,
            interpolate_linear(gv_short_end.co_2d, gv_corner_b.co_2d, t=i/denom_long),
            grid_index=(denom_short, i)
        )
        for i in range(grid_size[1])
    ]

    gv_inner: list[GridVertex] = []
    if denom_short > 1:
        for grid_col in range(grid_size[0]):
            gv_row_start = fetch_grid_vert((grid_col, 0))
            gv_row_end = fetch_grid_vert((grid_col, denom_long))
            for grid_row in range(grid_size[1]):
                if gv := fetch_grid_vert((grid_col, grid_row)):
                    # print(f"Grid vertex at index ({grid_col}, {grid_row}) already exists. Coord2D: {gv.co_2d}")
                    continue
                co2d = interpolate_linear(
                    gv_row_start.co_2d,
                    gv_row_end.co_2d,
                    t=grid_row/denom_long
                )
                gv = GridVertex.from_co2d(context, co2d, grid_index=(grid_col, grid_row))
                print(f"Grid vertex at index ({grid_col}, {grid_row}) created. Coord2D: {co2d}")
                gv_inner.append(gv)

    print("Inner Grid Vertices:", gv_inner)

    # Realize vertices.
    for gv in grid_vertices.values():
        gv.realize_bm_vert(bm)
    
    bm.verts.ensure_lookup_table()

    # Let's see the vertices for each quad in the grid.
    gv_faces: list[list[GridVertex]] = []
    for grid_col in range(grid_steps[0]):
        for grid_row in range(grid_steps[1]):
            gv_faces.append([
                fetch_grid_vert((grid_col, grid_row)),
                fetch_grid_vert((grid_col + 1, grid_row)),
                fetch_grid_vert((grid_col + 1, grid_row + 1)),
                fetch_grid_vert((grid_col, grid_row + 1)),
            ])

    print("Grid Faces:")
    for gv_face in gv_faces:
        print("t-", ', '.join([f"{gv.grid_index}" for gv in gv_face]))

    print("Expected face count:", grid_steps[0] * grid_steps[1])
    print("Resulting face count:", len(gv_faces))

    # Realize faces.
    for gv_face in gv_faces:
        bm_face = bm.faces.new([gv.vert for gv in gv_face])
        bm_face.normal_update()
        if is_face_normal_away_from_view(context, bm_face):
            bm_face.normal_flip()

    bm.faces.ensure_lookup_table()
    return True


def create_grid_from_ABCD(
                    context: Context,
                    bm: BMesh,
                    a_vert: BMVert,
                    b_vert: BMVert,
                    c_vert: BMVert,
                    d_vert: BMVert,
                    edge_path: list[BMEdge] | None = None) -> bool:
    def ordered_verts_from_edges(start_vert: BMVert, edges: list[BMEdge]) -> list[BMVert]:
        if not edges:
            return []
        verts = [start_vert]
        current_vert = start_vert
        for edge in edges:
            if current_vert not in edge.verts:
                return []
            current_vert = edge.other_vert(current_vert)
            verts.append(current_vert)
        return verts

    def segment_path_edges(path_edges: list[BMEdge]) -> tuple[dict[int, list[tuple[BMEdge, BMVert, BMVert]]], int] | None:
        ordered_edges = path_edges
        ordered_verts = ordered_verts_from_edges(a_vert, ordered_edges)
        if not ordered_verts or ordered_verts[-1] is not b_vert:
            ordered_edges = list(reversed(path_edges))
            ordered_verts = ordered_verts_from_edges(a_vert, ordered_edges)
            if not ordered_verts or ordered_verts[-1] is not b_vert:
                return None

        segments = defaultdict(list)
        segment_index = 0
        for e_idx, edge in enumerate(ordered_edges):
            v1 = ordered_verts[e_idx]
            v2 = ordered_verts[e_idx + 1]
            if e_idx != 0 and len(v1.link_faces) > 2:
                segment_index += 1
            segments[segment_index].append((edge, v1, v2))
        return segments, segment_index

    short_side_verts: list[BMVert] = []
    long_side_verts: list[BMVert] = []
    top_side_verts: list[BMVert] = []

    if edge_path:
        segmented = segment_path_edges(edge_path)
        if not segmented:
            print("create_grid_from_ABCD failed: edge_path is not a valid ordered path from a_vert to b_vert")
            return False
        segments, segment_index = segmented
        if segment_index != 2 or len(segments[0]) != len(segments[2]):
            print(f"create_grid_from_ABCD failed: invalid edge_path segmentation. segment_count={segment_index}, len(segments[0])={len(segments[0])}, len(segments[2])={len(segments[2])}")
            return False
        inferred_d_vert = segments[0][-1][2]
        inferred_c_vert = segments[2][0][1]
        d_vert = inferred_d_vert
        c_vert = inferred_c_vert
        short_side_verts = [v1 for _, v1, _ in segments[0]]
        short_side_verts.append(segments[0][-1][2])
        short_side_verts.reverse()
        long_side_verts = [v1 for _, v1, _ in segments[1]]
        long_side_verts.append(segments[1][-1][2])
        top_side_verts = [v1 for _, v1, _ in segments[2]]
        top_side_verts.append(segments[2][-1][2])
        if top_side_verts[0] is not c_vert and top_side_verts[-1] is c_vert:
            top_side_verts.reverse()
    else:
        _, short_side_edges = walk_boundary(d_vert, a_vert, wire_walk=True)
        _, long_side_edges = walk_boundary(d_vert, c_vert, wire_walk=True)
        if not short_side_edges or not long_side_edges:
            print("create_grid_from_ABCD failed: could not build side paths")
            return False
        short_side_verts = ordered_verts_from_edges(d_vert, short_side_edges)
        long_side_verts = ordered_verts_from_edges(d_vert, long_side_edges)

    if len(short_side_verts) < 2 or len(long_side_verts) < 2:
        print("create_grid_from_ABCD failed: short or long side paths are invalid")
        return False

    denom_short = len(short_side_verts) - 1
    denom_long = len(long_side_verts) - 1

    grid_verts: dict[tuple[int, int], BMVert] = {}
    vert_co2d_cache: dict[BMVert, Vector] = {}

    def vert_to_co2d(vert: BMVert) -> Vector:
        if co2d := vert_co2d_cache.get(vert):
            return co2d
        co2d = location_3d_to_region_2d(context.region, context.region_data, vert.co, default=Vector((0, 0))).freeze()
        vert_co2d_cache[vert] = co2d
        return co2d

    def create_vert_from_co2d(co2d: Vector) -> BMVert:
        hit_info = raycast_scene(context, co2d)
        if hit_info and hit_info.hit:
            return bm.verts.new(hit_info.location)
        return bm.verts.new(region_2d_to_location_3d(context.region, context.region_data, co2d, d_vert.co))

    for i, vert in enumerate(short_side_verts):
        grid_verts[(i, 0)] = vert
    for j, vert in enumerate(long_side_verts):
        grid_verts[(0, j)] = vert
    grid_verts[(denom_short, denom_long)] = b_vert
    if top_side_verts:
        if len(top_side_verts) != denom_short + 1:
            print(f"create_grid_from_ABCD failed: invalid top side length. expected={denom_short + 1}, got={len(top_side_verts)}")
            return False
        for i, vert in enumerate(top_side_verts):
            grid_verts[(i, denom_long)] = vert

    c_co2d = vert_to_co2d(c_vert)
    b_co2d = vert_to_co2d(b_vert)
    for i in range(denom_short + 1):
        key = (i, denom_long)
        if key in grid_verts:
            continue
        co2d = interpolate_linear(c_co2d, b_co2d, t=i/max(denom_short, 1))
        grid_verts[key] = create_vert_from_co2d(co2d)

    a_co2d = vert_to_co2d(a_vert)
    for j in range(denom_long + 1):
        key = (denom_short, j)
        if key in grid_verts:
            continue
        co2d = interpolate_linear(a_co2d, b_co2d, t=j/max(denom_long, 1))
        grid_verts[key] = create_vert_from_co2d(co2d)

    for i in range(1, denom_short):
        start_vert = grid_verts[(i, 0)]
        end_vert = grid_verts[(i, denom_long)]
        start_co2d = vert_to_co2d(start_vert)
        end_co2d = vert_to_co2d(end_vert)
        for j in range(1, denom_long):
            key = (i, j)
            if key in grid_verts:
                continue
            co2d = interpolate_linear(start_co2d, end_co2d, t=j/max(denom_long, 1))
            grid_verts[key] = create_vert_from_co2d(co2d)

    def ensure_edge(v1: BMVert, v2: BMVert) -> BMEdge:
        existing = bm.edges.get((v1, v2))
        if existing:
            return existing
        return bm.edges.new((v1, v2))

    def get_existing_face(verts: list[BMVert]) -> BMFace | None:
        face_sets = [set(v.link_faces) for v in verts]
        if not face_sets:
            return None
        shared = set.intersection(*face_sets)
        for face in shared:
            if len(face.verts) == 4 and all(v in face.verts for v in verts):
                return face
        return None

    def create_quad_face(verts: list[BMVert]) -> BMFace | None:
        if existing := get_existing_face(verts):
            return existing
        try:
            return bm.faces.new(verts)
        except ValueError:
            try:
                quad_edges = [
                    ensure_edge(verts[0], verts[1]),
                    ensure_edge(verts[1], verts[2]),
                    ensure_edge(verts[2], verts[3]),
                    ensure_edge(verts[3], verts[0]),
                ]
                res = bmesh.ops.contextual_create(bm, geom=quad_edges)
                faces = [g for g in res.get('geom', []) if isinstance(g, BMFace)]
                for face in faces:
                    if len(face.verts) == 4 and all(v in face.verts for v in verts):
                        return face
            except Exception:
                return None
        return None

    created_faces = 0
    for i in range(denom_short):
        for j in range(denom_long):
            face_verts = [
                grid_verts[(i, j)],
                grid_verts[(i + 1, j)],
                grid_verts[(i + 1, j + 1)],
                grid_verts[(i, j + 1)],
            ]
            bm_face = create_quad_face(face_verts)
            if not bm_face:
                continue
            bm_face.normal_update()
            if is_face_normal_away_from_view(context, bm_face):
                bm_face.normal_flip()
            created_faces += 1

    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    return created_faces > 0



#MARK: Grid from AC_B
def create_grid_from_AC_B(
                    context: Context,
                    bm: BMesh,
                    a_vert: BMVert,
                    c_vert: BMVert,
                    b_vert_location: Vector) -> bool:
    """Create a grid from vertices A, B, and C.
    The grid will be created with A and C as existing corners, and B as the loose vertex between A and C (to be created by this fn).

    Args:
        context (Context): The Blender context.
        bm (BMesh): The BMesh object.
        a_vert (BMVert): The A vertex.
        c_vert (BMVert): The C vertex.
        b_vert_location (Vector): The location of the B vertex (it can be 3d or 2d).

    Returns:
        bool: True if the grid was created successfully, False otherwise.
    """
    try:
        if len(b_vert_location) == 2:
            raycast_info = raycast_scene(context, b_vert_location)
            if raycast_info is None:
                print(f"create_grid_from_AC_B: raycast_scene failed. b_vert_location={b_vert_location}")
                return False
            b_vert_location = raycast_info.location
        b_vert = bm.verts.new(b_vert_location)
        bm.verts.ensure_lookup_table()
        if not create_grid_from_ABC(context, bm, a_vert, b_vert, c_vert):
            raise Exception("create_grid_from_ABC failed")
        return True
    except Exception as e:
        print(f"create_grid_from_AC_B: {e}")
        bm.verts.remove(b_vert)
        bm.verts.ensure_lookup_table()
        return False


def create_face_from_bmverts_and_raw_coords(context: Context, bm: BMesh, *verts: BMVert | Vector) -> BMFace | None:
    """Create a polygon face from a list of BMVert objects or their locations.

    Args:
        context (Context): The Blender context.
        bm (BMesh): The BMesh object.
        verts (BMVert | Vector): The vertices of the polygon.

    Returns:
        BMFace | None: The created polygon face, or None if the face could not be created (e.g. less than 3 vertices).
    """
    def _realize_vert(vert: BMVert | Vector) -> BMVert:
        if isinstance(vert, BMVert):
            return vert
        if not isinstance(vert, Vector):
            raise ValueError(f"create_face_from_bmverts_and_raw_coords: vert is not a BMVert or Vector. vert={vert}")
        loc = vert
        if len(loc) == 2:
            raycast_info = raycast_scene(context, loc)
            if raycast_info is None:
                raise ValueError(f"create_face_from_bmverts_and_raw_coords: raycast_scene failed. vert={vert}")
            loc = raycast_info.location
        return bm.verts.new(loc)

    bm_verts = [_realize_vert(vert) for vert in verts if isinstance(vert, (BMVert, Vector))]
    if len(set(bm_verts)) < 3:
        print(f"create_face_from_bmverts_and_raw_coords: verts must have at least 3 vertices. verts={verts}")
        return None
    bm_verts = remove_duplicates_keep_order(bm_verts)
    bm_face = bm.faces.new(bm_verts)
    bm_face.normal_update()
    if is_face_normal_away_from_view(context, bm_face):
        bm_face.normal_flip()
    bmesh.update_edit_mesh(context.edit_object.data, destructive=True)
    return bm_face


def vert_shared_vert(a: BMVert, b: BMVert) -> BMVert | None:
    """Find the shared vertex between two vertices.

    Args:
        a (BMVert): The A vertex.
        b (BMVert): The B vertex.

    Returns:
        BMVert | None: The shared vertex, or None if no shared vertex exists.
    """
    a_linked_edges = a.link_edges
    a_other_verts = {edge.other_vert(a) for edge in a_linked_edges}
    b_linked_edges = b.link_edges
    b_other_verts = {edge.other_vert(b) for edge in b_linked_edges}
    intersect_verts = a_other_verts & b_other_verts
    if len(intersect_verts) != 0:
        d_vert = intersect_verts.pop()
        return d_vert
    return None


def vert_shared_edge(a: BMVert, b: BMVert) -> BMEdge | None:
    """Find the shared edge between two vertices.

    Args:
        a (BMVert): The A vertex.
        b (BMVert): The B vertex.

    Returns:
        BMEdge | None: The shared edge, or None if no shared edge exists.
    """
    shared_edge = None
    for edge in a.link_edges:
        if b in edge.verts:
            shared_edge = edge
            break
    return shared_edge


#MARK: Edge Loop Cut by 2d Line
def edge_loop_cut_by_2d_line(
        context: Context,
        edge: BMEdge,
        line_a: Vector,
        line_b: Vector,
        number_cuts: int = 1,
        smoothness: float = 0.0,
        ) -> list[BMEdge]:
    """Cut an edge loop by a 2d line.

    Args:
        context (Context): The Blender context.
        bm (BMesh): The BMesh object.
        edge (BMEdge): The edge to cut.
        line_a (Vector): The A point of the line.
        line_b (Vector): The B point of the line.
        number_cuts (int, optional): The number of cuts to make. Defaults to 1.
        smoothness (float, optional): The smoothness of the cut. Defaults to 0.0.

    Returns:
        tuple[bool, str]: True if the edge was cut successfully, False otherwise. The second element is the error message.
    """
    if context.mode != 'EDIT_MESH':
        return False, 'WRONG_MODE'

    v1, v2 = edge.verts
    # Check if the line intersects with the edge.
    region, rv3d = context.region, context.region_data
    reg_edge_v1 = location_3d_to_region_2d(region, rv3d, v1.co)
    reg_edge_v2 = location_3d_to_region_2d(region, rv3d, v2.co)
    if reg_edge_v1 is None or reg_edge_v2 is None:
        return False, "PROJECTION_ERROR"

    # Check if the line intersects with the shared edge.
    if (intersect := intersect_line_line_2d(line_a, line_b, reg_edge_v1, reg_edge_v2)) is None:
        return False, "NO_INTERSECT"

    # Add the cut.
    bpy.ops.mesh.loopcut(
        number_cuts=number_cuts,
        smoothness=smoothness,
        falloff='SMOOTH',
        object_index=0,
        edge_index=edge.index,
    )

    # Factor [-1, -1] of the intersect point between v1 and v2.
    # depending on the orientation of the edge, the factor is different and should be inverted.
    # but i'm not sure what is the correct way to calculate the factor, probably loops or edge indices involved...
    factor = (intersect - reg_edge_v2).length / (reg_edge_v1 - reg_edge_v2).length * 2 - 1

    '''print("EDGE LOOP CUT INFO:")
    print(f"  factor={factor}")
    print(f"  edge={edge}")
    print(f"  edge_edge_loops={list(edge.link_loops)}")
    print(f"  v1_linked_loops={list(v1.link_loops)}")
    print(f"  v2_linked_loops={list(v2.link_loops)}")
    print(f"  v1_co={v1.co}")
    print(f"  v2_co={v2.co}")
    # print(f"  intersect_3d={intersect_3d}")
    print(f"  edge_face_angle={edge.calc_face_angle()}")
    print(f"  edge_face_angle_signed={edge.calc_face_angle_signed()}")
    print(f"  edge v2-v1: {v2.co - v1.co}")
    print(f"  vert with lower coords in X axis: {v1.co if v1.co.x < v2.co.x else v2.co}")
    print(f"  vert with lower coords in Y axis: {v1.co if v1.co.y < v2.co.y else v2.co}")
    print(f"  vert with lower coords in Z axis: {v1.co if v1.co.z < v2.co.z else v2.co}")'''

    bpy.ops.transform.edge_slide(
        value=factor,
        release_confirm=False,
    )
    return True, "SUCCESS"


#MARK: Quadstrip from Line 2D
def quadstrip_from_line_2d(context: Context, bm: BMesh, line_a: Vector, line_b: Vector, number_cuts: int = 8) -> None:
    """Create a quad-only strip along the provided 2D line.
    Args:
        context (Context): The Blender context.
        bm (BMesh): The BMesh object.
        line_a (Vector): The A point of the line.
        line_b (Vector): The B point of the line.
        number_cuts (int): The number of cuts to make.
    """
    if context.mode != 'EDIT_MESH':
        return
    line_dir = line_b - line_a
    if line_dir.length == 0:
        return
    line_dir.normalize()
    perp = Vector((-line_dir.y, line_dir.x))
    samples = max(number_cuts + 1, 2)
    radius_step = 12.0
    radius_steps = 8
    left_hits = []
    right_hits = []
    for i in range(samples):
        t = i / (samples - 1)
        center = line_a.lerp(line_b, t)
        for side, hits in ((-1.0, left_hits), (1.0, right_hits)):
            best_hit = None
            best_r = 0.0
            for s in range(1, radius_steps + 1):
                r = s * radius_step
                coord = center + perp * side * r
                info = raycast_scene(context, coord)
                if info is not None and info.hit:
                    if r > best_r:
                        best_r = r
                        best_hit = info.location
            if best_hit is not None:
                hits.append(best_hit)
    ring_points = left_hits + right_hits[::-1]
    if len(ring_points) < 3:
        return
    mw_inv = context.edit_object.matrix_world.inverted()
    ring_verts: list[BMVert] = []
    for p in ring_points:
        ring_verts.append(bm.verts.new(mw_inv @ p))
    bm.verts.ensure_lookup_table()
    for i in range(len(ring_verts)):
        v1 = ring_verts[i]
        v2 = ring_verts[(i + 1) % len(ring_verts)]
        try:
            bm.edges.new((v1, v2))
        except ValueError:
            pass
    bmesh.update_edit_mesh(context.edit_object.data, destructive=True)


def _plane_from_line_2d(context: Context, line_a: Vector, line_b: Vector, apply_edit_object_transform: bool = False) -> tuple[Vector, Vector]:
    """
    Calculate the plane from the line in 2D space.

    Args:
        context (Context): The Blender context.
        line_a (Vector): The A point of the line.
        line_b (Vector): The B point of the line.
        apply_edit_object_transform (bool): Whether to apply the transform of the edit object to the plane.
    
    Returns:
        tuple[Vector, Vector]: A tuple containing the center point of the plane and the normal vector of the plane.
    """
    line_middle = (line_a + line_b) / 2

    # Project the line middle to the mesh.
    raycast_info = raycast_scene(context, line_middle)
    if raycast_info is None:
        raise ValueError(f"ring_loopcut_from_line_2d: raycast_scene failed. line_middle={line_middle}")
    line_middle_prj = raycast_info.location
    line_a_3d = region_2d_to_location_3d(context.region, context.region_data, line_a, line_middle_prj)
    line_b_3d = region_2d_to_location_3d(context.region, context.region_data, line_b, line_middle_prj)
    line_dir = line_b_3d - line_a_3d
    if line_dir.length == 0:
        return
    line_dir.normalize()
    view_dir = get_view_vector(context, line_middle)
    plane_normal_world = view_dir.cross(line_dir)
    if plane_normal_world.length == 0:
        return
    plane_normal_world.normalize()
    if apply_edit_object_transform:
        mw = context.edit_object.matrix_world
    else:
        mw = Matrix.Identity(4)
    plane_co = mw.inverted() @ line_middle_prj
    plane_no = (mw.inverted().to_3x3() @ plane_normal_world).normalized()
    return plane_co, plane_no


#MARK: Bisect Plane Utils
def _split_geom_cut(geom_cut):
    verts = {g for g in geom_cut if isinstance(g, BMVert)}
    edges = {g for g in geom_cut if isinstance(g, BMEdge)}
    return verts, edges

def _geom_cut_to_boundaries(geom_cut):
    edges = {g for g in geom_cut if isinstance(g, BMEdge)}
    return _extract_boundaries_from_edges(edges)
    _, edges = _split_geom_cut(geom_cut)
    graph = build_edge_graph(edges)
    return _extract_boundaries_from_graph(graph)

def _geom_cut_to_boundaries__planar(geom_cut, plane_origin, plane_normal):
    edges = {g for g in geom_cut if isinstance(g, BMEdge)}
    return _extract_boundaries_from_edges_planar(
        edges,
        plane_origin,
        plane_normal
    )

def _extract_boundaries_from_graph(graph):
    visited = set()
    boundaries = []

    # iterar sobre copia estática
    for start in list(graph.keys()):
        if start in visited:
            continue

        boundary = [start]
        visited.add(start)

        prev = None
        current = start

        while True:
            neighbors = graph[current] - ({prev} if prev else set())

            # loop abierto o degenerado
            if not neighbors:
                break

            nxt = neighbors.pop()

            # loop cerrado
            if nxt == start:
                break

            if nxt in visited:
                break

            boundary.append(nxt)
            visited.add(nxt)

            prev, current = current, nxt

        if len(boundary) >= 3:
            boundaries.append(boundary)

    return boundaries

def _extract_boundaries_from_edges(edges):
    unused = set(edges)
    boundaries = []

    while unused:
        edge = unused.pop()
        v_start, v_next = edge.verts

        boundary = [v_start, v_next]
        current = v_next
        prev = v_start

        while True:
            connected = [
                e for e in current.link_edges
                if e in unused
            ]

            if not connected:
                break  # loop abierto

            e = connected[0]
            unused.remove(e)

            v1, v2 = e.verts
            nxt = v2 if v1 == current else v1

            if nxt == v_start:
                break  # loop cerrado

            boundary.append(nxt)
            prev, current = current, nxt

        if len(boundary) >= 3:
            boundaries.append(boundary)

    return boundaries

def _extract_boundaries_from_edges_planar(
    edges,
    plane_origin,
    plane_normal
):
    def project_vert_2d(v, plane_origin, u, v_axis):
        vec = v.co - plane_origin
        return Vector((vec.dot(u), vec.dot(v_axis)))

    # base del plano
    u, v_axis, _ = plane_basis(plane_normal)

    # proyectar verts
    v2d = {}
    for e in edges:
        for vtx in e.verts:
            if vtx not in v2d:
                v2d[vtx] = project_vert_2d(vtx, plane_origin, u, v_axis)

    # construir adjacency con ángulos
    adj = {}
    for e in edges:
        for a, b in ((e.verts[0], e.verts[1]), (e.verts[1], e.verts[0])):
            vec = v2d[b] - v2d[a]
            ang = atan2(vec.y, vec.x)
            adj.setdefault(a, []).append((ang, b, e))

    # ordenar por ángulo
    for vtx in adj:
        adj[vtx].sort(key=lambda x: x[0])

    used = set()
    boundaries = []

    for vtx in adj:
        for ang, nxt, e in adj[vtx]:
            if e in used:
                continue

            boundary = [vtx]
            current = vtx
            current_edge = e
            current_ang = ang

            while True:
                used.add(current_edge)
                boundary.append(nxt)

                options = adj[nxt]
                # buscar la continuación "más a la derecha"
                angles = [a for a, _, _ in options]
                idx = angles.index(
                    min(angles, key=lambda a: (a - current_ang) % (2 * pi))
                )

                next_ang, next_vert, next_edge = options[idx]

                if next_vert == vtx:
                    break

                current = nxt
                current_ang = next_ang
                current_edge = next_edge
                nxt = next_vert

            if len(boundary) >= 3:
                boundaries.append(boundary)

    return boundaries

def _snap_boundary_to_plane(boundary, plane_co, plane_no):
    snapped = []
    for v in boundary:
        p = v.co
        snapped.append(
            p - plane_no * (p - plane_co).dot(plane_no)
        )
    return snapped

def _dedupe_boundary(boundary, eps=1e-6):
    out = [boundary[0]]
    for v in boundary[1:]:
        if (v.co - out[-1].co).length > eps:
            out.append(v)
    return out


#MARK: Bisect Objects into BMesh
def bisect_objects_into_bmesh(
    context: Context,
    source_objects: list[Object],
    bm: BMesh,
    plane_co: Vector,
    plane_no: Vector,
    separate: bool = True,
    post_process: Literal['NONE', 'BOOLEAN_UNION', 'ALPHA_SHAPES'] = 'NONE',
) -> tuple[bool, str | dict[Object, dict[str, list]]]:
    """
    Creates a joined temporary BMesh from source_objects,
    bisects it with a plane, and copies the resulting cut
    verts/edges into the provided BMesh.
    
    Args:
        source_objects (list[Object]): The list of source objects to bisect.
        bm (BMesh): The BMesh object to receive the cut geometry.
        plane_co (Vector): The center point of the bisect plane.
        plane_no (Vector): The normal vector of the bisect plane.
        separate (bool): Whether to bisect each object separately.
        use_alphashapes (bool): Whether to use alpha shapes to construct the resulting loops by using biseect_plane edge loops as input.

    Returns:
        tuple[bool, str | tuple[list[BMVert], list[BMEdge]]]: A tuple containing a boolean indicating
        whether the bisect operation was successful, and a string
        with the reason for failure if the operation was not successful.
        If the operation was successful, the second element of the tuple
        is a tuple containing the list of cut vertices and edges.
    """

    if post_process != 'NONE':
        # We need to join the loops here!
        separate = False

    # --------------------------------------------------
    # 1. Build joined temporary bmesh (world space)
    # --------------------------------------------------
    depsgraph = context.evaluated_depsgraph_get()
    
    if separate:
        temp_bm = {}
    else:
        temp_bm = bmesh.new()

    for obj in source_objects:
        if obj.type != 'MESH':
            continue

        obj_bm = bmesh.new()
        obj_bm.from_object(obj, depsgraph)

        # Transform into world space
        obj_bm.transform(obj.matrix_world)

        if separate:
            temp_bm[obj] = obj_bm
            continue

        # Copy geometry into temp_bm
        geom_map = {}
        for v in obj_bm.verts:
            geom_map[v] = temp_bm.verts.new(v.co)

        temp_bm.verts.ensure_lookup_table()

        for e in obj_bm.edges:
            temp_bm.edges.new((
                geom_map[e.verts[0]],
                geom_map[e.verts[1]],
            ))

        for f in obj_bm.faces:
            temp_bm.faces.new([geom_map[v] for v in f.verts])

        obj_bm.free()

    if not separate:
        temp_bm.normal_update()
        temp_bm.verts.ensure_lookup_table()
        temp_bm.edges.ensure_lookup_table()

    # --------------------------------------------------
    # 2. Bisect plane + capture cut geometry
    # --------------------------------------------------
    
    if not separate:
        temp_bm = {'joined': temp_bm}
        
    bisect_results = {}

    for obj, _bm in temp_bm.items():
        res = bmesh.ops.bisect_plane(
            _bm,
            geom=_bm.verts[:] + _bm.edges[:] + _bm.faces[:],
            plane_co=plane_co,
            plane_no=plane_no,
            clear_inner=False,
            clear_outer=False,
        )
        if geom_cut := res.get('geom_cut', []):
            bisect_results[obj] = {
                'verts': [v for v in geom_cut if isinstance(v, BMVert)],
                'edges': [e for e in geom_cut if isinstance(e, BMEdge)],
            }

    if not bisect_results:
        for _bm in temp_bm.values():
            _bm.free()
        return False, "NO_CUT_EDGES"

    # --------------------------------------------------
    # 3. Post Process
    # --------------------------------------------------

    if post_process == 'BOOLEAN_UNION':
        # NOTE: snap to plane, but certainly not needed here since the bisect_plane op already does it for us.
        # for v in res['geom_cut']:
        #     if isinstance(v, BMVert):
        #         v.co -= plane_no * (v.co - plane_co).dot(plane_no)

        boundaries = _geom_cut_to_boundaries(res['geom_cut']) # __planar(res['geom_cut'], plane_co, plane_no)
        if len(boundaries) < 2:
            # We are good to go! no need for post processing!
            post_process = 'NONE'

    if post_process == 'BOOLEAN_UNION':
        ## print(f"BOOLEAN_UNION: n_boundaries={len(boundaries)}")
        res_boundary = union_bmvert_boundaries_2d(
            boundaries, # [res['verts'] for res in bisect_results.values()]
            context.active_object.matrix_world, # IMPORTANT NOTE: we suppose is the active object matrix world... but if there are many objects there... ^u^" what happens with multiple source objects???
            plane='CUSTOM',
            plane_origin=plane_co,
            plane_normal=plane_no,
            unproject=True # coords to 3d space so we can create the BMVerts out of them!
        )
        ## print("Boundary:", res_boundary)

        verts = []
        edges = []
        for boundary in res_boundary:
            new_verts = [bm.verts.new(co) for co in boundary]
            bm.verts.ensure_lookup_table()

            for i in range(len(new_verts)):
                e = bm.edges.new((
                    new_verts[i],
                    new_verts[(i + 1) % len(new_verts)]
                ))
                edges.append(e)

            bm.edges.ensure_lookup_table()

            verts.extend(new_verts)

        return True, {'boolean': {'verts': verts, 'edges': edges}}


    # --------------------------------------------------
    # 4. Copy cut geometry into provided bmesh
    # --------------------------------------------------

    vert_map = {}
    bisect_output = defaultdict(dict)

    for obj, res in bisect_results.items():
        verts = []
        for v in res['verts']:
            bm_vert = bm.verts.new(v.co)
            verts.append(bm_vert)
            vert_map[v] = bm_vert
        bisect_output[obj]['verts'] = verts

    bm.verts.ensure_lookup_table()

    for obj, res in bisect_results.items():
        cut_edges = res['edges']
        edges = []
        if len(cut_edges) == 0:
            cut_verts = res['verts']
            # Create edges between current vert and next one, starting from current=last and next=first
            last_vert = vert_map.get(cut_verts[-1])
            first_vert = vert_map.get(cut_verts[0])
            edges.append(bm.edges.new((last_vert, first_vert)))
            for i in range(len(cut_verts) - 1):
                v1 = vert_map.get(cut_verts[i])
                v2 = vert_map.get(cut_verts[i + 1])
                edges.append(bm.edges.new((v1, v2)))
        else:
            for e in cut_edges:
                v1 = vert_map.get(e.verts[0])
                v2 = vert_map.get(e.verts[1])
                if v1 and v2:
                    edges.append(bm.edges.new((v1, v2)))
        bisect_output[obj]['edges'] = edges

    bm.edges.ensure_lookup_table()

    for _bm in temp_bm.values():
        _bm.free()

    if post_process == 'NONE':
        try:
            bmesh.ops.remove_doubles(bm, verts=list(vert_map.values()), dist=0.001)
            bm.verts.ensure_lookup_table()
            bm.edges.ensure_lookup_table()
            bm.normal_update()
            for bisect_object in bisect_output.keys():
                bisect_output[bisect_object]['verts'] = [v for v in bisect_output[bisect_object]['verts'] if v is not None and v.is_valid]
                bisect_output[bisect_object]['edges'] = [e for e in bisect_output[bisect_object]['edges'] if e is not None and e.is_valid]
            return True, bisect_output
        except ValueError as e:
            print(f"remove_doubles ValueError: {e}")
            return False, "REMOVE_DOUBLES_ERROR"

    return True, bisect_output


#MARK: Bisect Objects into Edit Object from Line 2D
def bisect_objects_into_edit_object_from_line_2d(context: Context, line_a: Vector, line_b: Vector, merge_closer_edge_loops: bool = True) -> tuple[bool, str]:
    """
    Creates a joined temporary BMesh from source_objects,
    bisects it with a plane defined by the line in 2D space,
    and copies the resulting cut verts/edges into the active edit object.
    
    Args:
        context (Context): The Blender context.
        line_a (Vector): The A point of the line.
        line_b (Vector): The B point of the line.
        merge_closer_edge_loops (bool, optional): Whether to merge
        the edge loops that are closer to each other. Defaults to True.

    Returns:
        tuple[bool, str]: A tuple containing a boolean indicating
        whether the bisect operation was successful, and a string
        with the reason for failure if the operation was not successful.
    """
    edit_object = context.edit_object

    def _restore_mode(ok: bool = False):
        nonlocal edit_object
        if ok:
            bm.to_mesh(edit_object.data)
        bpy.ops.object.select_all(action='DESELECT')
        edit_object.select_set(True)
        context.view_layer.objects.active = edit_object
        bpy.ops.object.mode_set(False,mode='EDIT')

    bpy.ops.object.mode_set(False, mode='OBJECT')

    xmin = min(line_a.x, line_b.x) - 1
    ymin = min(line_a.y, line_b.y) - 1
    xmax = max(line_a.x, line_b.x) + 1
    ymax = max(line_a.y, line_b.y) + 1
    bpy.ops.view3d.toggle_xray()
    bpy.ops.view3d.select_box(
        False,
        xmin=int(xmin),
        ymin=int(ymin),
        xmax=int(xmax),
        ymax=int(ymax),
        wait_for_input=False,
        mode='SET'
    )
    bpy.ops.view3d.toggle_xray()

    source_objects = set(context.selected_objects)
    if edit_object in source_objects:
        source_objects.add(edit_object)

    # Calculate the plane from the line in 2D space.
    plane_co, plane_no = _plane_from_line_2d(context, line_a, line_b, apply_edit_object_transform=False)

    bm: BMesh = bmesh.new(use_operators=True) # we will use remove_doubles in the bisect_objects_into_bmesh function
    bm.from_object(edit_object, context.evaluated_depsgraph_get())

    # Bisect the mesh with the plane.
    ok, msg = bisect_objects_into_bmesh(
        context=context,
        source_objects=source_objects,
        bm=bm,
        plane_co=plane_co,
        plane_no=plane_no,
        separate=True,
        post_process='BOOLEAN_UNION'
    )
    if not ok:
        _restore_mode()
        return ok, msg

    # Raycast bm in the center of the line to get the closer vert.
    if merge_closer_edge_loops:
        context.view_layer.objects.active = edit_object
        bisect_data: dict[Object, dict[str, list]] = msg
        print(f"len(bisect_data)={len(bisect_data)}")
        for obj, data in bisect_data.items():
            print(f"{obj.name if hasattr(obj, 'name') else obj}: len(verts)={len(data['verts'])}, len(edges)={len(data['edges'])}")
        # boundaries = find_all_boundaries(cut_edges)
        # print(f"len(boundaries)={len(boundaries)}")
        # for boundary_index, boundary in enumerate(boundaries):
        #     print(f"{boundary_index}: len(boundary)={len(boundary)}")

    
    _restore_mode(ok=True)

    return True, "SUCCESS"


def get_mesh_volume_depth_at_region_point(context: Context, region_coord: Vector) -> float:
    """Get the volume depth of the mesh at the given region coordinate.

    Args:
        context (Context): The Blender context.
        region_coord (Vector): The region coordinate.

    Returns:
        float: The volume depth of the mesh at the given region coordinate.
    """
    first_raycast_info = raycast_scene(context, region_coord)
    if first_raycast_info is None:
        raise ValueError(f"get_mesh_depth_at_region_point: raycast_scene failed. region_coord={region_coord}")

    # Move the ray origin to the projected point.
    new_location = first_raycast_info.location - first_raycast_info.normal * 0.001

    # Raycast again but to the other side of the mesh.
    second_raycast_info = raycast_scene(context, new_location)
    if second_raycast_info is None:
        raise ValueError(f"get_mesh_depth_at_region_point: raycast_scene failed. region_coord={region_coord}")

    vec = second_raycast_info.location - first_raycast_info.location
    return vec.length * 2.0


#MARK: Ring Loopcut from Line 2D
def ring_loopcut_from_line_2d(context: Context, bm: BMesh, line_a: Vector, line_b: Vector, number_cuts: int = 1) -> None:
    """Make a ring-loop-cut on the mesh based on a 2d line.
    This needs to be done over an edit mesh with existing geometry in the cut area, and not over an empty area in the edit mesh,
    even if another mesh behind has actual geometry, as it won't work.

    Args:
        context (Context): The Blender context.
        bm (BMesh): The BMesh object.
        line_a (Vector): The A point of the line.
        line_b (Vector): The B point of the line.
        number_cuts (int): The number of cuts to make.
    """
    # Calculate the plane from the line in 2D space.
    plane_co, plane_no = _plane_from_line_2d(context, line_a, line_b)
    
    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    res = bmesh.ops.bisect_plane(
        bm,
        geom=geom,
        plane_co=plane_co,
        plane_no=plane_no,
        clear_outer=False,
        clear_inner=False,
    )
    if number_cuts > 1:
        cut_edges = [g for g in res.get('geom_cut', []) if isinstance(g, BMEdge)]
        if cut_edges:
            bmesh.ops.subdivide_edges(bm, edges=cut_edges, cuts=number_cuts - 1)
    bmesh.update_edit_mesh(context.edit_object.data, destructive=True)


#MARK: Wrap Mesh from Line 2D
def wrap_mesh_from_line_2d(context: Context, bm: BMesh, line_a: Vector, line_b: Vector, number_cuts: int = 8) -> None:
    """Wrap meshes in scene based on a 2d line.
    And make a ring-edge-loop in the provided bmesh that wrap those meshes in the scene.

    Args:
        context (Context): The Blender context.
        bm (BMesh): The BMesh object.
        line_a (Vector): The A point of the line.
        line_b (Vector): The B point of the line.
        number_cuts (int): The number of cuts to make.
    """
    if context.mode != 'EDIT_MESH':
        return
    if (line_b - line_a).length == 0:
        return
    center = (line_a + line_b) * 0.5
    center_hit = raycast_scene(context, center)
    if center_hit is None or not center_hit.hit:
        return
    line_a_3d = region_2d_to_location_3d(context.region, context.region_data, line_a, center_hit.location)
    line_b_3d = region_2d_to_location_3d(context.region, context.region_data, line_b, center_hit.location)
    u = line_b_3d - line_a_3d
    if u.length == 0:
        return
    u.normalize()
    view_dir = get_view_vector(context, center)
    plane_normal = view_dir.cross(u)
    if plane_normal.length == 0:
        return
    v = plane_normal.cross(u)
    if v.length == 0:
        return
    v.normalize()
    radius = (line_b_3d - line_a_3d).length * 0.5
    center_samples = max(number_cuts * 6, 32)
    center_candidates: list[Vector] = []
    view_dir = get_view_vector(context, center)
    for i in range(center_samples):
        angle = i * 2 * pi / center_samples
        target = center_hit.location + u * (cos(angle) * radius) + v * (sin(angle) * radius)
        coord = location_3d_to_region_2d(context.region, context.region_data, target, default=None)
        if coord is None:
            continue
        info = raycast_scene(context, coord)
        if info is None or not info.hit:
            continue
        back_info = raycast_scene(context, info.location + view_dir * 0.002)
        if back_info is not None and back_info.hit:
            center_candidates.append((info.location + back_info.location) * 0.5)
    if center_candidates:
        center_est = sum(center_candidates, Vector((0.0, 0.0, 0.0))) / len(center_candidates)
    else:
        center_est = center_hit.location
    ring_steps = max(number_cuts, 3)
    depsgraph = context.evaluated_depsgraph_get()
    hits: list[Vector] = []
    for i in range(ring_steps):
        angle = i * 2 * pi / ring_steps
        dir_world = (u * cos(angle) + v * sin(angle)).normalized()
        origin = center_est + dir_world * 0.0001
        hit = context.scene.ray_cast(depsgraph, origin, dir_world)
        if hit[0]:
            hits.append(hit[1])
            continue
        hit = context.scene.ray_cast(depsgraph, origin, -dir_world)
        if hit[0]:
            hits.append(hit[1])
    if len(hits) < 3:
        return
    mw_inv = context.edit_object.matrix_world.inverted()
    ring_verts: list[BMVert] = []
    for p in hits:
        ring_verts.append(bm.verts.new(mw_inv @ p))
    bm.verts.ensure_lookup_table()
    for i in range(len(ring_verts)):
        v1 = ring_verts[i]
        v2 = ring_verts[(i + 1) % len(ring_verts)]
        try:
            bm.edges.new((v1, v2))
        except ValueError:
            pass
    bmesh.update_edit_mesh(context.edit_object.data, destructive=True)



# MARK: Align Edge Loop

def align_AB_verts_edge_loop_to_line_2d(
        context: Context,
        bm: BMesh,
        a_vert: BMVert,
        b_vert: BMVert,
        line_2d_a: Vector,
        line_2d_b: Vector,
    ) -> bool:
    """Align an edge loop to a 2D line.

    Args:
        context (Context): The Blender context.
        edge_loop (list[BMEdge]): The edge loop to align.
        line_a (Vector): The A point of the line.
        line_b (Vector): The B point of the line.
    """
    if a_vert is b_vert:
        print("TopoDraw.handle_shape_i: align_AB_verts_edge_loop_to_line_2d failed: a_vert is b_vert")
        return False

    edge_loop = get_edge_loop_between_verts(bm, a_vert, b_vert, return_type='VERT')
    if edge_loop is None or len(edge_loop) == 0:
        print("TopoDraw.handle_shape_i: align_AB_verts_edge_loop_to_line_2d failed: edge_loop is None or len(edge_loop) == 0")
        return False

    n_verts = len(edge_loop)
    if n_verts < 2:
        print("TopoDraw.handle_shape_i: align_AB_verts_edge_loop_to_line_2d failed: n_verts < 2")
        return False
    
    region, rv3d = context.region, context.region_data

    points_along_line_2d = [
        line_2d_a.lerp(line_2d_b, i / (n_verts - 1))
        for i in range(n_verts)
    ]

    points_along_line_2d = points_along_line_2d[1:-1]  # Exclude first and last points (A and B verts)

    for i, vert in enumerate(edge_loop[1:-1]):  # Exclude first and last verts (A and B verts)
        target_2d = points_along_line_2d[i]
        raycast_hit = raycast_scene(context, target_2d)
        if raycast_hit is None or not raycast_hit.hit:
            continue
        vert.co = raycast_hit.location

    return True


# MAR: Close Geometry by Line 2D

def create_geometry_between_verts(
        context: Context,
        bm: BMesh,
        a_vert: BMVert,
        b_vert: BMVert
    ) -> bool:
    """Create a geometry between two vertices.

    Args:
        context (Context): The Blender context.
        bm (BMesh): The BMesh to close.
        a_vert (BMVert): The A vert of the line.
        b_vert (BMVert): The B vert of the line.
    """
    if a_vert is b_vert:
        print("close_geometry_between_verts failed: a_vert is b_vert")
        return False
    
    if not is_wire_or_boundary(a_vert) or not is_wire_or_boundary(b_vert):
        print("close_geometry_between_verts failed: a_vert or b_vert is not wire or boundary")
        return False
    
    def _create_face(verts) -> BMFace | None:
        return create_face_from_bmverts_and_raw_coords(context, bm, *verts)

    def _walk_boundary_excluding_edges(blocked_edges: set[BMEdge], max_walk: int = 200) -> tuple[list[BMVert], list[BMEdge]]:
        visited: set[BMVert] = {a_vert}
        parent: dict[BMVert, BMVert] = {}
        parent_edge: dict[BMVert, BMEdge] = {}
        queue: list[BMVert] = [a_vert]
        while queue and len(visited) <= max_walk:
            v = queue.pop(0)
            if v == b_vert:
                verts_path: list[BMVert] = []
                edges_path: list[BMEdge] = []
                cur = b_vert
                while cur != a_vert:
                    verts_path.append(cur)
                    edges_path.append(parent_edge[cur])
                    cur = parent[cur]
                verts_path.reverse()
                edges_path.reverse()
                if verts_path:
                    return (verts_path[:-1], edges_path)
                return ([], edges_path)
            for edge in v.link_edges:
                if edge in blocked_edges:
                    continue
                if not (edge.is_boundary or edge.is_wire):
                    continue
                other_vert = edge.other_vert(v)
                if other_vert in visited:
                    continue
                visited.add(other_vert)
                parent[other_vert] = v
                parent_edge[other_vert] = edge
                queue.append(other_vert)
        return ([], [])

    # Triangle case.
    # Both vertices share an edge.
    if shared_vert := vert_shared_vert(a_vert, b_vert):
        return _create_face([a_vert, shared_vert, b_vert]) is not None

    # verts_path is the path of vertices between a_vert and b_vert.
    # edges_path is the path of edges between a_vert and b_vert.
    verts_path, edges_path = walk_boundary(a_vert, b_vert, wire_walk=True)
    if not verts_path:
        # Edge case.
        if len(a_vert.link_edges) <= 1 or len(b_vert.link_edges) <= 1:
            # Connect loose verts and loose wire edges.
            bm.edges.new((a_vert, b_vert))
            bm.verts.ensure_lookup_table()
            bm.edges.ensure_lookup_table()
            return True
        
        print("close_geometry_between_verts failed: no path exists between a_vert and b_vert")
        return False

    if len(verts_path) == 2:
        alt_verts_path, _ = _walk_boundary_excluding_edges(set(edges_path))
        if len(alt_verts_path) == 2:
            main_quad_created = _create_face([a_vert, *verts_path, b_vert]) is not None
            alt_quad_created = _create_face([a_vert, *alt_verts_path, b_vert]) is not None
            return main_quad_created or alt_quad_created

    if len(verts_path) > 2: # skip n-gons!
        # Grid fill if has this pattern:
        '''
         __•A         B•__
        |__|           |__|
        |__|__.__.__.__|__|
        |__|__|__|__|__|__|
        
        # For N verts, there will be N-1 edges.
        '''
        segments = defaultdict(list)
        verts_path = [a_vert, *verts_path, b_vert]
        segment_index = 0
        for e_idx, edge in enumerate(edges_path):
            v1 = verts_path[e_idx]
            v2 = verts_path[e_idx + 1]
            if e_idx != 0 and len(v1.link_faces) > 2:
                segment_index += 1
            segments[segment_index].append((edge, v1, v2))

        if segment_index == 2 and len(segments[0]) == len(segments[2]):
            d_vert = segments[0][-1][2]
            c_vert = segments[2][0][1]
            if create_grid_from_ABCD(context, bm, a_vert, b_vert, c_vert, d_vert, edge_path=edges_path):
                return True
            print("close_geometry_between_verts failed: create_grid_from_ABCD failed")
        else:
            print(f"close_geometry_between_verts failed: segment_count = {segment_index}, len(segments[0]) = {len(segments[0])}, len(segments[2]) = {len(segments[2])}")

        print("close_geometry_between_verts failed: n-gons are not supported. verts_path: ", verts_path, "- edges_path: ", edges_path)
        return False

    # Create a quad face from the path.
    return _create_face([a_vert, *verts_path, b_vert]) is not None

    '''
    sides = sum(1 for v in verts_path if len(v.link_edges) != 3)
    verts_path = [a_vert, *verts_path, b_vert]

    if sides == 3:
        ab_edge = bm.edges.new((a_vert, b_vert))
        res = bmesh.ops.subdivide_edges(bm, edges=[ab_edge], cuts=len(verts_path) - sides)
        if not res:
            print("close_geometry_between_verts failed: bmesh.ops.subdivide_edges failed")
            return False
        bm.edges.ensure_lookup_table()
        subdiv_edges = [e for e in res['geom'] if isinstance(e, BMEdge)]
        edges_path = [*subdiv_edges, *edges_path]

    res = bmesh.ops.triangle_fill(bm, edges=edges_path, use_beauty=True)
    if not res:
        print("close_geometry_between_verts failed: bmesh.ops.holes_fill failed")
        return False

    faces = [f for f in res['geom'] if isinstance(f, BMFace)]
    if faces:
        for face in faces:
            face.select = True
        bmesh.update_edit_mesh(context.edit_object.data)

    bpy.ops.mesh.tris_convert_to_quads(False, face_threshold=radians(60), shape_threshold=radians(60))
    '''

    return True
