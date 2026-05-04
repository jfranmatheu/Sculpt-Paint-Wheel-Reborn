"""Operators for brush metadata items in the active brush set."""

from bpy.props import IntProperty

from ..core.bl_types import OperatorAction
from ..pg.pg_wheel_storage import WheelStorage
from ..utils.ups import get_active_brush_mode, get_tool_settings


class OpPollActiveBrushSet:
    @classmethod
    def poll_operator(cls, context) -> bool | str:
        if WheelStorage.get_by_mode(context).active_brush_set is None:
            return "No active brush set"
        return True


class OpPollActiveBrushItem(OpPollActiveBrushSet):
    @classmethod
    def poll_operator(cls, context) -> bool | str:
        is_valid = super().poll_operator(context)
        if is_valid is not True:
            return is_valid
        active_set = WheelStorage.get_by_mode(context).active_brush_set
        idx = active_set.active_item_index
        if idx < 0 or idx >= len(active_set.items):
            return "No active brush item"
        return True


class OpBrushListAdd(OperatorAction, OpPollActiveBrushSet):
    """Add current active brush to active brush set."""
    bl_label = "Add active brush to active brush set"

    def action(self, context, event):
        active_set = WheelStorage.get_by_mode(context).active_brush_set
        ts = get_tool_settings(context)
        if not ts or not getattr(ts, "brush", None):
            return "No active brush"

        weak_ref = getattr(ts, "brush_asset_reference", None)
        key = (
            getattr(weak_ref, "asset_library_type", "") if weak_ref else "",
            getattr(weak_ref, "asset_library_identifier", "") if weak_ref else "",
            getattr(weak_ref, "relative_asset_identifier", "") if weak_ref else "",
            ts.brush.name,
            get_active_brush_mode(context),
        )
        for item in active_set.items:
            existing = (
                getattr(item, "asset_library_type", ""),
                getattr(item, "asset_library_identifier", ""),
                getattr(item, "relative_asset_identifier", ""),
                getattr(item, "name", ""),
                getattr(item, "mode", ""),
            )
            if existing == key:
                return "Brush is already in the active brush set"

        active_set.add_active_brush(context)
        active_set.active_item_index = len(active_set.items) - 1


class OpBrushListRemove(OperatorAction, OpPollActiveBrushItem):
    """Remove selected brush metadata from active brush set."""
    bl_label = "Remove selected brush metadata from active brush set"

    def action(self, context, event):
        active_set = WheelStorage.get_by_mode(context).active_brush_set
        idx = active_set.active_item_index
        active_set.items.remove(idx)
        if len(active_set.items) == 0:
            active_set.active_item_index = -1
        else:
            active_set.active_item_index = min(idx, len(active_set.items) - 1)


class OpBrushListMove(OperatorAction, OpPollActiveBrushItem):
    """Move selected brush metadata up/down in active brush set."""
    bl_label = "Move selected brush metadata up/down in active brush set"

    direction: IntProperty(
        name="Direction",
        description="The direction to move the active brush metadata item",
        default=0,
        min=-1,
        max=1,
    )

    def action(self, context, event):
        active_set = WheelStorage.get_by_mode(context).active_brush_set
        count = len(active_set.items)
        if count <= 1:
            return
        src = active_set.active_item_index
        if self.direction == 1:
            dst = (src - 1 + count) % count
        elif self.direction == -1:
            dst = (src + 1) % count
        else:
            return
        active_set.items.move(src, dst)
        active_set.active_item_index = dst
