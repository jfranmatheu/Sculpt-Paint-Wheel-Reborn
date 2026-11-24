"""Operators related to addon preferences persistence."""

from ..core.bl_types import OperatorAction


def _reset_to_defaults(data, keep: frozenset = frozenset()) -> None:
    """Reset every property of a PropertyGroup (recursively) to its default value, except those in ``keep``."""
    for prop in data.bl_rna.properties:
        pid = prop.identifier
        if pid == "rna_type" or pid in keep or prop.is_readonly and prop.type != 'POINTER':
            continue
        if prop.type == 'POINTER':
            sub = getattr(data, pid, None)
            if sub is not None and hasattr(sub, "bl_rna"):
                _reset_to_defaults(sub)
            continue
        data.property_unset(pid)


class OpResetWheelTheme(OperatorAction):
    """Reset the wheel theme colors and sizes (both Dark and Light palettes) to their defaults. The theme mode (Auto / Dark / Light) is kept"""
    bl_label = "Reset Wheel Theme"

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        from ..prefs import BlendWheelPrefs
        _reset_to_defaults(BlendWheelPrefs.get_prefs(context).wheel.theme, keep=frozenset({"theme_mode"}))
        return {'FINISHED'}


class OpSaveBackupAddonPreferences(OperatorAction):
    """Save/backup addon preferences into the user-data JSON file."""
    bl_label = "Save/Backup Addon Preferences"

    def action(self, context, event):
        try:
            from ..prefs import BlendWheelPrefs

            prefs = BlendWheelPrefs.get_prefs(context)
            out_path = prefs.save()
            self.report({"INFO"}, f"Addon preferences saved to: {out_path}")
            return True
        except Exception as ex:
            return f"Failed to save addon preferences: {ex}"
