import bpy
from typing import Any, Dict, List
from .._base import BType
from .node_socket import SocketDef, SocketSpec, SocketRef, get_socket_bl_id
from dataclasses import dataclass
from typing import Optional, Callable

class BType_Node(BType, bpy.types.Node):
    _input_specs: List[SocketSpec] = []
    _output_specs: List[SocketSpec] = []
    _socket_defs: Dict[str, SocketDef] = {}
    _prop_defs: Dict[str, Any] = {}

    @classmethod
    def tag_register(cls, **kwargs):
        inputs: List[SocketSpec] = []
        outputs: List[SocketSpec] = []
        cls._socket_defs = {}
        cls._prop_defs = {}
        for name, ann in getattr(cls, "__annotations__", {}).items():
            if isinstance(ann, SocketDef):
                sd: SocketDef = ann
                kind = sd.kind or ("INPUT" if name.startswith("in_") else "OUTPUT" if name.startswith("out_") else "INPUT")
                if kind == "OUTPUT":
                    sd.multi_input = False
                    sd.dynamic_group = None
                spec = SocketSpec(name=name, type_id=sd.type_id, label=sd.label or name, kind=kind)
                if kind == "INPUT":
                    inputs.append(spec)
                else:
                    outputs.append(spec)
                cls._socket_defs[name] = sd
        # Convert proxy node properties (PropDef) to actual bpy.props
        for name, value in list(cls.__dict__.items()):
            pd = getattr(value, "__propdef__", None)
            if pd is not None:
                cls._prop_defs[name] = pd
                prop = _make_bpy_property(pd, name)
                setattr(cls, name, prop)
        cls._input_specs = inputs
        cls._output_specs = outputs
        annotations = {}
        for spec in inputs + outputs:
            setattr(cls, spec.name, SocketRef(spec))
            annotations[spec.name] = bpy.types.NodeSocket
        cls.__annotations__ = annotations
        return super().tag_register(**kwargs)

    def init(self, context):
        for spec in self._input_specs:
            t = get_socket_bl_id(spec.type_id)
            sd = self._socket_defs.get(spec.name)
            if sd and sd.dynamic_group:
                n = max(1, sd.dynamic_min_count)
                for i in range(1, n + 1):
                    label = (sd.dynamic_label_fmt or f"{sd.dynamic_group} {{i}}").format(i=i)
                    self.inputs.new(t, label, use_multi_input=sd.multi_input)
            else:
                lbl = (sd.label or spec.label or spec.name) if sd else (spec.label or spec.name)
                self.inputs.new(t, lbl, use_multi_input=(sd.multi_input if sd else False))
        for spec in self._output_specs:
            t = get_socket_bl_id(spec.type_id)
            sd = self._socket_defs.get(spec.name)
            lbl = (sd.label or spec.label or spec.name) if sd else (spec.label or spec.name)
            self.outputs.new(t, lbl)

    def update(self):
        for name, sd in self._socket_defs.items():
            if sd.dynamic_group and (sd.kind or ("INPUT" if name.startswith("in_") else "OUTPUT")) == "INPUT":
                group = sd.dynamic_group
                sockets = [s for s in self.inputs if isinstance(s.name, str) and s.name.startswith(group)]
                if sockets:
                    last = sockets[-1]
                    if last.is_linked:
                        t = get_socket_bl_id(sd.type_id)
                        label = (sd.dynamic_label_fmt or f"{group} {{i}}").format(i=len(sockets) + 1)
                        self.inputs.new(t, label, use_multi_input=sd.multi_input)
                    else:
                        while len(sockets) > sd.dynamic_min_count and sockets and not sockets[-1].is_linked:
                            self.inputs.remove(sockets[-1])
                            sockets = [s for s in self.inputs if isinstance(s.name, str) and s.name.startswith(group)]

    def _update_socket_value(self, socket, value: Any):
        try:
            self.update()
            if hasattr(self, "update_socket_value"):
                self.update_socket_value(socket, value)
            sd = self._find_socket_def_for_socket(socket)
            if sd and sd.update_cb:
                try:
                    sd.update_cb(self, bpy.context, socket.name, value)
                except Exception:
                    pass
        except Exception:
            pass

    def _find_socket_def_for_socket(self, socket):
        name = socket.name
        for sd in self._socket_defs.values():
            if sd.dynamic_group:
                if isinstance(name, str) and name.startswith(sd.dynamic_group):
                    return sd
            else:
                if sd.label == name:
                    return sd
        return None

    def _update_property(self, prop_name: str, prop_value: Any):
        try:
            self.update()
            if hasattr(self, "update_property"):
                self.update_property(prop_name, prop_value)
            pd = self._prop_defs.get(prop_name)
            if pd and pd.update_cb:
                try:
                    pd.update_cb(self, bpy.context, prop_name, prop_value)
                except Exception:
                    pass
        except Exception:
            pass

