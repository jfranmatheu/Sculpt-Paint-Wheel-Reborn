from bpy.app import handlers
import bpy

from ..prefs import BlendWheelPrefs


def on_exit_pre(*_args):
    # Blender auto-saves the preferences at quit only when they are marked as changed, and editing the add-on's
    # nested data (brush sets, custom buttons...) doesn't mark them: do it so that data reaches userpref.blend.
    try:
        bpy.context.preferences.is_dirty = True
    except Exception as ex:
        print(f"Cleaning up... could not mark the preferences as changed: {ex}")
    try:
        prefs = BlendWheelPrefs.get_prefs(bpy.context)
        out_path = prefs.save()
        print(f"Cleaning up... preferences saved to: {out_path}")
    except Exception as ex:
        print(f"Cleaning up... failed to save preferences: {ex}")



# ---------------------------------------------

def register():
    handlers.exit_pre.append(on_exit_pre)

def unregister():
    if on_exit_pre in handlers.exit_pre:
        handlers.exit_pre.remove(on_exit_pre)
