from typing import Any
import bpy
import sys
from pathlib import Path
import tomllib

from .. import __package__ as __main_package__

FORCE_DEBUG = True


class PATHS:
    """ Addon paths. """
    ROOT = Path(__file__).parent.parent
    ROOT_STR = ROOT.as_posix()
    CORE = ROOT / 'core'
    MANIFEST = ROOT / "blender_manifest.toml"
    ASSETS = ROOT / 'assets'
    ICONS = ASSETS / 'icons'
    USER_DATA = bpy.utils.resource_path('USER')


with open(PATHS.MANIFEST, "rb") as f:
    _blender_manifest_contents = tomllib.load(f)


PATHS.USER_DATA = PATHS.USER_DATA / _blender_manifest_contents['id']
PATHS.USER_DATA.mkdir(parents=True, exist_ok=True)


class GLOBALS:
    """ Addon globals. """
    PYTHON_PATH = sys.executable
    BLENDER_VERSION = bpy.app.version
    IN_BACKGROUND = bpy.app.background
    USE_DEBUG_FLAG = bpy.app.debug_value == 1 or FORCE_DEBUG
    IN_DEVELOPMENT = USE_DEBUG_FLAG or 'vscode_development' in __main_package__

    class ADDON:
        """ Addon info. """
        ID = _blender_manifest_contents['id']
        ID_UPPER = ID.upper()
        NAME = _blender_manifest_contents['name']
        VERSION = _blender_manifest_contents['version']
        BLENDER_VERSION_MIN = _blender_manifest_contents['blender_version_min']

        PACKAGE_NAME = __main_package__
        CORE_PACKAGE_NAME = __package__
        NAME_NO_SPACE = NAME.replace(' ', '')
        NAME_UPPER = NAME.upper().replace(' ', '_')
        NAME_LOWER = NAME.lower().replace(' ', '_')
        WORKS_IN_BACKGROUND = _blender_manifest_contents.get('works_in_background', False)
        AUTO_CODE_OPTIONS = _blender_manifest_contents.get('auto_code_options', [])
        DEFAULT_ROOT_PROP_GROUP_DATAPATH = _blender_manifest_contents.get('default_root_prop_group_datapath', ID)
        DEFAULT_PANELS_CATEGORY = _blender_manifest_contents.get('default_panels_category', NAME)
        DEFAULT_PANELS_CONTEXT = _blender_manifest_contents.get('default_panels_context', "")
        DEFAULT_PANELS_SPACE_TYPE = _blender_manifest_contents.get('default_panels_space_type', "VIEW_3D")
        DEFAULT_PANELS_REGION_TYPE = _blender_manifest_contents.get('default_panels_region_type', "UI")


def set_global_value(global_name: str, value):
    if not hasattr(bpy, GLOBALS.ADDON.ID):
        setattr(bpy, GLOBALS.ADDON.ID, {})
    getattr(bpy, GLOBALS.ADDON.ID)[global_name] = value

def get_global_value(global_name: str, default_value=None) -> Any:
    if not hasattr(bpy, GLOBALS.ADDON.ID):
        return default_value
    return getattr(bpy, GLOBALS.ADDON.ID).get(global_name, default_value)
