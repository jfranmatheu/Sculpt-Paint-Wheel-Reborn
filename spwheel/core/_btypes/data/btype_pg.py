from typing import Type, TypeVar

import bpy
from bpy.types import Context, UILayout

from .btype_prefs import BType_AddonPreferences
from ..ui.btype_ui_base import BType_UIExtra
from ...globals import GLOBALS


TRoot = TypeVar("RootPropertyGroup", bound='BType_PGRoot')


class BType_PropertyGroup(BType_UIExtra, bpy.types.PropertyGroup):
    pg_role: str
    pg_prop_name: str

    @classmethod
    def get_name(cls) -> str:
        if prop_name := getattr(cls, "pg_prop_name", ""):
            return prop_name
        return cls.__name__.lower()

    @classmethod
    def get_datapath(cls) -> str:
        raise NotImplementedError("Not implemented!")

    @classmethod
    def get(cls, context: Context) -> 'BType_PropertyGroup':
        raise NotImplementedError("Not implemented!")

    @classmethod
    def _draw(self, context: Context, layout: UILayout) -> None:
        self.get(context).draw_ui(context, layout)

    def draw_ui(self, context: Context, layout: UILayout) -> None:
        pass


class BType_PGChild(BType_PropertyGroup):
    pg_role = 'CHILD'
    pg_parent: Type[BType_PropertyGroup] | Type[BType_AddonPreferences] | None = None
    
    @classmethod
    def get_datapath(cls) -> str:
        if issubclass(cls.pg_parent, BType_AddonPreferences):
            # Preferences are accessed differently from standard property groups
            return cls.get_name()
        return f"{cls.pg_parent.get_datapath()}.{cls.get_name()}"

    @classmethod
    def get(cls, context: Context, *data_path: str) -> TRoot:
        if cls.pg_parent is None:
            raise ValueError("pg_parent is None!")
    
        if issubclass(cls.pg_parent, BType_AddonPreferences):
            if isinstance(context, Context):
                prefs = cls.pg_parent.get_prefs(context)
                path = cls.get_name()
                if data_path:
                    path += '.' + '.'.join(data_path)
                return prefs.path_resolve(path)
            else:
                raise ValueError("Requires Context to resolve BType_AddonPreferences child.")

        return cls.pg_parent.get(context, *data_path, cls.get_name())


class BType_PGRoot(BType_PropertyGroup):
    pg_role = 'ROOT'
    pg_root_type: Type[bpy.types.ID] | None = None
    pg_root_datapath: str = ""

    @classmethod
    def get_datapath(cls) -> str:
        return f"{cls.pg_root_datapath}.{cls.get_name()}"

    @classmethod
    def get(cls, context: Context) -> TRoot:
        return context.path_resolve(cls.get_datapath())


def _new_root_pg(root_type: Type[bpy.types.ID], data_path: str) -> Type[BType_PGRoot]:
    return type(f"BType_PGRoot_{root_type}", (BType_PGRoot,), {
        "pg_root_type": root_type,
        "pg_root_datapath": f"{data_path}.{GLOBALS.ADDON.DEFAULT_ROOT_PROP_GROUP_DATAPATH}"
    })


class BType_PGRootTypes:
    CUSTOM = BType_PGRoot
    # ---
    WINDOW_MANAGER = _new_root_pg(bpy.types.WindowManager, 'window_manager')
    SCENE = _new_root_pg(bpy.types.Scene, 'scene')
    OBJECT = _new_root_pg(bpy.types.Object, 'object')
    MATERIAL = _new_root_pg(bpy.types.Material, 'material')
    MESH = _new_root_pg(bpy.types.Mesh, 'mesh')
    BRUSH = _new_root_pg(bpy.types.Brush, 'brush')
    TEXTURE = _new_root_pg(bpy.types.Texture, 'texture')
    IMAGE = _new_root_pg(bpy.types.Image, 'texture')
