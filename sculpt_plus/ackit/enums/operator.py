from dataclasses import dataclass
from enum import Enum

from bpy.types import Operator, Context


class OpsReturn:
    FINISH = {'FINISHED'}
    CANCEL = {'CANCELLED'}
    PASS = {'PASS_THROUGH'}
    RUN = {'RUNNING_MODAL'}
    UI = {'INTERFACE'}


class SubmodalReturn(Enum):
    STOP = 0        # Stop the submodal
    RUNNING = 1     # Keep running the submodal
