import sys
from pathlib import Path
import os

import bpy

from .utils.fs import is_junction
from .. import __package__ as __main_package__


__all__ = [
    'GLOBALS',
]


class GLOBALS:
    PYTHON_PATH = sys.executable

    # Blender info.
    BLENDER_VERSION = bpy.app.version
    IN_BACKGROUND = bpy.app.background

    # Addon Info.
    ADDON_MODULE = __main_package__
    ADDON_MODULE_SHORT = __main_package__.split('.')[-1] if BLENDER_VERSION >= (4, 2, 0) else __main_package__
    ADDON_MODULE_UPPER = ADDON_MODULE_SHORT.upper().replace('_', '')

    ADDON_MODULE_NAME = ADDON_MODULE_SHORT.replace('_', ' ').title().replace(' ', '')

    # Paths.
    ADDON_SOURCE_PATH = Path(__file__).parent.parent
    ADDON_DIR = ADDON_SOURCE_PATH  # alias
    ICONS_PATH = ADDON_SOURCE_PATH / 'lib' / 'icons'
    IMAGES_PATH = ADDON_SOURCE_PATH / 'lib' / 'images'
    USER_CONFIG_DIR = os.path.join(
        bpy.utils.resource_path('USER'),
        'config',
        'ackit'  # Base config folder for ackit
    )

    @classmethod
    def check_in_development(cls) -> bool:
        """Check if addon is in development mode."""
        if bpy.app.debug_value == 1:
            return True
        if (hasattr(sys, 'gettrace') and sys.gettrace() is not None) and is_junction(GLOBALS.ADDON_SOURCE_PATH):
            return True
        return False

    @classmethod
    def check_in_production(cls) -> bool:
        """Check if addon is in production mode."""
        return not cls.check_in_development()

    @classmethod
    def ensure_config_dir(cls) -> None:
        """Ensure the config directory exists."""
        Path(cls.USER_CONFIG_DIR).mkdir(parents=True, exist_ok=True)

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

def init():
    GLOBALS.ensure_config_dir()


def register():
    setattr(bpy, GLOBALS.ADDON_MODULE, dict())


def unregister():
    if hasattr(bpy, GLOBALS.ADDON_MODULE):
        delattr(bpy, GLOBALS.ADDON_MODULE)
