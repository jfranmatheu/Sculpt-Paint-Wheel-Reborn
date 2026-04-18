import bpy
from dataclasses import dataclass
from typing import Optional, Any, Callable
from .._base import BType

class BType_NodeSocket(BType, bpy.types.NodeSocket):
    pass

@dataclass
class SocketSpec:
    name: Optional[str]
    type_id: str
    label: Optional[str]
    kind: str

def _type_name(x: Any) -> str:
    if isinstance(x, str):
        return x
    if hasattr(x, "__name__"):
        return x.__name__
    return str(x)



SOCKET_TYPE_MAP = {
    "Float": None,
    "Int": None,
    "Bool": None,
}

def _normalize_type_id(type_id: str) -> str:
    t = type_id.strip()
    if not t:
        return "Float"
    return t[0].upper() + t[1:].lower()

def get_socket_bl_id(type_id: str) -> str:
    t = _normalize_type_id(type_id)
    bl = SOCKET_TYPE_MAP.get(t)
    if isinstance(bl, str) and bl:
        return bl
    # Fallback to blender built-ins if custom not ready
    if t == "Int":
        return "NodeSocketInt"
    if t == "Bool":
        return "NodeSocketBool"
    return "NodeSocketFloat"

class SocketRef:
    def __init__(self, spec: SocketSpec):
        self.spec = spec
    def __get__(self, instance, owner):
        if instance is None:
            return self.spec
        name = self.spec.label or self.spec.name
        if self.spec.kind == "INPUT":
            for s in instance.inputs:
                if s.name == name:
                    return s
        else:
            for s in instance.outputs:
                if s.name == name:
                    return s
        return None

class SocketDef:
    def __init__(self, type_id: str):
        self.type_id = _type_name(type_id)
        self.label: Optional[str] = None
        self.tooltip: Optional[str] = None
        self.multi_input: bool = False
        self.default: Any = None
        self.min: Optional[float] = None
        self.max: Optional[float] = None
        self.update_cb: Optional[Callable] = None
        self.reset_on_copy_flag: bool = False
        self.kind: Optional[str] = None
        self.dynamic_group: Optional[str] = None
        self.dynamic_label_fmt: Optional[str] = None
        self.dynamic_min_count: int = 1
    def label_(self, text: str):
        self.label = text
        return self
    def tooltip_(self, text: str):
        self.tooltip = text
        return self
    def default_(self, value: Any):
        self.default = value
        return self
    def range_(self, min: Optional[float] = None, max: Optional[float] = None):
        self.min = min
        self.max = max
        return self
    def multi(self):
        self.multi_input = True
        return self
    def update(self, fn: Callable):
        self.update_cb = fn
        return self
    def reset_on_copy(self):
        self.reset_on_copy_flag = True
        return self
    def dynamic(self, group: str, label_fmt: str = "Value {i}", min_count: int = 1):
        self.dynamic_group = group
        self.dynamic_label_fmt = label_fmt
        self.dynamic_min_count = max(1, int(min_count))
        return self
    def input(self):
        self.kind = "INPUT"
        return self
    def output(self):
        self.kind = "OUTPUT"
        return self

class Socket:
    @staticmethod
    def Int(**kwargs) -> SocketDef:
        sd = SocketDef("Int")
        Socket._apply_kwargs(sd, **kwargs)
        return sd
    @staticmethod
    def Float(**kwargs) -> SocketDef:
        sd = SocketDef("Float")
        Socket._apply_kwargs(sd, **kwargs)
        return sd
    @staticmethod
    def Bool(**kwargs) -> SocketDef:
        sd = SocketDef("Bool")
        Socket._apply_kwargs(sd, **kwargs)
        return sd
    @staticmethod
    def _apply_kwargs(sd: SocketDef, **kwargs):
        if "label" in kwargs: sd.label_(kwargs["label"])
        if "tooltip" in kwargs: sd.tooltip_(kwargs["tooltip"])
        if "default" in kwargs: sd.default_(kwargs["default"])
        if "min" in kwargs or "max" in kwargs: sd.range_(kwargs.get("min"), kwargs.get("max"))
        if kwargs.get("multi"): sd.multi()
        if "update" in kwargs and kwargs["update"]: sd.update(kwargs["update"])
        if kwargs.get("reset_on_copy"): sd.reset_on_copy()
        dg = kwargs.get("dynamic")
        if isinstance(dg, dict):
            sd.dynamic(dg.get("group", "Values"), dg.get("label_fmt", "Value {i}"), dg.get("min_count", 1))

class TM_NodeSocketFloat(BType_NodeSocket):
    bl_label = "Float"
    value: bpy.props.FloatProperty(
        name="Value",
        description="Socket value",
        update=lambda self, ctx: getattr(self, "_on_update_value", lambda c: None)(ctx),
    )
    def _on_update_value(self, ctx):
        try:
            self.node._update_socket_value(self, self.value)
        except Exception:
            pass
    def draw(self, context, layout, node, text):
        if self.is_output or self.is_linked:
            layout.label(text=text)
        else:
            layout.prop(self, "value", text=text)
    @classmethod
    def draw_color_simple(cls):
        return (0.2, 0.6, 1.0, 0.5)
    @classmethod
    def on_register(cls):
        _bind_custom_bl_ids()

class TM_NodeSocketInt(BType_NodeSocket):
    bl_label = "Int"
    value: bpy.props.IntProperty(
        name="Value",
        description="Socket value",
        update=lambda self, ctx: getattr(self, "_on_update_value", lambda c: None)(ctx),
    )
    def _on_update_value(self, ctx):
        try:
            self.node._update_socket_value(self, self.value)
        except Exception:
            pass
    def draw(self, context, layout, node, text):
        if self.is_output or self.is_linked:
            layout.label(text=text)
        else:
            layout.prop(self, "value", text=text)
    @classmethod
    def draw_color_simple(cls):
        return (0.6, 0.6, 0.2, 0.5)
    @classmethod
    def on_register(cls):
        _bind_custom_bl_ids()

class TM_NodeSocketBool(BType_NodeSocket):
    bl_label = "Bool"
    value: bpy.props.BoolProperty(
        name="Value",
        description="Socket value",
        update=lambda self, ctx: getattr(self, "_on_update_value", lambda c: None)(ctx),
    )
    def _on_update_value(self, ctx):
        try:
            self.node._update_socket_value(self, self.value)
        except Exception:
            pass
    def draw(self, context, layout, node, text):
        if self.is_output or self.is_linked:
            layout.label(text=text)
        else:
            layout.prop(self, "value", text=text)
    @classmethod
    def draw_color_simple(cls):
        return (0.2, 0.9, 0.2, 0.5)
    @classmethod
    def on_register(cls):
        _bind_custom_bl_ids()

def _bind_custom_bl_ids():
    try:
        SOCKET_TYPE_MAP["Float"] = TM_NodeSocketFloat.bl_idname
        SOCKET_TYPE_MAP["Int"] = TM_NodeSocketInt.bl_idname
        SOCKET_TYPE_MAP["Bool"] = TM_NodeSocketBool.bl_idname
    except Exception:
        pass
