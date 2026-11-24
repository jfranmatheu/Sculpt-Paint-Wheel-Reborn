"""Operators related to addon preferences persistence."""

from ..core.bl_types import OperatorAction


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
