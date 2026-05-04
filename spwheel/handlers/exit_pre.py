from bpy.app import handlers
import bpy

from ..prefs import BlendWheelPrefs


def on_exit_pre(arg_1, arg_2):
    print("on_exit_pre")
    print(arg_1) # boolean
    print(arg_2) # None, type?
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
