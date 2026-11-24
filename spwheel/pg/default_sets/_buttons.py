"""Helpers to declare direct-action buttons (operators and toggles) in the default sets."""

from os.path import dirname, join

icons_dir = join(dirname(dirname(dirname(__file__))), "assets", "images", "custom_buttons")


def operator(name: str, icon: str, expr: str, state_path: str = "") -> dict:
    """Operator button. ``expr`` is ``"module.op"`` or ``"module.op#arg=value, ..."``; ``state_path`` (optional) is a
    boolean data path from the context that draws the button pressed while it is True."""
    return {
        "name": name,
        "image_path": join(icons_dir, icon),
        "type": "OPERATOR",
        "as_attribute": "CUSTOM",
        "custom_identifier": expr,
        "state_path": state_path,
    }


def toggle(name: str, icon: str, data_path: str) -> dict:
    """Toggle button: flips the boolean at ``data_path`` (from the context) and shows its state."""
    return {
        "name": name,
        "image_path": join(icons_dir, icon),
        "type": "PROPERTY",
        "data_path": data_path,
    }


# Shared toggles.
MIRROR_X = toggle("Mirror X", "mirror.png", "object.data.use_mirror_x")
FACE_SELECTION_MASKING = toggle("Face Selection Masking", "face_mask.png", "object.data.use_paint_mask")
VERTEX_SELECTION_MASKING = toggle("Vertex Selection Masking", "vertex_mask.png", "object.data.use_paint_mask_vertex")
AUTO_NORMALIZE = toggle("Auto Normalize", "normalize.png", "tool_settings.use_auto_normalize")
GP_MULTI_FRAME = toggle("Multi-Frame Editing", "frames.png", "tool_settings.use_grease_pencil_multi_frame_editing")
GP_ONION_SKIN = toggle("Onion Skin", "onion.png", "space_data.overlay.use_gpencil_onion_skin")
