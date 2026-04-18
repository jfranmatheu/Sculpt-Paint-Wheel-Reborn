from typing import Dict, Tuple, Type
from bpy.types import Context, Event, KeyConfig
from bpy.utils import register_class, unregister_class
from mathutils import Vector
from bl_ui.space_toolsystem_common import ToolActivePanelHelper, ToolSelectPanelHelper

from .btype_gz_tool_multi import BType_GZG_ToolMulti
from .btype_gz import BType_GZ
from .btype_gzg import BType_GZG

from ...utils.class_utils import is_method_overridden
from ...utils.op_return import OpReturn


tool_widgets = []


km_hotkeys=(
    'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z',
    'ZERO', 'ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX', 'SEVEN', 'EIGHT', 'NINE',
    'LEFT_ARROW', 'DOWN_ARROW', 'RIGHT_ARROW', 'UP_ARROW',
    'LEFTMOUSE', 'MIDDLEMOUSE', 'RIGHTMOUSE', 'PEN', 'ERASER', #'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE',
    'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'WHEELINMOUSE', 'WHEELOUTMOUSE',
    'RET', 'SPACE', 'BACK_SPACE', 'DEL',
    'TIMER'
)
km_op = 'gizmogroup.gizmo_tweak' # 'gizmogroup.gizmo_tweak' # 'gizmogroup.gizmo_select'

class WidgetKM:
    keymaps: Tuple[Dict[str, str | bool]] = () # 'event', 'value', 'alt', 'shift', 'ctrl', ...

    @classmethod
    def setup_keymap(cls, gzg_cls, keyconfig: KeyConfig):
        km = keyconfig.keymaps.get(gzg_cls.bl_idname, None)
        if km and km.keymap_items and len(km.keymap_items) > 1: return km
        km = keyconfig.keymaps.new(name=gzg_cls.bl_idname, space_type='VIEW_3D', region_type='WINDOW')
        if cls.keymaps:
            for km_data in cls.keymaps:
                event_type = km_data['type']
                event_value = km_data['value']
                alt = km_data.get('alt', False)
                shift = km_data.get('shift', False)
                ctrl = km_data.get('ctrl', False)
                km.keymap_items.new(km_op, event_type, event_value, alt=alt, shift=shift, ctrl=ctrl)
        else:
            for key in km_hotkeys: km.keymap_items.new(km_op, key, 'ANY', any=True);km.keymap_items.new(km_op, key, 'PRESS', any=True);km.keymap_items.new(km_op, key, 'RELEASE', any=True)
        # km.keymap_items.new(km_op, 'LEFT_ALT', 'ANY', alt=True)
        return km


