


from dataclasses import dataclass
from math import dist
from typing import Callable, List, Literal, Optional, Set, Tuple, Union

import bmesh
from bmesh.types import BMesh, BMFace, BMEdge, BMVert, BMLoop
from bpy.types import Object, Context, Event
from bpy_extras.view3d_utils import location_3d_to_region_2d
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

from .view_utils import get_ray_origin, get_view_vector
from .geom_utils import closest_segment_to_point, is_face_facing_view_vector


@dataclass
class RaycastInfo:
    hit: bool
    location: Vector
    normal: Vector
    index: int
    object: Object
    matrix: Matrix

    def __bool__(self) -> bool:
        return self.hit


def raycast_scene(context: Context, event: Event | Vector)-> RaycastInfo:
    """
    Casts a ray from the mouse cursor to the scene.
    
    Parameters:
        context (Context): The Blender context.
        event (Event | Vector): The event or vector to cast the ray from.
            If an event is provided, the ray is cast from the mouse cursor position.
            If a vector is provided, the ray is cast from that point.
    
    Returns:
        RaycastInfo: The result of the raycast.
    """
    if isinstance(event, (Vector, tuple, list)) and len(event) in {2, 3}:
        coord = event
    elif isinstance(event, Event):
        coord = Vector((event.mouse_region_x, event.mouse_region_y))
    else:
        raise ValueError(f"Invalid event type: {type(event)}")
    if len(coord) == 2:
        return RaycastInfo(
            *context.scene.ray_cast(
                context.evaluated_depsgraph_get(),
                get_ray_origin(context, coord),
                get_view_vector(context, coord)
            )
        )
    elif len(coord) == 3:
        return RaycastInfo(
            *context.scene.ray_cast(
                context.evaluated_depsgraph_get(),
                coord,
                get_view_vector(context, location_3d_to_region_2d(context.region, context.region_data, coord))
            )
        )
    else:
        raise ValueError(f"Invalid coordinate length: {len(coord)}")


def raycast_object(context: Context, event: Event | Vector, object: Object) -> RaycastInfo:
    """
    Casts a ray from the mouse cursor to the scene.
    
    Parameters:
        context (Context): The Blender context.
        event (Event | Vector): The event or vector to cast the ray from.
            If an event is provided, the ray is cast from the mouse cursor position.
            If a vector is provided, the ray is cast from that point.
        object (Object): The object to cast the ray against.
    
    Returns:
        RaycastInfo: The result of the raycast.
    """
    coord = event if isinstance(event, Vector) else event.mouse_region_x, event.mouse_region_y
    eval_ob = context.object.evaluated_get(context.evaluated_depsgraph_get())
    if len(coord) == 2:
        return RaycastInfo(
            *eval_ob.ray_cast(get_ray_origin(context, coord), get_view_vector(context, coord)),
            object,
            eval_ob.matrix_world,
        )
    elif len(coord) == 3:
        return RaycastInfo(
            *eval_ob.ray_cast(coord, get_view_vector(context, location_3d_to_region_2d(context.region, context.region_data, coord))),
            object,
            eval_ob.matrix_world,
        )
    else:
        raise ValueError(f"Invalid coordinate length: {len(coord)}")


