from typing import List, Type
from bpy.types import GizmoGroup as GZG, Gizmo as GZ

from .._base import BType


class BType_GZG(BType, GZG):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'PERSISTENT', 'SHOW_MODAL_ALL'}

    _instance: 'BType_GZG' = None
    _gizmos_cls: List[Type[GZ]] = None

    def draw_prepare(self, context):
        pass

    def setup(self, context):
        for gz_cls in self.__class__._gizmos_cls:
            gz = self.gizmos.new(gz_cls.bl_idname)
            gz.use_event_handle_all = True
            gz.use_draw_modal = True
            gz.scale_basis = 1

    def invoke_prepare(self, context, gizmo):
        pass

    def refresh(self, context):
        if not self.__class__._instance or self.__class__._instance is self:
            return

        self.__class__._instance = self