class BType_ToolWidget(WidgetKM):
    gz_options: set[str] = set()
    _is_registered: bool = False
    _gz_cls: Type[BType_GZ] = None
    _gzg_cls: Type[BType_GZG] = None
    _tool_cls = None
    _tool_idname: str = '' # Set by BType_WorkspaceTool on registering...
    _instance: 'BType_ToolWidget' = None
    is_hovered: bool = False

    bl_space_type: str = 'VIEW_3D'
    bl_region_type: str = 'WINDOW'

    use_test_keymaps: bool = True # If this is False and keymaps == (), then no keymaps will be setup, instead Blender internal keymaps will be used.

    @classmethod
    def new_type(cls, idname: str = '') -> Type['BType_ToolWidget']:
        return type(f'{cls.__name__}_{idname}', (cls, ), {})

    def __init__(self) -> None:
        self.is_hovered = False
        self.reg_size = Vector((0.0, 0.0))
        self.init()

    def init(self) -> None:
        pass

    @classmethod
    def get(cls) -> 'BType_ToolWidget':
        if not cls._instance:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def register(cls) -> None:
        if cls._is_registered:
            return
        cls._is_registered = True
        instance = cls.get()

        kwargs = {
            '_tool_widget_cls': cls,
            'setup': lambda self: self.__class__._tool_widget_cls.get()._setup(),
            'test_select': lambda self, context, location: self.__class__._tool_widget_cls.get()._test_select(context, location),
            'invoke': lambda self, context, event: self.__class__._tool_widget_cls.get()._invoke(context, event),
            'modal': lambda self, context, event, tweak: self.__class__._tool_widget_cls.get().modal(context, event, tweak),
            'exit': lambda self, context, cancel: self.__class__._tool_widget_cls.get().exit(context, cancel),
            'draw': lambda self, context: self.__class__._tool_widget_cls.get().draw(context),
        }
        new_gz_cls = type(f'{cls.__name__}GZ', (BType_GZ, cls), kwargs)
        new_gz_cls.tag_register()
        register_class(new_gz_cls)
        new_gz_cls.on_register()
        cls._gz_cls = new_gz_cls

        kwargs = {
            '_tool_widget_cls': cls,
            '_gizmos_cls': (cls._gz_cls, ),
            'bl_space_type': cls.bl_space_type,
            'bl_region_type': cls.bl_region_type,
            'poll': classmethod(lambda cls, context: cls._tool_widget_cls.get()._poll(context)),
            'refresh': lambda self, context: self.__class__._tool_widget_cls.get()._refresh(context),
            'invoke_prepare': lambda self, context, gizmo: self.__class__._tool_widget_cls.get().invoke_prepare(context),
            'draw_prepare': lambda self, context: self.__class__._tool_widget_cls.get().draw_prepare(context),
        }
        if cls.gz_options:
            kwargs['bl_options'] = cls.gz_options
        if cls.use_test_keymaps or cls.keymaps:
            kwargs['setup_keymap'] = classmethod(lambda cls, keyconfig: cls._tool_widget_cls.get().setup_keymap(cls, keyconfig))
        new_gzg_cls = type(f'{cls.__name__}GZG', (BType_GZG,), kwargs)
        new_gzg_cls.tag_register()
        register_class(new_gzg_cls)
        new_gzg_cls.on_register()
        cls._gzg_cls = new_gzg_cls

    @classmethod
    def unregister(cls) -> None:
        if not cls._is_registered:
            return
        cls._is_registered = False
        if cls._gz_cls:
            unregister_class(cls._gz_cls)
            cls._gz_cls.on_unregister()
            cls._gz_cls = None
        if cls._gzg_cls:
            unregister_class(cls._gzg_cls)
            cls._gzg_cls.on_unregister()
            cls._gzg_cls = None
        cls._instance = None

    # @classmethod
    # def setup_keymap(cls, keyconfig: KeyConfig) -> None:
    #     pass

    def _poll(self, context: Context) -> bool:
        if context.space_data.type != self.bl_space_type:
            return False
        if context.region.type != self.bl_region_type:
            return False
        # Check if active tool is current tool widget.
        active_tool = ToolSelectPanelHelper.tool_active_from_context(context)
        if active_tool.idname != self._tool_idname:
            return False
        return self.poll(context)

    def poll(self, context: Context) -> bool:
        return True

    def refresh(self, context: Context) -> None:
        pass

    def _test_select(self, context: Context, xy: tuple[int, int]) -> int:
        mouse = Vector(xy)
        res = self.test_hover(context, mouse)
        if res:
            if not self.is_hovered:
                # HOVER ENTER!
                self.is_hovered = True
                context.region.tag_redraw()
                self.on_hover_enter(context, mouse)
            return 1
        else:
            if self.is_hovered:
                # HOVER EXIT!
                self.is_hovered = False
                context.region.tag_redraw()
                self.on_hover_exit(context, mouse)
            return -1

    def _setup(self) -> None:
        self.setup()

    def _invoke(self, context: Context, event: Event) -> set[str]:
        # print(f"_invoke tool widget: {event.type}, {event.value}, {event.ctrl}, {event.shift}, {event.alt}, {event.direction}")
        if not self.is_hovered:
            return OpReturn.PASS
        return self.invoke(context, event)

    def _refresh(self, context: Context) -> None:
        reg_size = (context.region.width, context.region.height)
        if self.reg_size != reg_size:
            self.reg_size = reg_size
            self.on_region_size_change(context, Vector(reg_size))
            context.region.tag_redraw()
        self.refresh(context)

    def on_region_size_change(self, context: Context, reg_size: Vector) -> None:
        pass

    def setup(self) -> None:
        pass

    def on_hover_enter(self, context: Context, mouse: Vector) -> None:
        pass

    def on_hover_exit(self, context: Context, mouse: Vector) -> None:
        pass

    def test_hover(self, context: Context, mouse: Vector) -> bool:
        return False

    def invoke_prepare(self, context: Context) -> None:
        pass

    def invoke(self, context: Context, event: Event) -> set[str]:
        return {'FINISHED'}

    def modal(self, context: Context, event: Event, tweak: str) -> set[str]:
        return {'FINISHED'}

    def exit(self, context: Context, cancel: bool) -> None:
        pass

    def draw_prepare(self, context: Context) -> None:
        pass

    def draw(self, context: Context) -> None:
        pass




def late_init():
    global tool_widgets
    tool_widgets = BType_ToolWidget.__subclasses__()

def register():
    global tool_widgets
    
    for widget in tool_widgets:
        widget.register()

def unregister():
    global tool_widgets
    
    for widget in tool_widgets:
        widget.unregister()
