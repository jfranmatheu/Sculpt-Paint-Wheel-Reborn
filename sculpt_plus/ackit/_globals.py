import sys
from pathlib import Path

import bpy

from .utils.fs import is_junction
from .. import __package__ as __main_package__


__all__ = [
    'GLOBALS',
]


class GLOBALS:
    PYTHON_PATH = sys.executable

    BLENDER_VERSION = bpy.app.version
    IN_BACKGROUND = bpy.app.background

    ADDON_MODULE = __main_package__
    ADDON_MODULE_SHORT = __main_package__.split('.')[-1] if BLENDER_VERSION >= (4, 2, 0) else __main_package__
    ADDON_MODULE_UPPER = ADDON_MODULE_SHORT.upper().replace('_', '')
    ADDON_SOURCE_PATH = Path(__file__).parent.parent
    ADDON_MODULE_NAME = ADDON_MODULE_SHORT.replace('_', ' ').title().replace(' ', '')
    ICONS_PATH = ADDON_SOURCE_PATH / 'lib' / 'icons'
    IMAGES_PATH = ADDON_SOURCE_PATH / 'lib' / 'images'

    check_in_development = lambda : (hasattr(sys, 'gettrace') and sys.gettrace() is not None) and is_junction(GLOBALS.ADDON_SOURCE_PATH)
    check_in_production = lambda : not GLOBALS.check_in_development()

    class CodeGen:
        TYPES = 'types.py'
        ICONS = 'icons.py'
        OPS = 'ops.py'

    @staticmethod
    def get_value(key: str, default_value = None):
        return getattr(bpy, GLOBALS.ADDON_MODULE).get(key, default_value)

    @staticmethod
    def set_value(key: str, value) -> None:
        getattr(bpy, GLOBALS.ADDON_MODULE)[key] = value


# ----------------------------------------------------------------

def register():
    setattr(bpy, GLOBALS.ADDON_MODULE, dict())

def unregister():
    if hasattr(bpy, GLOBALS.ADDON_MODULE):
        delattr(bpy, GLOBALS.ADDON_MODULE)
