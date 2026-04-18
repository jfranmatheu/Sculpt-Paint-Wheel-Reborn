from typing import Callable, Type
from bpy.types import Context, Event, Macro

from bpy.utils import register_class, unregister_class

from ...globals import GLOBALS
from .btype_op_base import BType_Operator
from .btype_op_action import BType_OpAction


_macros: list['MacroCreator'] = []


class MacroCreator:

    def __init__(self, label: str, use_redo_panel: bool = True) -> None:
        self.registered = False
        self.macro_cls = None
        idname = label.replace(' ', '_').lower()
        self.name = f"{GLOBALS.ADDON.ID_UPPER}_OT_{idname}"
        self.kwargs = {
            'bl_label': label,
            'bl_idname': f"{GLOBALS.ADDON.ID}.{idname}",
            'bl_options': {'REGISTER', 'UNDO'} if use_redo_panel else {}
        }
        self.pre_callback = None
        self.post_callback = None
        self.pre_operator_cls = None
        self.post_operator_cls = None
        self.operators = {}
        _macros.append(self)

    def set_poll(self, poll: Callable[[Context], bool]) -> 'MacroCreator':
        self.kwargs['poll'] = classmethod(lambda cls, context: poll(context) if poll else True)
        return self

    def set_pre_callback(self, pre: Callable[[Context, Event], None]) -> 'MacroCreator':
        self.pre_callback = pre
        return self

    def set_post_callback(self, post: Callable[[Context, Event], None]) -> 'MacroCreator':
        self.post_callback = post
        return self

    def add_operator(self, operator: Type[BType_Operator] | str, **properties: dict) -> 'MacroCreator':
        self.operators[operator if isinstance(operator, str) else operator.bl_idname] = properties
        return self

    def register(self):
        if self.registered:
            return

        if self.pre_callback:
            pre_op_cls = type(
                f"{self.name}_Pre",
                (BType_OpAction,),
                {
                    'action': self.pre_callback,
                }
            )
            pre_op_cls.tag_register()
            register_class(pre_op_cls)
            self.pre_operator_cls = pre_op_cls
        if self.post_callback:
            post_op_cls = type(
                f"{self.name}_Post",
                (BType_OpAction,),
                {
                    'action': self.post_callback,
                }
            )
            post_op_cls.tag_register()
            register_class(post_op_cls)
            self.post_operator_cls = post_op_cls

        new_macro_cls = type(
            self.name,
            (Macro,),
            self.kwargs,
        )
        if self.pre_operator_cls:
            new_macro_cls.define(self.pre_operator_cls.bl_idname)
        for op_idname, op_props in self.operators.items():
            step = new_macro_cls.define(op_idname)
            props = step.properties
            for prop_name, prop_value in op_props.items():
                setattr(props, prop_name, prop_value)
        if self.post_operator_cls:
            new_macro_cls.define(self.post_operator_cls.bl_idname)

        register_class(new_macro_cls)
        self.macro_cls = new_macro_cls
        self.registered = True

    def unregister(self):
        if not self.registered:
            return
        unregister_class(self.macro_cls)
        if self.pre_operator_cls:
            unregister_class(self.pre_operator_cls)
            self.pre_operator_cls = None
        if self.post_operator_cls:
            unregister_class(self.post_operator_cls)
            self.post_operator_cls = None
        self.registered = False
        self.macro_cls = None


def register():
    for macro in _macros:
        macro.register()
        
def unregister():
    for macro in _macros:
        macro.unregister()
