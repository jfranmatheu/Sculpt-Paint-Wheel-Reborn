import bpy
from bpy.types import Context
from ...globals import GLOBALS

from ..ui.btype_ui_base import BType_UIExtra


class BType_AddonPreferences(BType_UIExtra, bpy.types.AddonPreferences):
    bpy_type = bpy.types.AddonPreferences

    @classmethod
    def tag_register(cls, **kwargs):
        cls.bl_idname = GLOBALS.ADDON.PACKAGE_NAME
        if not getattr(cls, "bl_label", ""):
            cls.bl_label = GLOBALS.ADDON.NAME
        for key, value in kwargs.items():
            setattr(cls, key, value)
        return cls

    @classmethod
    def get_prefs(cls, context: Context):
        return context.preferences.addons[GLOBALS.ADDON.PACKAGE_NAME].preferences
