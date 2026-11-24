"""Wheel theme presets: apply, save, save as, reset and delete (see utils/theme_presets)."""

from bpy.props import EnumProperty, StringProperty

from ..core.bl_types import OperatorAction
from ..utils import theme_presets


def _theme(context):
    from ..prefs import BlendWheelPrefs
    return BlendWheelPrefs.get_prefs(context).wheel.theme


def _redraw(context) -> None:
    for win in context.window_manager.windows:
        for area in win.screen.areas:
            area.tag_redraw()


_preset_items: list = []  # (Blender needs the enum item strings kept alive.)


def _icon(name: str, dark_icon: str) -> str:
    return 'LIGHT_SUN' if theme_presets.is_light_preset(name) else dark_icon


def _preset_enum_items(self, context):
    _preset_items.clear()
    builtins = theme_presets.builtin_names()
    users = theme_presets.user_names()
    for i, name in enumerate(builtins):
        _preset_items.append((name, name, f"Built-in theme: {name}", _icon(name, 'COLOR'), i))
    for j, name in enumerate(users):
        _preset_items.append((name, name, f"Your theme: {name}", _icon(name, 'USER'), len(builtins) + j))
    return _preset_items


class _ExecAction:
    """(Mixin) execute() runs action() too: for dialogs and menus that call execute."""
    def execute(self, context):
        msg = self.action(context, None)
        if isinstance(msg, str):
            self.report({"ERROR"}, msg)
            return {'CANCELLED'}
        return {'CANCELLED'} if msg is False else {'FINISHED'}


class OpApplyThemePreset(_ExecAction, OperatorAction):
    """Apply a theme preset to the wheel (unsaved edits of the current one are discarded)"""
    bl_label = "Theme Preset"

    preset: EnumProperty(name="Theme", items=_preset_enum_items)

    def action(self, context, event):
        if not theme_presets.apply(_theme(context), self.preset):
            return f'Theme "{self.preset}" not found'
        _redraw(context)


class OpSaveThemePreset(_ExecAction, OperatorAction):
    """Save the edits to the active theme (your own themes only: save a built-in one under a new name)"""
    bl_label = "Save Theme"

    def action(self, context, event):
        theme = _theme(context)
        if theme_presets.is_builtin(theme.active_preset):
            return "Built-in themes can't be overwritten: use Save As"
        theme_presets.save(theme, theme.active_preset)
        self.report({'INFO'}, f'Theme "{theme.active_preset}" saved')


class OpSaveThemePresetAs(_ExecAction, OperatorAction):
    """Save the current colors as a new theme of yours"""
    bl_label = "Save Theme As"

    name: StringProperty(name="Name", default="My Theme")

    def draw(self, context):
        self.layout.prop(self, "name")
        name = self.name.strip()
        if theme_presets.is_builtin(name):
            self.layout.label(text="That's a built-in theme's name", icon='ERROR')
        elif name and theme_presets.exists(name):
            self.layout.label(text="Overwrites your theme with that name", icon='INFO')

    def invoke(self, context, event):
        active = _theme(context).active_preset
        self.name = active if not theme_presets.is_builtin(active) else f"My {active}"
        return context.window_manager.invoke_props_dialog(self, confirm_text="Save")

    def action(self, context, event):
        name = self.name.strip()
        if not name:
            return "The theme needs a name"
        if theme_presets.is_builtin(name):
            return f'"{name}" is a built-in theme: pick another name'
        theme_presets.save(_theme(context), name)
        self.report({'INFO'}, f'Theme "{name}" saved')
        _redraw(context)


class OpResetWheelTheme(_ExecAction, OperatorAction):
    """Discard the edits: back to the active theme as it was saved"""
    bl_label = "Reset Theme"

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def action(self, context, event):
        theme = _theme(context)
        if not theme_presets.apply(theme, theme.active_preset):
            theme_presets.apply(theme, theme_presets.DEFAULT_PRESET)
        _redraw(context)


class OpDeleteThemePreset(_ExecAction, OperatorAction):
    """Delete the active theme (your own themes only) and go back to the default one"""
    bl_label = "Delete Theme"

    def invoke(self, context, event):
        name = _theme(context).active_preset
        return context.window_manager.invoke_confirm(self, event, title="Delete Theme",
                                                     message=f'Delete your theme "{name}"?', confirm_text="Delete",
                                                     icon='WARNING')

    def action(self, context, event):
        theme = _theme(context)
        name = theme.active_preset
        if theme_presets.is_builtin(name):
            return "Built-in themes can't be deleted"
        theme_presets.delete(name)
        theme_presets.apply(theme, theme_presets.DEFAULT_PRESET)
        self.report({'INFO'}, f'Theme "{name}" deleted')
        _redraw(context)