def _make_bpy_property(pd, name: str):
    kwargs = {}
    if pd.label:
        kwargs["name"] = pd.label
    if pd.tooltip:
        kwargs["description"] = pd.tooltip
    if pd.default is not None:
        kwargs["default"] = pd.default
    if pd.min is not None:
        kwargs["min"] = pd.min
    if pd.max is not None:
        kwargs["max"] = pd.max
    def _upd(self, context):
        try:
            self._update_property(name, getattr(self, name))
        except Exception:
            pass
    kwargs["update"] = _upd
    t = pd.type_id
    if t == "Float":
        return bpy.props.FloatProperty(**kwargs)
    if t == "Int":
        return bpy.props.IntProperty(**kwargs)
    if t == "Bool":
        return bpy.props.BoolProperty(**kwargs)
    if t == "String":
        return bpy.props.StringProperty(**kwargs)
    return bpy.props.StringProperty(**kwargs)

@dataclass
class PropDef:
    type_id: str
    label: Optional[str] = None
    tooltip: Optional[str] = None
    default: Any = None
    min: Optional[float] = None
    max: Optional[float] = None
    update_cb: Optional[Callable] = None

class _PropProxy:
    def __init__(self, pd: PropDef):
        self.__propdef__ = pd
    def label_(self, text: str):
        self.__propdef__.label = text
        return self
    def tooltip_(self, text: str):
        self.__propdef__.tooltip = text
        return self
    def default_(self, value: Any):
        self.__propdef__.default = value
        return self
    def range_(self, min: Optional[float] = None, max: Optional[float] = None):
        self.__propdef__.min = min
        self.__propdef__.max = max
        return self
    def update(self, fn: Callable):
        self.__propdef__.update_cb = fn
        return self

class Prop:
    @staticmethod
    def Float(**kwargs) -> _PropProxy:
        pd = PropDef("Float")
        _apply_pd_kwargs(pd, **kwargs)
        return _PropProxy(pd)
    @staticmethod
    def Int(**kwargs) -> _PropProxy:
        pd = PropDef("Int")
        _apply_pd_kwargs(pd, **kwargs)
        return _PropProxy(pd)
    @staticmethod
    def Bool(**kwargs) -> _PropProxy:
        pd = PropDef("Bool")
        _apply_pd_kwargs(pd, **kwargs)
        return _PropProxy(pd)
    @staticmethod
    def String(**kwargs) -> _PropProxy:
        pd = PropDef("String")
        _apply_pd_kwargs(pd, **kwargs)
        return _PropProxy(pd)

def _apply_pd_kwargs(pd: PropDef, **kwargs):
    if "label" in kwargs: pd.label = kwargs["label"]
    if "tooltip" in kwargs: pd.tooltip = kwargs["tooltip"]
    if "default" in kwargs: pd.default = kwargs["default"]
    if ("min" in kwargs) or ("max" in kwargs): pd.min = kwargs.get("min"); pd.max = kwargs.get("max")
    if "update" in kwargs and kwargs["update"]: pd.update_cb = kwargs["update"]
