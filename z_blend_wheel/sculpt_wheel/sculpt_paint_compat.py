"""Blender 5+: UnifiedPaintSettings moved under mode-specific tool settings (e.g. sculpt)."""

from __future__ import annotations

from typing import Any

from bpy.types import Context


def get_sculpt_unified_paint_settings(context: Context) -> Any | None:
    """Return unified paint settings for sculpt, or None if unavailable.

    Blender 5.0+: ``tool_settings.sculpt.unified_paint_settings``
    Older: ``tool_settings.unified_paint_settings``
    """
    ts = context.tool_settings
    sculpt = getattr(ts, "sculpt", None)
    if sculpt is not None:
        ups = getattr(sculpt, "unified_paint_settings", None)
        if ups is not None:
            return ups
    return getattr(ts, "unified_paint_settings", None)
