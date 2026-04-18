
import bmesh
from bmesh.types import BMEdge, BMFace, BMVert
import bpy
from bpy.types import Context
from mathutils import Vector

from ..falloff import FalloffType
from ..raycast_utils import BVHTreeRaycaster, raycast_scene


def mouse_offset_to_3d(context: Context, face: BMFace, mouse_offset_2d: Vector) -> Vector:
    rv3d = context.region_data
    view_right = rv3d.view_rotation @ Vector((1, 0, 0))
    view_up    = rv3d.view_rotation @ Vector((0, 1, 0))

    move = (
        view_right * mouse_offset_2d.x +
        view_up    * mouse_offset_2d.y
    )

    n = face.normal.normalized()
    move -= n * move.dot(n)

    return move


class QuadRetopoTweakTool:
    """
    Local tweak tool for vertices and edge loops.
    Stateless per stroke (no drift).
    """

    def __init__(self, bm):
        self.bm = bm
        self.primitive = None
        self.falloff = None
        self.op_id = None

    # --------------------------------------------------
    # Call on mouse press
    # --------------------------------------------------

    def begin(self, context: Context, mouse_pos: Vector, falloff: FalloffType = FalloffType.GAUSSIAN):
        self.falloff = falloff

        raycaster = BVHTreeRaycaster(context, existing_bmesh=self.bm)
        raycast_info = raycaster.do_raycast(context, mouse_pos)
        if raycast_info is None:
            return
        if result := raycast_info.get_closest_primitive(context, primitive_types={'VERT', 'EDGE'}, edge_corner_factor=0.25):
            closest_primitive, index, type, distance, coords = result
            self.primitive = closest_primitive
            bpy.ops.mesh.select_all(action='DESELECT')
            self.primitive.select_set(True)
            bmesh.update_edit_mesh(
                context.edit_object.data,
                loop_triangles=False,
                destructive=False
            )

            if type == 'VERT':
                bpy.ops.transform.translate('INVOKE_DEFAULT', release_confirm=True, snap=True)
                self.op_id = bpy.ops.transform.translate.idname_py()
            elif type == 'EDGE':
                bpy.ops.mesh.loop_select('INVOKE_DEFAULT', extend=True)
                bpy.ops.transform.edge_slide('INVOKE_DEFAULT', release_confirm=True, snap=True, use_even=True)
                self.op_id = bpy.ops.transform.edge_slide.idname_py()
                # res = bpy.ops.mesh.loop_select_and_slide('INVOKE_DEFAULT')
                # print("loop_select_and_slide", res)

    # --------------------------------------------------
    # Call on mouse move
    # --------------------------------------------------

    def update(
        self,
        context,
        mouse_pos: Vector
    ):
        if context.active_operator and context.active_operator.bl_idname == self.op_id:
            return {'FINISHED'}

        return
        if self.primitive is None:
            return

        hit_result = raycast_scene(context, mouse_pos)
        if hit_result is None or not hit_result.hit:
            return
        hit_location = hit_result.location

        bmesh.update_edit_mesh(
            context.edit_object.data,
            loop_triangles=False,
            destructive=False
        )

    # --------------------------------------------------
    # Call on mouse release
    # --------------------------------------------------

    def end(self):
        pass
