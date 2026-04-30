import bpy

from ..pg.pg_wheel_storage import WheelStorage


def startup_timer() -> None:
    print("Startup...")
    WheelStorage.get(bpy.context).initialize()
    return None

def register() -> None:
    bpy.app.timers.register(startup_timer, first_interval=1.0)
