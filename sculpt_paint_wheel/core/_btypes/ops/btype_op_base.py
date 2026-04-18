import bpy
from bpy.types import Context, Event, Operator

from ...utils.op_return import OpReturn as _OpReturn
from ..ui.btype_ui_base import BType_UICommon


class BType_Operator(BType_UICommon, Operator):
    active_operator: 'BType_Operator' = None
    _is_modal: bool = False

    OpReturn = _OpReturn

    @classmethod
    def decorator(
        cls,
        *,
        register: bool = True,
        undo: bool = True,
        internal: bool = False,
        blocking: bool = False,
        options: set[str] | None = None,
        **kwargs,
    ):
        bl_options = set(options or set())
        if register:
            bl_options.add("REGISTER")
        if undo:
            bl_options.add("UNDO")
        if internal:
            bl_options.add("INTERNAL")
        if blocking:
            bl_options.add("BLOCKING")
        return super().decorator(bl_options=bl_options, **kwargs)


    # Run Operator -------------------------------------------------------------------------

    @classmethod
    def run(cls, undo: bool = True, execute_method: str = 'EXEC_DEFAULT', **kwargs) -> set[str]:
        getattr(bpy.ops, cls.bl_idname)(undo, execute_method, **kwargs)

    @classmethod
    def run_invoke(cls) -> set[str]:
        return cls.run(execute_method='INVOKE_DEFAULT')


    # Invoke (UI) Operator -------------------------------------------------------------------------

    @classmethod
    def invoke_dialog_props(cls, context: Context, width: int = 300) -> set[str]:
        """
        Invokes the dialog with the properties of the operator.
        """
        return context.window_manager.invoke_props_dialog(cls, width=width)

    @classmethod
    def invoke_dialog_confirm(cls, context: Context, event: Event, title: str = "", message: str = "", confirm_text: str = "", icon: str = "") -> set[str]:
        """
        Invokes the dialog with a confirm message.
        """
        return context.window_manager.invoke_confirm(cls, event, title=title, message=message, confirm_text=confirm_text, icon=icon)


    # Polling Operator -------------------------------------------------------------------------

    @classmethod
    def poll(cls, context: Context) -> bool:
        res = cls.poll_operator(context)
        if isinstance(res, str):
            cls.poll_message_set(res)
            return False
        elif isinstance(res, bool):
            return res
        return False

    @classmethod
    def poll_operator(cls, context: Context) -> bool | str:
        """
        Returns True if the operator can be run, False if it cannot be run, or a string message if the operator cannot be run.
        """
        return True