@dataclass
class BVHTreeRaycastInfo:
    location: Vector | None = None
    normal: Vector | None = None
    index: int | None = None
    distance: float | None = None
    location_2d: Vector | None = None
    bm_face: BMFace | None = None

    def copy(self) -> 'BVHTreeRaycastInfo':
        return BVHTreeRaycastInfo(
            self.location.copy() if self.location is not None else None,
            self.normal.copy() if self.normal is not None else None,
            self.index,
            self.distance,
            self.location_2d.copy() if self.location_2d is not None else None,
            self.bm_face,
        )

    @property
    def hit(self) -> bool:
        return self.index is not None

    @property
    def closest_vert(self) -> Optional[BMVert]:
        """
        Get the closest vertex to the hit location.
        
        Returns:
            Optional[BMVert]: The closest vertex, or None if no vertex is found.
        """
        if self.bm_face is None or not self.bm_face.is_valid:
            return None
        closest_vert = None
        min_distance = float('inf')
        for vert in self.bm_face.verts:
            vert_distance = dist(vert.co, self.location)
            if vert_distance < min_distance:
                min_distance = vert_distance
                closest_vert = vert
        return closest_vert

    @property
    def closest_edge(self) -> Optional[BMEdge]:
        """
        Get the closest edge to the hit location.
        
        Returns:
            Optional[BMEdge]: The closest edge, or None if no edge is found.
        """
        if self.bm_face is None or not self.bm_face.is_valid:
            return None
        closest_edge = None
        min_distance = float('inf')
        for edge in self.bm_face.edges:
            v1, v2 = edge.verts
            edge_length: float = edge.calc_length()
            edge_corner: float = edge_length * 0.01
            edge_center: Vector = (v2.co + v1.co) * 0.5
            edge_dir_v1: Vector = (v2.co - v1.co).normalized()
            edge_v1_off: Vector = v1.co + edge_dir_v1 * edge_corner
            edge_dir_v2: Vector = edge_dir_v1 * -1
            edge_v2_off: Vector = v2.co + edge_dir_v2 * edge_corner
            nearest_point_dist = min([dist(p, self.location) for p in (edge_center, edge_v1_off, edge_v2_off)])
            if nearest_point_dist < min_distance:
                min_distance = nearest_point_dist
                closest_edge = edge
        return closest_edge

    @property
    def closest_corner(self) -> Optional[Tuple[BMVert, Tuple[BMEdge, BMEdge]]]:
        """
        Get the closest corner to the hit location.
        
        Returns:
            Optional[Tuple[BMVert, Tuple[BMEdge, BMEdge]]]: The closest corner, or None if no corner is found.
            The tuple contains the vertex, and both edges conforming the closest corner.
        """
        if self.bm_face is None or not self.bm_face.is_valid:
            return None
        closest_vert = self.closest_vert
        if closest_vert is None:
            return None
        # Get the edges connected to the closest vertex,
        # that are also part of the hit face.
        connected_edges = [edge for edge in closest_vert.link_edges if edge in self.bm_face.edges]
        if len(connected_edges) != 2:
            return None
        return closest_vert, connected_edges

    @property
    def closest_adjacent_face(self) -> Optional[BMFace]:
        """
        Get the closest adjacent face to the hit face.
        
        Returns:
            Optional[BMFace]: The closest adjacent face, or None if no face is found.
        """
        if self.bm_face is None or not self.bm_face.is_valid:
            return None
        closest_face = None
        min_distance = float('inf')
        for edge in self.bm_face.edges:
            for face in edge.link_faces:
                if face != self.bm_face:
                    face_distance = dist(face.calc_center_median(), self.location)
                    if face_distance < min_distance:
                        min_distance = face_distance
                        closest_face = face
        return closest_face

    @property
    def adjacent_faces_by_edges(self) -> Set[BMFace]:
        """
        Get the adjacent faces to the hit face, by shared edges.
        
        Returns:
            Set[BMFace]: The adjacent faces, or an empty set if no face is found.
        """
        if self.bm_face is None or not self.bm_face.is_valid:
            return set()
        adjacent_faces = set()
        for edge in self.bm_face.edges:
            for face in edge.link_faces:
                if face != self.bm_face:
                    adjacent_faces.add(face)
        return adjacent_faces

    @property
    def adjacent_faces_by_verts(self) -> Set[BMFace]:
        """
        Get the adjacent faces to the hit face, by shared vertices.
        
        Returns:
            Set[BMFace]: The adjacent faces, or an empty set if no face is found.
        """
        if self.bm_face is None or not self.bm_face.is_valid:
            return set()
        # Should not share any edge with the adjacent faces!
        adjacent_faces = set()
        hit_face_edges = set(self.bm_face.edges)
        for vert in self.bm_face.verts:
            for face in vert.link_faces:
                if face != self.bm_face and not hit_face_edges & set(face.edges):
                    adjacent_faces.add(face)
        return adjacent_faces

    def get_closest_primitive(self, context: Context, primitive_types: set[str] = {'FACE', 'EDGE', 'VERT'}, edge_corner_factor: float = 0.092, filter: Callable[[BMFace | BMEdge | BMVert], bool] = None) -> Tuple[BMFace | BMEdge | BMVert, str, List[Vector]]:
        """
        Get the closest primitive to the raycast location.
        
        Parameters:
            primitive_types (set[str]): The primitive types to consider.
        """
        obj = context.edit_object if context.mode == 'EDIT_MESH' else context.active_object
        mw = obj.matrix_world if obj is not None else Matrix.Identity(4)

        if primitive_types == {'FACE'}:
            if self.bm_face is None or not self.bm_face.is_valid:
                return None
            return self.bm_face, self.bm_face.index, 'FACE', dist(self.bm_face.calc_center_median(), self.location), [mw @ vert.co for vert in self.bm_face.verts]

        distances = []
        bm_face = self.bm_face
        loc = self.location
        if 'FACE' in primitive_types:
            if filter is None or filter(bm_face):
                distances.append((bm_face, 'FACE', dist(bm_face.calc_center_median(), loc)))
        if 'EDGE' in primitive_types:
            # Make edge (line segment) shorter from both ends by a 5% per end.
            segments = []
            for edge in bm_face.edges:
                if filter is None or filter(edge):
                    edge_corner = edge_corner_factor * edge.calc_length()
                    edge_vec = (edge.verts[1].co - edge.verts[0].co).normalized()
                    edge_v1_off = edge.verts[0].co + edge_vec * edge_corner
                    edge_v2_off = edge.verts[1].co - edge_vec * edge_corner
                    segments.append((edge_v1_off, edge_v2_off))
            if len(segments) == 0:
                return None
            index, d = closest_segment_to_point(loc, segments)
            distances.append((bm_face.edges[index], 'EDGE', d))
        if 'VERT' in primitive_types:
            for vert in bm_face.verts:
                if filter is None or filter(vert):
                    distances.append((vert, 'VERT', dist(vert.co, loc)))
        if len(distances) == 0:
            return None
        min_distance = float('inf')
        closest_primitive = None
        for primitive, primitive_type, distance in distances:
            if distance < min_distance:
                min_distance = distance
                closest_primitive = primitive

        if closest_primitive is None:
            return None
        primitive_coords = []
        if isinstance(closest_primitive, BMFace):
            primitive_type = 'FACE'
            for vert in closest_primitive.verts:
                primitive_coords.append(mw @ vert.co)
        elif isinstance(closest_primitive, BMEdge):
            primitive_type = 'EDGE'
            primitive_coords.append(mw @ closest_primitive.verts[0].co)
            primitive_coords.append(mw @ closest_primitive.verts[1].co)
        elif isinstance(closest_primitive, BMVert):
            primitive_type = 'VERT'
            primitive_coords.append(mw @ closest_primitive.co)
        else:
            raise ValueError(f"Unknown primitive type: {closest_primitive}")
        return closest_primitive, closest_primitive.index, primitive_type, min_distance, primitive_coords

    def is_adjacent(self, other: 'BVHTreeRaycastInfo', by_verts: bool = False, get_shared_edge: bool = False) -> bool | BMEdge:
        """
        Check if the other raycast info is adjacent to this one.
        
        Parameters:
            other (BVHTreeRaycastInfo): The other raycast info.
            by_verts (bool): Whether to check adjacency by shared vertices or not (by edges by default).

        Returns:
            bool: True if the other raycast info is adjacent to this one, False otherwise.
        """
        if self.bm_face is None or other.bm_face is None:
            return False
        if not self.bm_face.is_valid or not other.bm_face.is_valid:
            return False
        edges = set(self.bm_face.edges)
        other_edges = set(other.bm_face.edges)
        shared_edge = edges.intersection(other_edges)
        if not shared_edge:
            return None if get_shared_edge else False
        if get_shared_edge:
            return shared_edge.pop()
        return True


