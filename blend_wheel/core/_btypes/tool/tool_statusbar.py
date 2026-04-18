from typing import Callable

import bpy
from bpy.types import Context, UILayout

from ...utils.callback_utils import CallbackDict


draw_statusbar_callbacks = CallbackDict()
is_enabled = False


def draw_statusbar_header(context: Context, layout: UILayout, tool_idname: str):
    """ Override the statusbar header to display custom tools hotkeys. """
    # Tool statusbar, keymaps, etc.
    global draw_statusbar_callbacks
    draw_statusbar_callbacks(tool_idname, context, layout, default=lambda ctx, layout: layout.label(text="No keymaps defined for this tool"))

    layout.separator_spacer()

    # Messages
    layout.template_reports_banner()

    # Progress Bar
    layout.template_running_jobs()

    layout.separator_spacer()

    row = layout.row()
    row.alignment = 'RIGHT'

    # Stats & Info
    layout.template_status_info()


# ---------------------------------------------------------------------------------------

def add_draw_statusbar_callback(tool_id: str, callback: Callable) -> None:
    global draw_statusbar_callbacks
    draw_statusbar_callbacks += (tool_id, callback)


# ---------------------------------------------------------------------------------------

def enable_draw_statusbar(context: Context, tool_id: str) -> None:
    global is_enabled
    if is_enabled:
        return
    context.workspace.status_text_set(lambda statusbar_header, context: draw_statusbar_header(context, statusbar_header.layout, tool_id))
    is_enabled = True

def reload_draw_statusbar(context: Context | None = None, tool_id: str | None = None) -> None:
    if context is None:
        context = bpy.context
    if tool_id is None:
        tool_id = context.workspace.tools[0].idname
    disable_draw_statusbar(context)
    enable_draw_statusbar(context, tool_id)

def disable_draw_statusbar(context: Context | None = None) -> None:
    global is_enabled
    if not is_enabled:
        return
    if context is None:
        context = bpy.context
    context.workspace.status_text_set(None)
    is_enabled = False

def unregister():
    global draw_statusbar_callbacks
    disable_draw_statusbar()
    draw_statusbar_callbacks.clear_callbacks()
