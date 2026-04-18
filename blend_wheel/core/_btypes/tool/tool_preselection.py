from dataclasses import dataclass
from math import dist
from typing import List, Literal, Optional, Set

from bmesh.types import BMEdge, BMFace, BMVert
from bpy.types import Context, Event
from bpy_extras.view3d_utils import location_3d_to_region_2d
from mathutils import Matrix, Vector

from ...utils.raycast_utils import BVHTreeRaycastInfo, BVHTreeRaycaster, raycast_scene
from ...utils.geom_utils import closest_point_on_segment, dist_to_segment, get_n_points_around
from ...utils.bmesh import EdgeFinder, VertexFinder, get_boundary_edge_loop, is_wire_or_boundary, walk_closed_boundary
from ...gpu import imm_2d
from .tool_specs import ToolPreselectionSpecs


PRESELECTION_HIGHLLIGHT_VALUES = Literal['FACE', 'EDGE', 'VERT', 'EDGE_LOOP_BOUNDARY', 'EDGE_BOUNDARY', 'EDGE_LOOP_RING']


NO_HIT_RING_COUNT = 8
USE_DEBUG = False


def _is_edge_loop_closed(edges: list[BMEdge]) -> bool:
    """True when the given edges form a closed cycle (every vertex has degree 2)."""
    if len(edges) < 3:
        return False
    degree: dict[BMVert, int] = {}
    for e in edges:
        for v in e.verts:
            degree[v] = degree.get(v, 0) + 1
    return all(d == 2 for d in degree.values())


