from typing import Optional
from bpy.types import Context, Depsgraph, Object, ViewLayer
from mathutils import Vector

from .geometry.bbox import BBox


def is_visible(ob: Object, view_layer: Optional[ViewLayer] = None) -> bool:
    return ob.visible_get(view_layer=view_layer)

def has_polygons(ob: Object, depsgraph: Optional[Depsgraph] = None) -> bool:
    if depsgraph is None:
        if ob.type == 'MESH':
            return bool(ob.data.polygons)
        return False
    eval_ob = ob.evaluated_get(depsgraph)
    if eval_ob.type == 'MESH':
        return bool(eval_ob.data.polygons)
    try:
        eval_me = eval_ob.to_mesh()
        if not eval_me:
            return False
        return bool(eval_me.polygons)
    except Exception as e:
        print(f"Error evaluating object {ob.name}: {e}")
        return False
    finally:
        eval_ob.to_mesh_clear()

def get_bbox_min_max(ob: Object, as_bbox: bool = False, world_space: bool = True) -> tuple[Vector, Vector] | BBox:
    bbox = ob.bound_box
    min_x = min([v[0] for v in bbox])
    min_y = min([v[1] for v in bbox])
    min_z = min([v[2] for v in bbox])
    max_x = max([v[0] for v in bbox])
    max_y = max([v[1] for v in bbox])
    max_z = max([v[2] for v in bbox])
    _min = Vector((min_x, min_y, min_z))
    _max = Vector((max_x, max_y, max_z))
    if world_space:
        _min = ob.matrix_world @ _min
        _max = ob.matrix_world @ _max
    if as_bbox:
        return BBox(_min, _max)
    return _min, _max

def get_mesh_objects(
    context: Context,
    include_convertible_types: bool = False,
) -> set[Object]:
    if include_convertible_types:
        ob_types = {'MESH', 'CURVE', 'SURFACE', 'META', 'FONT'}
    else:
        ob_types = {'MESH'}

    depsgraph = context.evaluated_depsgraph_get()
    return {
        o
        for o in context.view_layer.objects
        if is_visible(o) and\
        o.type in ob_types and\
        has_polygons(o, depsgraph=depsgraph)
    }
