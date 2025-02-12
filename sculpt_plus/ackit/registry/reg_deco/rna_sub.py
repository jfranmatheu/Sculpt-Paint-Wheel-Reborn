from functools import wraps

import bpy

from .handlers import Handlers
from ...debug import debug_context, print_debug



owners = []

rna_listeners: dict[object, dict] = {}
ctx_rna_listeners: dict[object, dict] = {}


def subscribe_to_rna_change(bpy_rna_type: type, attr_name: str, data_path: str | None = None, persistent: bool = False):
    def decorator(decorated_func):
        def rna_callback_decorator(_decorated_func):
            @wraps(_decorated_func)
            def wrapper(*args, **kwargs):
                # print_debug(f"RNA change {bpy_rna_type.__name__}.{attr_name}")
                ctx = bpy.context
                if data_path is not None:
                    data = ctx.path_resolve(data_path)
                else:
                    data = getattr(ctx, bpy_rna_type.__name__.lower(), None)
                _decorated_func(ctx, data, getattr(data, attr_name) if data is not None else None)
            return wrapper

        owner = object()
        options = set()
        if persistent:
            options.add('PERSISTENT')
        rna_listeners[(bpy_rna_type, attr_name)] = {
            'key': (bpy_rna_type, attr_name),
            'owner': owner,
            'args': (),
            'notify': rna_callback_decorator(decorated_func),
            'options': options
        }
    return decorator


def subscribe_to_rna_change_based_on_context(data_path: str, attr_name: str, persistent: bool,):
    def decorator(decorated_func):
        def rna_callback_decorator(_decorated_func):
            @wraps(_decorated_func)
            def wrapper(*args, **kwargs):
                # print_debug(f"RNA change {bpy_rna_type.__name__}.{attr_name}")
                ctx = bpy.context
                data = ctx.path_resolve(data_path)
                _decorated_func(ctx, data, getattr(data, attr_name))
            return wrapper

        owner = object()
        options = set()
        if persistent:
            options.add('PERSISTENT')
        ctx = bpy.context
        ctx_rna_listeners[data_path + '.' + attr_name] = {
            'key': data_path + '.' + attr_name,
            'owner': owner,
            'args': (),
            'notify': rna_callback_decorator(decorated_func),
            'options': options
        }
    return decorator


def unregister_rna_sub():
    for owner in owners:
        bpy.msgbus.clear_by_owner(owner)
    owners.clear()
    print_debug("Clear RNA Subscriptions")

def register_rna_sub():
    with debug_context('RNA Subscriptions') as _print_debug:
        for data in rna_listeners.values():
            bpy_data, data_attr = data['key']
            _print_debug(f"{bpy_data.__name__} . {data_attr} -> '{data['notify'].__name__}', in module '{data['notify'].__module__}'")
            bpy.msgbus.subscribe_rna(**data)
            owners.append(data['owner'])

        context = bpy.context
        for data in ctx_rna_listeners.values():
            _print_debug(f"[CONTEXT] . {data['key']} -> '{data['notify'].__name__}', in module '{data['notify'].__module__}'")
            _data = data.copy()
            _data['key'] = context.path_resolve(data['key'], False)
            bpy.msgbus.subscribe_rna(**data)
            owners.append(data['owner'])


@Handlers.LOAD_POST(persistent=True)
def on_load_post(context, *args):
    # Make sure we register the RNA_Subscriptions on .blend file load.
    unregister_rna_sub()
    register_rna_sub()


# ----------------------------------------------------------------

def register():
    # Make sure we register the RNA_Subscriptions on addon register.
    bpy.app.timers.register(register_rna_sub, first_interval=0.1, persistent=False)

def unregister():
    unregister_rna_sub()