class PreselectionInfo:
    _instance: 'PreselectionInfo' = None
    bvhtree_raycaster: BVHTreeRaycaster = None
    vertex_finder: VertexFinder | None = None
    edge_finder: EdgeFinder | None = None
    
    raycast_info: BVHTreeRaycastInfo | None = None
    primitive: BMFace | BMEdge | BMVert | None = None
    primitive_index: int | None = None
    primitive_type: PRESELECTION_HIGHLLIGHT_VALUES | None = None
    distance: float | None = None
    primitive_coords: List[Vector] | None = None
    scene_hit_location: Vector | None = None
    scene_hit_normal: Vector | None = None
    frozen: bool = False

    def get_primitive_if_type(self, primitive_type: PRESELECTION_HIGHLLIGHT_VALUES) -> BMFace | BMEdge | BMVert | None:
        if self.primitive_type == primitive_type:
            return self.primitive
        return None

    @property
    def primitive_hash(self) -> int | tuple[int, ...] | None:
        if self.primitive is None:
            return None
        if self.primitive_type in ('EDGE_LOOP_BOUNDARY', 'EDGE_LOOP_RING') or isinstance(self.primitive, (list, tuple)):
            return tuple(hash(p) for p in self.primitive)
        return hash(self.primitive)

    @classmethod
    def get(cls) -> 'PreselectionInfo':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def freeze(cls) -> None:
        """Freeze the current preselection state.

        While frozen, :meth:`update` becomes a no-op so micro-movements after a
        PRESS event cannot clear or replace the primitive that was under the cursor
        at press time.  The frozen visual stays on screen until :meth:`unfreeze`
        or :meth:`clear` is called.
        """
        cls.get().frozen = True

    @classmethod
    def unfreeze(cls) -> None:
        """Resume normal preselection updates (inverse of :meth:`freeze`)."""
        cls.get().frozen = False

    @classmethod
    def get_bvhtree_raycaster(cls, context: Context) -> BVHTreeRaycaster:
        info = cls.get()
        if info.bvhtree_raycaster is None:
            ## print('PreselectionInfo.get_bvhtree_raycaster: creating BVHTreeRaycaster')
            info.bvhtree_raycaster = BVHTreeRaycaster(context)
        return info.bvhtree_raycaster

    @classmethod
    def get_vertex_finder(cls, context: Context) -> VertexFinder:
        info = cls.get()
        if info.vertex_finder is None or not info.vertex_finder.is_valid:
            ## print('PreselectionInfo.get_vertex_finder: creating VertexFinder')
            bvhtree_raycaster = cls.get_bvhtree_raycaster(context)
            bm = bvhtree_raycaster.ensure_bmesh(context)
            info.vertex_finder = VertexFinder(bm, '3D', v_filter=is_wire_or_boundary)
        return info.vertex_finder

    @classmethod
    def get_edge_finder(cls, context: Context) -> EdgeFinder:
        info = cls.get()
        if info.edge_finder is None or not info.edge_finder.is_valid:
            ## print('PreselectionInfo.get_edge_finder: creating EdgeFinder')
            bvhtree_raycaster = cls.get_bvhtree_raycaster(context)
            bm = bvhtree_raycaster.ensure_bmesh(context)
            info.edge_finder = EdgeFinder(bm, samples=3, e_filter=is_wire_or_boundary)
        return info.edge_finder

    @classmethod
    def update(cls, context: Context, mouse_pos: Vector, specs: ToolPreselectionSpecs, is_retry: bool = False, callback=None):
        if cls.get().frozen:
            return
        if context.mode != 'EDIT_MESH':
            return
        geom_types = specs.get_geom_types(context)
        if geom_types == set():
            return

        info = cls.get()
        last_primitive_index = info.primitive_index

        # ── EDGE_BOUNDARY: highlight the closest boundary/wire edge of the hit face ──
        if 'EDGE_BOUNDARY' in geom_types:
            def _eb_check_hover_exit():
                nonlocal last_primitive_index, info
                info.clear()
                if last_primitive_index is not None:
                    context.region.tag_redraw()
                    if callback is not None:
                        callback(context, mouse_pos, info)

            obj = context.edit_object if context.mode == 'EDIT_MESH' else context.active_object
            mw = obj.matrix_world if obj is not None else Matrix.Identity(4)
            snap_radius = max(3.0, specs.get_snap_radius(context)) * context.preferences.system.dpi / 72

            raycast_info = cls.get_bvhtree_raycaster(context).do_raycast(context, mouse_pos)

            # Retry with a ring of points if there was no direct hit.
            if (raycast_info is None or not raycast_info.hit) and not is_retry:
                retry_coords = get_n_points_around(mouse_pos, snap_radius, NO_HIT_RING_COUNT)
                closest_raycast_info: BVHTreeRaycastInfo | None = None
                min_distance = float('inf')
                for retry_coord in retry_coords:
                    if ri := cls.get_bvhtree_raycaster(context).do_raycast(context, retry_coord):
                        loc_2d = location_3d_to_region_2d(context.region, context.region_data, mw @ ri.location, default=None)
                        if loc_2d is None:
                            continue
                        d = (loc_2d - mouse_pos).length
                        if d < min_distance:
                            min_distance = d
                            closest_raycast_info = ri
                if closest_raycast_info is not None:
                    raycast_info = closest_raycast_info
                    raycast_info.location_2d = mouse_pos

            if raycast_info is None or not raycast_info.hit:
                _eb_check_hover_exit()
                return

            face = raycast_info.bm_face
            if face is None or not face.is_valid:
                _eb_check_hover_exit()
                return

            boundary_edges = [e for e in face.edges if e.is_boundary or e.is_wire]
            if not boundary_edges:
                _eb_check_hover_exit()
                return

            # Find the boundary edge whose midpoint is closest to the cursor in 2D.
            closest_edge = None
            min_dist_2d = float('inf')
            for e in boundary_edges:
                mid_3d = mw @ ((e.verts[0].co + e.verts[1].co) / 2)
                mid_2d = location_3d_to_region_2d(context.region, context.region_data, mid_3d, default=None)
                if mid_2d is None:
                    continue
                d = (mid_2d - mouse_pos).length
                if d < min_dist_2d:
                    min_dist_2d = d
                    closest_edge = e

            if closest_edge is None:
                closest_edge = boundary_edges[0]  # positional fallback

            index = closest_edge.index
            if last_primitive_index != index:
                context.region.tag_redraw()

            info.raycast_info = raycast_info
            info.primitive = closest_edge
            info.primitive_index = index
            info.primitive_type = 'EDGE_BOUNDARY'
            info.primitive_coords = [mw @ closest_edge.verts[0].co, mw @ closest_edge.verts[1].co]
            info.distance = 0.0

            if callback is not None:
                callback(context, mouse_pos, info)
            return

        # ── OLD! EDGE_LOOP_RING: only closed boundary/wire loops ───────────────────────
        if '_EDGE_LOOP_RING' in geom_types:
            obj = context.edit_object if context.mode == 'EDIT_MESH' else context.active_object
            mw = obj.matrix_world if obj is not None else Matrix.Identity(4)
            snap_radius = max(3.0, specs.get_snap_radius(context)) * context.preferences.system.dpi / 72

            def _elr_check_hover_exit():
                nonlocal last_primitive_index, info
                info.clear()
                if last_primitive_index is not None:
                    context.region.tag_redraw()
                    if callback is not None:
                        callback(context, mouse_pos, info)

            elr_raycast_info = cls.get_bvhtree_raycaster(context).do_raycast(context, mouse_pos)

            # Retry with a ring of sample points if there was no direct hit.
            if (elr_raycast_info is None or not elr_raycast_info.hit) and not is_retry:
                retry_coords = get_n_points_around(mouse_pos, snap_radius, NO_HIT_RING_COUNT)
                closest_elr_ri: BVHTreeRaycastInfo | None = None
                min_distance = float('inf')
                for retry_coord in retry_coords:
                    if ri := cls.get_bvhtree_raycaster(context).do_raycast(context, retry_coord):
                        loc_2d = location_3d_to_region_2d(context.region, context.region_data, mw @ ri.location, default=None)
                        if loc_2d is None:
                            continue
                        d = (loc_2d - mouse_pos).length
                        if d < min_distance:
                            min_distance = d
                            closest_elr_ri = ri
                if closest_elr_ri is not None:
                    elr_raycast_info = closest_elr_ri
                    elr_raycast_info.location_2d = mouse_pos
                    scn_hit = raycast_scene(context, mouse_pos)
                    if scn_hit.hit:
                        elr_raycast_info.distance = (mw @ elr_raycast_info.location - scn_hit.location).length
                        elr_raycast_info.location = scn_hit.location

            if elr_raycast_info is None or not elr_raycast_info.hit:
                _elr_check_hover_exit()
                return

            # Find the closest boundary or wire edge on the hit face.
            elr_result = elr_raycast_info.get_closest_primitive(context, {'EDGE'}, edge_corner_factor=0.092)
            if elr_result is None:
                _elr_check_hover_exit()
                return

            elr_primitive, elr_index, _, elr_distance, _ = elr_result

            if not is_wire_or_boundary(elr_primitive):
                _elr_check_hover_exit()
                return

            # Walk the full boundary / wire loop from this edge.
            loop_edges, loop_coords = get_boundary_edge_loop(elr_primitive, wire_walk=True, get_coords=True)

            # Only accept closed loops.
            if not _is_edge_loop_closed(loop_edges):
                _elr_check_hover_exit()
                return

            # Use the minimum edge index as a stable loop identity for redraw throttling.
            loop_index = min(e.index for e in loop_edges) if loop_edges else elr_index

            if last_primitive_index != loop_index:
                context.region.tag_redraw()

            info.raycast_info = elr_raycast_info
            info.primitive = loop_edges
            info.primitive_index = loop_index
            info.primitive_type = 'EDGE_LOOP_RING'
            info.primitive_coords = [mw @ co for co in loop_coords]
            info.distance = elr_distance

            if callback is not None:
                callback(context, mouse_pos, info)
            return

        if 'EDGE_LOOP_BOUNDARY' not in geom_types:
            gtypes = {'EDGE'} if 'EDGE_LOOP_RING' in geom_types or 'EDGE_LOOP_BOUNDARY' in geom_types else geom_types
            snap_distance = max(0.0001, specs.get_snap_distance(context))
            result = preselect_editmesh_primitive_from_mouse(
                context, mouse_pos, gtypes, snap_distance,
                use_loop='EDGE_LOOP_BOUNDARY' in geom_types,
                use_closed_loop='EDGE_LOOP_RING' in geom_types,
                use_boundary_only=geom_types.intersection({'EDGE_LOOP_BOUNDARY', 'EDGE_LOOP_RING', 'EDGE_BOUNDARY'}) != set()
            )
            if result is None:
                info.clear()
            else:
                info.raycast_info = result.raycast_info
                info.primitive = result.primitive
                info.primitive_index = result.primitive_index
                info.primitive_type = result.primitive_type
                info.distance = result.distance_3d
                info.primitive_coords = result.primitive_coords
                info.scene_hit_location = result.scene_hit_location
                info.scene_hit_normal = result.scene_hit_normal

            if last_primitive_index != info.primitive_index:
                ## print(f'Preselection: {info.primitive_type} {info.primitive_index}')
                context.region.tag_redraw()
                if callback is not None:
                    callback(context, mouse_pos, info)

            return

        def _check_hover_exit():
            nonlocal last_primitive_index, info
            info.clear()
            if last_primitive_index is not None:
                context.region.tag_redraw()
                if callback is not None:
                    callback(context, mouse_pos, info)

        raycast_info = cls.get_bvhtree_raycaster(context).do_raycast(context, mouse_pos)
        obj = context.edit_object if context.mode == 'EDIT_MESH' else context.active_object
        mw = obj.matrix_world if obj is not None else Matrix.Identity(4)
        snap_radius = max(3.0, specs.get_snap_radius(context)) * context.preferences.system.dpi / 72
        snap_distance = max(0.0001, specs.get_snap_distance(context))

        if raycast_info is None or not raycast_info.hit:
            if not is_retry and ('EDGE_LOOP_BOUNDARY' in geom_types or not specs.only_direct_hits):
                retry_coords = get_n_points_around(mouse_pos, snap_radius, NO_HIT_RING_COUNT)
                closest_raycast_info: BVHTreeRaycastInfo | None = None
                min_distance = float('inf')
                for retry_coord in retry_coords:
                    if raycast_info := cls.get_bvhtree_raycaster(context).do_raycast(context, retry_coord):
                        loc_2d = location_3d_to_region_2d(context.region, context.region_data, mw @ raycast_info.location, default=None)
                        if loc_2d is None:
                            continue
                        d = (loc_2d - mouse_pos).length
                        if d < min_distance:
                            min_distance = d
                            closest_raycast_info = raycast_info

                # As the retry coords were virtual ones, we need to set the raycast hit locations (2D and 3D) 
                # to the real mouse position and real hit location found (if any).
                if closest_raycast_info is not None:
                    raycast_info = closest_raycast_info
                    raycast_info.location_2d = mouse_pos
                    scn_raycast_hit = raycast_scene(context, mouse_pos)
                    if scn_raycast_hit.hit:
                        raycast_info.distance = (mw @ raycast_info.location - scn_raycast_hit.location).length
                        raycast_info.location = scn_raycast_hit.location

        # BVHTree raycast method won't work for wire vertices, so we need to use KDTree based VertexFinder utility to check for wire vertices.
        if not is_retry and (raycast_info is None or not raycast_info.hit) and 'VERT' in geom_types:
            # Use vertex finder utility to check for wire vertices...
            with VertexFinder(info.bvhtree_raycaster.ensure_bmesh(context), 'HYBRID', v_filter=lambda v: v.is_wire) as find_vertex:
                if v := find_vertex(context, mouse_pos, dist_2d=snap_radius, dist_3d=snap_distance):
                    info.primitive = v
                    info.primitive_type = 'VERT'
                    info.primitive_index = v.index
                    info.distance = 0.0
                    info.primitive_coords = [mw @ v.co]
                    context.region.tag_redraw()
                    if callback is not None:
                        callback(context, mouse_pos, info)
                    return

        if raycast_info is None or not raycast_info.hit:
            _check_hover_exit()
            if USE_DEBUG:
                print(f"PreselectionInfo: No hit")
            return

        if 'EDGE_LOOP_BOUNDARY' in geom_types:
            _preselection_highlight = {'EDGE'}
        else:
            _preselection_highlight = geom_types
        edge_corner_factor = 0.32 if 'VERT' in geom_types else 0.092
        result = raycast_info.get_closest_primitive(context, _preselection_highlight, edge_corner_factor=edge_corner_factor)
        if result is None:
            _check_hover_exit()
            if USE_DEBUG:
                print(f"PreselectionInfo: No primitive found")
            return

        primitive, index, prim_type, distance, coords = result

        if 'EDGE_LOOP_BOUNDARY' in geom_types:
            if not is_wire_or_boundary(primitive):
                _check_hover_exit()
                if USE_DEBUG:
                    print("PreselectionInfo: Edge is not boundary nor wire")
                return

        # _check_hover_enter
        if last_primitive_index != index:
            context.region.tag_redraw()

        if 'EDGE_LOOP_BOUNDARY' in geom_types:
            info.primitive, info.primitive_coords = get_boundary_edge_loop(primitive, wire_walk=True, get_coords=True)
            info.primitive_coords = [mw @ co for co in info.primitive_coords]
        else:
            if specs.only_boundary:
                if not is_wire_or_boundary(primitive):
                    _check_hover_exit()
                    if USE_DEBUG:
                        print("PreselectionInfo: Vert/Edge is not boundary nor wire")
                    return

            info.primitive = primitive
            info.primitive_coords = coords
        
        if 'EDGE_LOOP_BOUNDARY' not in geom_types:
            scn_raycast_hit = raycast_scene(context, mouse_pos)
            hit_location = scn_raycast_hit.location if scn_raycast_hit.hit else (mw @ raycast_info.location if raycast_info.location is not None else None)
            closest_distance_3d = float('inf')
            within_snap_radius = False
            for loc_3d in info.primitive_coords:
                loc_2d = location_3d_to_region_2d(context.region, context.region_data, loc_3d, default=None)
                if loc_2d is None:
                    continue
                if dist(loc_2d, mouse_pos) <= snap_radius:
                    within_snap_radius = True
                if hit_location is not None:
                    closest_distance_3d = min(closest_distance_3d, dist(loc_3d, hit_location))
            if not within_snap_radius or closest_distance_3d > snap_distance:
                info.primitive = raycast_info.bm_face
                info.primitive_coords = [mw @ v.co for v in info.primitive.verts]
                index = info.primitive.index
                prim_type = 'FACE'
                distance = 0.0
            if closest_distance_3d < float('inf'):
                distance = closest_distance_3d

        info.raycast_info = raycast_info
        info.primitive_index = index
        info.primitive_type = prim_type
        info.distance = distance

        if callback is not None:
            callback(context, mouse_pos, info)

    @classmethod
    def draw_3d(cls, context: Context, specs: ToolPreselectionSpecs, callback=None):
        if context.mode != 'EDIT_MESH':
            return
        info = cls.get()
        if info.raycast_info is None:
            return
        if info.primitive is None:
            return
        color = specs.get_color(info.primitive_type)
        if color[-1] > 0.0:
            match info.primitive_type:
                case 'FACE':
                    imm_2d.draw_polygon(info.primitive_coords, color=color)
                case 'EDGE':
                    if specs.line_width > 0.0:
                        imm_2d.draw_lines(info.primitive_coords, color=color, strip=True, line_width=specs.line_width)
                case 'EDGE_LOOP_BOUNDARY':
                    if specs.line_width > 0.0:
                        imm_2d.draw_lines(info.primitive_coords, color=color, strip=True, line_width=specs.line_width)
                case 'EDGE_LOOP_RING':
                    if specs.line_width > 0.0:
                        imm_2d.draw_lines(info.primitive_coords, color=color, strip=True, line_width=specs.line_width)
                case 'EDGE_BOUNDARY':
                    if specs.line_width > 0.0:
                        imm_2d.draw_lines(info.primitive_coords, color=color, strip=True, line_width=specs.line_width)
                case 'VERT':
                    if specs.point_size > 0.0:
                        imm_2d.draw_points(info.primitive_coords, color=color, point_size=specs.point_size)

        if callback is not None:
            callback(context, info)

    def clear(self):
        self.frozen = False
        self.raycast_info = None
        self.primitive = None
        self.primitive_index = None
        self.primitive_type = None
        self.distance = None
        self.primitive_coords = None
        self.scene_hit_location = None
        self.scene_hit_normal = None

    @classmethod
    def free(cls):
        info = cls.get()
        if info.bvhtree_raycaster is not None:
            info.bvhtree_raycaster.clear_bmesh()
            del info.bvhtree_raycaster
            info.bvhtree_raycaster = None
        if info.vertex_finder is not None:
            del info.vertex_finder
            info.vertex_finder = None
        if info.edge_finder is not None:
            del info.edge_finder
            info.edge_finder = None



