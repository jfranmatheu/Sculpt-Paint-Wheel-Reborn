
from typing import Callable, Dict

from bpy.types import Context, SpaceView3D, SpaceImageEditor, SpaceNodeEditor

from ...utils.callback_utils import CallbackDict, CallbackList


draw_2d_callbacks = CallbackDict()
draw_3d_callbacks = CallbackDict()

remove_active_handlers: CallbackList = CallbackList()

space_type_to_id_type: Dict[str, type] = {
    'VIEW_3D': SpaceView3D,
    'IMAGE_EDITOR': SpaceImageEditor,
    'NODE_EDITOR': SpaceNodeEditor,
}


# ---------------------------------------------------------------------------------------

def add_draw_2d_callback(tool_id: str, draw_func: Callable):
    global draw_2d_callbacks
    draw_2d_callbacks += (tool_id, draw_func)

def add_draw_3d_callback(tool_id: str, draw_func: Callable):
    global draw_3d_callbacks
    draw_3d_callbacks += (tool_id, draw_func)


# ---------------------------------------------------------------------------------------

def enable_draw_callbacks(context: Context, tool_id: str, space_type: str):
    global draw_2d_callbacks, draw_3d_callbacks, remove_active_handlers
    # space_type_id = space_type_to_id_type[space_type]
    if tool_id in draw_2d_callbacks:
        draw_2d_handler = context.space_data.draw_handler_add(
            lambda context: draw_2d_callbacks(tool_id, context),
            (context,),
            'WINDOW',
            'POST_PIXEL'
        )
        remove_active_handlers.add_callback(lambda draw_handler_remove=context.space_data.draw_handler_remove, handler=draw_2d_handler: draw_handler_remove(handler, 'WINDOW'))
    if tool_id in draw_3d_callbacks:
        draw_3d_handler = context.space_data.draw_handler_add(
            lambda context: draw_3d_callbacks(tool_id, context),
            (context,),
            'WINDOW',
            'POST_VIEW'
        )
        remove_active_handlers.add_callback(lambda draw_handler_remove=context.space_data.draw_handler_remove, handler=draw_3d_handler: draw_handler_remove(handler, 'WINDOW'))

def disable_draw_callbacks():
    global remove_active_handlers
    remove_active_handlers()
    remove_active_handlers.clear_callbacks()

def unregister():
    global draw_2d_callbacks, draw_3d_callbacks
    disable_draw_callbacks()

    draw_2d_callbacks.clear_callbacks()
    draw_3d_callbacks.clear_callbacks()