class BVHTreeRaycaster:
    _bm: BMesh
    _bvhtree: BVHTree
    _mesh_uuid: int

    def __init__(self, context: Context, existing_bmesh: BMesh = None):
        self._bm = None
        self._mesh_uuid = id(context.edit_object.data) if context.mode == 'EDIT_MESH' else id(context.active_object.data)
        self._bvhtree = BVHTree.FromBMesh(existing_bmesh if existing_bmesh else self.ensure_bmesh(context))

    def ensure_bmesh(self, context: Context, select_mode: set[str] = {'EDGE'}) -> BMesh:
        """
        Get the bmesh for the current edit object.
        
        Parameters:
            context (Context): The Blender context.
        
        Returns:
            BMesh: The bmesh for the current edit object.
        """
        if context.mode == 'EDIT_MESH':
            mesh_id = id(context.edit_object.data)
        else:
            mesh_id = id(context.active_object.data)

        if self._mesh_uuid != mesh_id:
            if self._bm is not None and self._bm.is_valid:
                self.clear_bmesh()
            self._bm = None
            self._mesh_uuid = mesh_id
        if self._bm is None or not self._bm.is_valid:
            if context.mode == 'EDIT_MESH':
                bm = bmesh.from_edit_mesh(context.edit_object.data)
            else:
                bm = bmesh.new()
                bm.from_object(context.active_object, context.evaluated_depsgraph_get())
            bm.edges.ensure_lookup_table()
            bm.edges.index_update()
            bm.faces.ensure_lookup_table()
            bm.faces.index_update()
            self._bvhtree = BVHTree.FromBMesh(bm)
            self._bm = bm
        self._bm.select_mode = select_mode
        return self._bm

    def clear_bmesh(self):
        """
        Clear the bmesh.
        """
        self._bm = None
        self._bvhtree = None

    def do_raycast(self, context: Context, event: Event | Vector) -> Optional[BVHTreeRaycastInfo]:
        """
        Casts a ray from the mouse cursor to the scene.
        
        Parameters:
            context (Context): The Blender context.
            event (Event | Vector): The event or vector to cast the ray from.
                If an event is provided, the ray is cast from the mouse cursor position.
                If a vector is provided, the ray is cast from that point.
            _previz (set[str]): preselection highlight values.

        Returns:
            bool: True if the ray hit something, False otherwise.
        """
        bm = self.ensure_bmesh(context)

        coord = event if isinstance(event, (Vector, tuple)) else Vector((event.mouse_region_x, event.mouse_region_y))
        obj = context.edit_object if context.mode == 'EDIT_MESH' else context.active_object
        mw = obj.matrix_world if obj is not None else Matrix.Identity(4)
        mw_inv = mw.inverted()
        ray_origin_ws = get_ray_origin(context, coord)
        ray_dir_ws = get_view_vector(context, coord)
        ray_origin_ls = mw_inv @ ray_origin_ws
        ray_dir_ls = (mw_inv.to_3x3() @ ray_dir_ws).normalized()
        location, normal, index, distance = self._bvhtree.ray_cast(
            ray_origin_ls,
            ray_dir_ls,
        )
        if index is None:
            return None

        try:
            bm_face = bm.faces[index]
        except IndexError:
            self.clear_bmesh()
            return None

        if not is_face_facing_view_vector(context, context.edit_object, bm_face, coord):
            return None

        return BVHTreeRaycastInfo(location, normal, index, distance, location_2d=coord, bm_face=bm_face)

    def __del__(self):
        self.clear_bmesh()

