"""Is Blender's interface theme dark or light?

Measured on Blender 5.3's bundled themes (relative luminance):
    menu background (wcol_menu_back.inner):  Blender Dark 0.09  |  Blender Light 0.75
    widget text      (wcol_regular.text):     Blender Dark 0.90  |  Blender Light 0.10
A theme counts as light only when its menus are light *and* its text is dark; anything else (dark themes,
ambiguous custom themes, errors) counts as dark.
"""

from __future__ import annotations

import bpy

LIGHT_BACK_MIN = 0.55   # Menu background at least this bright...
LIGHT_TEXT_MAX = 0.45   # ...and widget text at most this bright: a light theme.


def _luminance(c) -> float:
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def blender_theme_is_light() -> bool:
    try:
        ui = bpy.context.preferences.themes[0].user_interface
        back = _luminance(ui.wcol_menu_back.inner)
        text = _luminance(ui.wcol_regular.text)
    except Exception:
        return False
    return back >= LIGHT_BACK_MIN and text <= LIGHT_TEXT_MAX
