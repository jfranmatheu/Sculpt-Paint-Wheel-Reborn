"""Change the icon image of the active custom button."""
import os

import bpy
from bpy.props import BoolProperty, StringProperty

from ..core.bl_types import OperatorAction
from ..core.utils.image_previews import get_image_icon_id
from ..gpu.button_texture import forget_custom_button_texture
from ..pg.pg_wheel_storage import WheelStorage


def _get_active_button(context):
    storage = WheelStorage.get_by_mode(context)
    active_set = storage.active_tarta_set if storage is not None else None
    if active_set is None:
        return None
    idx = active_set.active_button_index
    if 0 <= idx < len(active_set.buttons):
        return active_set.buttons[idx]
    return None


class OpTartaButtonSetIcon(OperatorAction):
    """Load the icon of the selected custom button from an image file"""
    bl_label = "Change Button Icon"

    filepath: StringProperty(subtype="FILE_PATH", options={"SKIP_SAVE"})
    filter_image: BoolProperty(default=True, options={"HIDDEN", "SKIP_SAVE"})
    filter_folder: BoolProperty(default=True, options={"HIDDEN", "SKIP_SAVE"})
    clear: BoolProperty(
        name="Clear",
        description="Remove the icon instead of loading one",
        default=False,
        options={"SKIP_SAVE"},
    )

    @classmethod
    def poll_operator(cls, context) -> bool | str:
        if _get_active_button(context) is None:
            return "No custom button selected"
        return True

    def invoke(self, context, event):
        if self.clear:
            _get_active_button(context).image_path = ""
            return self.OpReturn.FINISH
        button = _get_active_button(context)
        if button.image_path:
            self.filepath = bpy.path.abspath(button.image_path)
        context.window_manager.fileselect_add(self)
        return self.OpReturn.RUN

    def execute(self, context):
        button = _get_active_button(context)
        if button is None:
            return self.OpReturn.CANCEL
        path = os.path.normpath(bpy.path.abspath(self.filepath)) if self.filepath else ""
        if not path or not os.path.isfile(path):
            self.report({"ERROR"}, "Pick an image file")
            return self.OpReturn.CANCEL
        # Picking the same file again reloads it (it may have been edited on disk).
        forget_custom_button_texture(path)
        get_image_icon_id(path, force_reload=True)
        button.image_path = path
        return self.OpReturn.FINISH
