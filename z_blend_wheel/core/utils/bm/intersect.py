from bmesh.types import BMEdge
from bpy.types import Context
from mathutils import Vector
from ..geometry.intersect import segment_intersection_2d
from ..view_utils import location_3d_to_region_2d


def get_intersect_edges_with_2d_line(context: Context, edges: list[BMEdge], line_2d: tuple[Vector, Vector], return_intersection_points: bool = False) -> list[BMEdge]:
    """Get intersect edges with 2d line.

    Args:
        context (bpy.types.Context): The context.
        edges (list[bmesh.types.BMEdge]): The edges to check.
        line_2d (tuple[mathutils.Vector, mathutils.Vector]): The 2d line.
        return_intersection_points (bool, optional): Whether to return the intersection points. Defaults to False.

    Returns:
        list[bmesh.types.BMEdge]: The intersect edges.
    """
    intersections = []
    for edge in edges:
        edge_2d_co = (
            location_3d_to_region_2d(context.region, context.region_data, edge.verts[0].co),
            location_3d_to_region_2d(context.region, context.region_data, edge.verts[1].co)
        )
        if intersect_point := segment_intersection_2d(*line_2d, *edge_2d_co):
            if return_intersection_points:
                intersections.append((edge, intersect_point))
            else:
                intersections.append(edge)
    return intersections
