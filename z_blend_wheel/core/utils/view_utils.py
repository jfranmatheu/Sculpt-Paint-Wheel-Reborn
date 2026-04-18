from bpy.types import Context, RegionView3D
from bpy_extras.view3d_utils import region_2d_to_vector_3d, region_2d_to_origin_3d, location_3d_to_region_2d
from mathutils import Vector


def get_view_vector(context: Context, region_coord: Vector) -> Vector:
    """
    Get the view vector from the mouse cursor position.
    
    Parameters:
        context (Context): The Blender context.
        region_coord (Vector): The mouse cursor position in the region.
    
    Returns:
        Vector: The view vector.
    """
    return region_2d_to_vector_3d(context.region, context.region_data, region_coord).normalized()


def get_ray_origin(context: Context, region_coord: Vector) -> Vector:
    """
    Get the ray origin from the mouse cursor position.
    
    Parameters:
        context (Context): The Blender context.
        region_coord (Vector): The mouse cursor position in the region.
    
    Returns:
        Vector: The ray origin.
    """
    return region_2d_to_origin_3d(context.region, context.region_data, region_coord)


def is_vector_pointing_away_from_view(rv3d: Context | RegionView3D, vector: Vector) -> bool:
    # Get the 3D view region
    if not rv3d:
        return False

    # View direction: negative of forward vector
    view_dir = -rv3d.view_rotation @ Vector((0, 0, 1))

    # Dot product between vector and view direction
    dot = vector.dot(view_dir)
    
    # If dot product is negative, vector is pointing away
    return dot < 0


def is_navigating(context: Context) -> bool:
    if not context.window.modal_operators:
        return False
    active_modal_op = context.window.modal_operators[-1].bl_idname
    if context.space_data.type == 'VIEW_3D':
        return active_modal_op in {'VIEW3D_OT_move', 'VIEW3D_OT_rotate', 'VIEW3D_OT_zoom'}
    else:
        raise NotImplementedError(f"is_navigating() - '{context.space_data.type}' editor is not supported!")