@dataclass
class MousePreselectionResult:
    raycast_info: BVHTreeRaycastInfo | None
    primitive: BMFace | BMEdge | BMVert
    primitive_index: int
    primitive_type: Literal['FACE', 'EDGE', 'VERT']
    distance_3d: float
    primitive_coords: List[Vector]
    scene_hit_location: Vector | None = None
    scene_hit_normal: Vector | None = None




    


def preselect_editmesh_primitive_from_mouse(
    context: Context,
    mouse_pos: Vector,
    primitive_types: Set[Literal['FACE', 'EDGE', 'VERT']] = {'FACE', 'EDGE', 'VERT'},
    snap_distance: float = 0.1,
    use_loop: bool = False,
    use_closed_loop: bool = False,
    use_boundary_only: bool = False,
) -> Optional[MousePreselectionResult]:
    if context.mode != 'EDIT_MESH' or context.edit_object is None or context.edit_object.type != 'MESH':
        print('Preselection: Not in EDIT_MESH mode or no mesh object')
        return None
    allowed_primitive_types = {'FACE', 'EDGE', 'VERT'}
    primitive_types = set(primitive_types).intersection(allowed_primitive_types)
    if not primitive_types:
        print('Preselection: No primitive types specified')
        return None
    snap_distance = max(0.000001, snap_distance)
    mouse_pos = Vector(mouse_pos)
    
    mw = context.edit_object.matrix_world
    mouse_scene_hit = raycast_scene(context, mouse_pos)

    raycaster = PreselectionInfo.get_bvhtree_raycaster(context)
    raycaster.ensure_bmesh(context)
    fallback_raycast_info = raycaster.do_raycast(context, mouse_pos)

    def _preselect_loop(_edge: BMEdge, _use_closed: bool) -> Optional[MousePreselectionResult]:
        nonlocal mouse_scene_hit
        if _use_closed:
            verts, edges = walk_closed_boundary(_edge)
            verts_co = [mw @ vert.co for vert in verts]
            p = edges
            p_idx = [edge.index for edge in edges]
            p_type = 'EDGE_LOOP_BOUNDARY'
        else:
            raise NotImplementedError('Non-closed loop not implemented')
        return MousePreselectionResult(
            raycast_info=None,
            primitive=p,
            primitive_index=p_idx,
            primitive_type=p_type,
            distance_3d=dist_to_segment(mouse_pos, *verts_co),
            primitive_coords=verts_co,
            scene_hit_location=mouse_scene_hit.location,
            scene_hit_normal=mouse_scene_hit.normal,
        )

    if fallback_raycast_info is None or not fallback_raycast_info.hit:
        if mouse_scene_hit is None or not mouse_scene_hit.hit:
            ## print('Preselection: No scene hit')
            return None
        if 'VERT' in primitive_types:
            vertex_finder = PreselectionInfo.get_vertex_finder(context)
            vert = vertex_finder._find(context, mouse_scene_hit.location, dist=snap_distance)
            if vert is None or not vert.is_valid:
                ## print('Preselection: VertexFinder - No vertex found')
                return None
            vert_co = mw @ vert.co
            return MousePreselectionResult(
                raycast_info=None,
                primitive=vert,
                primitive_index=vert.index,
                primitive_type='VERT',
                distance_3d=dist(mouse_scene_hit.location, vert_co),
                primitive_coords=[vert_co],
                scene_hit_location=mouse_scene_hit.location,
                scene_hit_normal=mouse_scene_hit.normal,
            )
        elif use_boundary_only and 'EDGE' in primitive_types:
            edge_finder = PreselectionInfo.get_edge_finder(context)
            bm_edge = edge_finder._find(context, mouse_pos)
            if bm_edge is None or not bm_edge.is_valid:
                ## print('Preselection: EdgeFinder - No edge found')
                return None
            if not use_loop and not use_closed_loop:
                p, p_idx, p_type = bm_edge, bm_edge.index, 'EDGE'
                verts_co = [mw @ vert.co for vert in bm_edge.verts]
                return MousePreselectionResult(
                    raycast_info=None,
                    primitive=p,
                    primitive_index=p_idx,
                    primitive_type=p_type,
                    distance_3d=dist_to_segment(mouse_pos, *verts_co),
                    primitive_coords=verts_co,
                    scene_hit_location=mouse_scene_hit.location,
                    scene_hit_normal=mouse_scene_hit.normal,
                )
            return _preselect_loop(bm_edge, use_closed_loop)    
        else:
            return None

    fallback_hit_location = mw @ fallback_raycast_info.location
    fallback_hit_normal = mw @ fallback_raycast_info.normal
    if mouse_scene_hit.hit:
        reference_location = mouse_scene_hit.location
        reference_normal = mouse_scene_hit.normal
    else:
        reference_location = fallback_hit_location
        reference_normal = fallback_hit_normal
    scene_hit_location = reference_location
    scene_hit_normal = reference_normal
    

    if primitive_types.intersection({'VERT', 'EDGE'}):
        best_result = None
        best_distance_3d = float('inf')
        edge_corner_factor = 0.32 if 'VERT' in primitive_types else 0.092
        primitive_result = fallback_raycast_info.get_closest_primitive(context, primitive_types, edge_corner_factor=edge_corner_factor)
        if primitive_result is not None:
            primitive, index, primitive_type, _, primitive_coords = primitive_result
            if primitive_coords:
                if primitive_type == 'VERT':
                    closest_distance_3d = dist(reference_location, primitive_coords[0])
                elif primitive_type == 'EDGE':
                    closest_point = closest_point_on_segment(primitive_coords[0], primitive_coords[1], reference_location)
                    closest_distance_3d = dist(reference_location, closest_point) if closest_point is not None else min(dist(reference_location, coord) for coord in primitive_coords)
                else:
                    closest_distance_3d = float('inf')
                if closest_distance_3d <= snap_distance and closest_distance_3d < best_distance_3d:
                    best_distance_3d = closest_distance_3d
                    best_result = MousePreselectionResult(
                        raycast_info=fallback_raycast_info,
                        primitive=primitive,
                        primitive_index=index,
                        primitive_type=primitive_type,
                        distance_3d=closest_distance_3d,
                        primitive_coords=primitive_coords,
                        scene_hit_location=scene_hit_location,
                        scene_hit_normal=scene_hit_normal,
                    )

        if best_result is not None:
            if 'EDGE' in primitive_types and use_loop or use_closed_loop:
                return _preselect_loop(best_result.primitive, use_closed_loop)
            return best_result

    face = fallback_raycast_info.bm_face
    face_hit_world = mw @ fallback_raycast_info.location
    face_distance_3d = dist(reference_location, face_hit_world)
    face_coords = [mw @ vert.co for vert in face.verts]
    return MousePreselectionResult(
        raycast_info=fallback_raycast_info,
        primitive=face,
        primitive_index=face.index,
        primitive_type='FACE',
        distance_3d=face_distance_3d,
        primitive_coords=face_coords,
        scene_hit_location=scene_hit_location,
        scene_hit_normal=scene_hit_normal,
    )
