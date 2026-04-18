from bmesh.types import BMFace, BMVert
from bpy.types import Context, Object
from mathutils import Matrix

from ..object import get_mesh_objects, get_bbox_min_max


def snap_verts_to_closest_object(
    context: Context,
    mesh_object: Object,
    verts: set[BMVert],
):
    depsgraph = context.evaluated_depsgraph_get()
    valid_objects = get_mesh_objects(context, include_convertible_types=True)
    source_mw = mesh_object.matrix_world
    source_mwi = source_mw.inverted()
    if mesh_object in valid_objects:
        valid_objects.remove(mesh_object)
    # objects_bbox = {
    #     ob: get_bbox_min_max(ob, as_bbox=True, world_space=False).expanded_uniform(0.1)
    #     for ob in valid_objects
    # }
    # print("snap_verts_to_closest_object: valid objects", valid_objects)
    for v in verts:
        best_dist = float('inf')
        best_ob = None
        best_co = None
        v_co_world = source_mw @ v.co
        for ob in valid_objects:
            mw = ob.matrix_world
            mwi = mw.inverted()
            v_co_object = mwi @ v_co_world
            # Filter objects by bbox.
            # if not objects_bbox[ob].contains(v_co_object):
            #     print(f"snap_verts_to_closest_object: {v} not in {ob} bbox")
            #     break

            ok, closest_co, closest_no, face_index = ob.closest_point_on_mesh(v_co_object, depsgraph=depsgraph)
            if not ok:
                continue
            co_world = mw @ closest_co

            dist = (co_world - v_co_world).length
            if dist < best_dist:
                best_dist = dist
                best_co = co_world
                best_ob = ob
        if best_ob:
            v.co = source_mwi @ best_co
            ## print(f"snap_verts_to_closest_object: snapped {v} to {best_ob} at {closest_co}")
            # v.normal = mwi @ best_ob.matrix_world @ closest_no
