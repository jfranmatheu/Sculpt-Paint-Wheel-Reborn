import bpy

from ..pg.pg_wheel_storage import WheelStorage
from ..prefs import BlendWheelPrefs
from ..core.globals import PATHS


def startup_timer() -> None:
    print("Startup...")
    prefs = BlendWheelPrefs.get_prefs(bpy.context)
    if getattr(prefs, "first_time", False):
        # First register after install/update: restore previous session data if present.
        prefs_path = PATHS.USER_DATA / "preferences.json"
        if prefs_path.exists():
            prefs.load(prefs_path)
        prefs.first_time = False
    WheelStorage.get(bpy.context).initialize_defaults()
    # Restored / seeded data lives in nested groups, which don't mark the preferences as changed by themselves.
    bpy.context.preferences.is_dirty = True
    return None

def register() -> None:
    bpy.app.timers.register(startup_timer, first_interval=1.0)
