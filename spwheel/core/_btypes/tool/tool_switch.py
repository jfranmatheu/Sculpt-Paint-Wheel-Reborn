from typing import Callable

import bl_ui.space_toolsystem_common as toolsystem_common
from bpy.types import Context

from ...utils.wrap_fn import wrap_function
from ...utils.callback_utils import CallbackDict
from .tool_statusbar import enable_draw_statusbar, disable_draw_statusbar
from .tool_draw import enable_draw_callbacks, disable_draw_callbacks
from .common import is_self_tool
from ...debug import print_debug

tool_enter_callbacks: CallbackDict = CallbackDict()
tool_exit_callbacks: CallbackDict = CallbackDict()

last_active_tool_id_per_space_type = {}
last_context_mode = None


def tool_enter(context: Context, space_type: str, tool_id: str):
    global tool_enter_callbacks
    tool_enter_callbacks(tool_id, context)
    enable_draw_statusbar(context, tool_id)
    enable_draw_callbacks(context, tool_id, space_type)

def tool_exit(context: Context, space_type: str, tool_id: str):
    global tool_exit_callbacks
    tool_exit_callbacks(tool_id, context)
    disable_draw_statusbar(context)
    disable_draw_callbacks()


def tool_switch_post(context: Context, space_type: str, item_idname: str | None, *, as_fallback=False) -> None:
    global last_active_tool_id_per_space_type, last_context_mode
    active_tool_id: str | None = item_idname
    last_tool_id: str | None = last_active_tool_id_per_space_type.get(space_type, None)

    print_debug(f"ℹ️  Tool switch post: {last_tool_id} -> {active_tool_id} (space_type: {space_type}, mode: {context.mode})")

    current_context_mode = context.mode
    if last_context_mode is None:
        # FIRST TIME
        last_context_mode = current_context_mode
    elif last_context_mode != current_context_mode:
        # A CHANGE IN CONTEXT MODE TRIGGERED A TOOL SWITCH
        pass

    # NO TOOL SWITCH
    if last_tool_id == active_tool_id:
        last_context_mode = current_context_mode
        return

    # TOOL EXIT
    if last_tool_id is not None and is_self_tool(last_tool_id):
        tool_exit(context, space_type, last_tool_id)
        last_active_tool_id_per_space_type[space_type] = None

    # TOOL ENTER
    if is_self_tool(active_tool_id):
        tool_enter(context, space_type, active_tool_id)
        last_active_tool_id_per_space_type[space_type] = active_tool_id

    last_context_mode = current_context_mode


# ---------------------------------------------------------------------------------------

def add_tool_enter_callback(tool_id: str, callback: Callable):
    """ Add a callback to be called when a tool is entered. """
    global tool_enter_callbacks
    tool_enter_callbacks += (tool_id, callback)

def add_tool_exit_callback(tool_id: str, callback: Callable):
    """ Add a callback to be called when a tool is exited. """
    global tool_exit_callbacks
    tool_exit_callbacks += (tool_id, callback)


# ---------------------------------------------------------------------------------------

restore_fn = None

def enable_tool_switch_handler():
    global restore_fn
    if restore_fn is not None:
        print_debug("⚠️ Warning: enable_tool_switch_handler() is already enabled.")
        return
    restore_fn = wrap_function(toolsystem_common.activate_by_id, post_func=tool_switch_post)

def disable_tool_switch_handler():
    """ To manually disable the tool switch handler.
        NOTE: it will be automatically disabled when unregistering the extension.
    """
    global restore_fn
    if restore_fn is None:
        print_debug("⚠️ Warning: disable_tool_switch_handler() is already disabled.")
        return
    restore_fn()
    restore_fn = None

def register():
    global tool_enter_callbacks, tool_exit_callbacks
    if tool_enter_callbacks or tool_exit_callbacks:
        enable_tool_switch_handler()

def unregister():
    global last_context_mode, last_active_tool_id_per_space_type, tool_enter_callbacks, tool_exit_callbacks
    last_context_mode = None
    last_active_tool_id_per_space_type.clear()

    tool_enter_callbacks.clear_callbacks()
    tool_exit_callbacks.clear_callbacks()
