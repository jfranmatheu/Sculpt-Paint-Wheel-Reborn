from dataclasses import dataclass
from itertools import chain
from typing import Any, Callable, Dict, List, Optional, TypeAlias, Sequence
from uuid import uuid4

from bpy.types import Context
from gpu.shader import create_from_info
from gpu.types import GPUBatch, GPUShader, GPUShaderCreateInfo, GPUStageInterfaceInfo, GPUTexture
from gpu_extras.batch import batch_for_shader

from .types import GPU_TYPES, PRIMITIVE_TYPES, UniformType
from ..globals import RuntimeDrawGlobals


_shaders: Dict[str, 'ShaderBuilder'] = {}
_batch_cache: Dict[tuple[str, str, PRIMITIVE_TYPES], GPUBatch] = {}


TrisIndices: TypeAlias = Sequence[tuple[int, int, int]]


UniformGetter = Callable[[Context], Any] | Callable[[Context, Any], Any]


@dataclass(frozen=True)
class UniformSpec:
    name: str
    type: GPU_TYPES
    default: Any = None
    internal: bool = False
    getter: Optional[UniformGetter] = None
    tooltip: Optional[str] = None

    def is_required(self) -> bool:
        return self.default is None and self.getter is None

@dataclass(frozen=True)
class VertexInAttribute:
    name: str
    type: GPU_TYPES
    tooltip: Optional[str] = None

@dataclass(frozen=True)
class SamplerSpec:
    name: str
    type: str
    tooltip: Optional[str] = None


class UniformsSpecStorage:
    def __init__(self):
        self._internals: List[UniformSpec] = []
        self._positionals: List[UniformSpec] = []
        self._kwargs: List[UniformSpec] = []

    def append(self, value: UniformSpec):
        if value.internal:
            self._internals.append(value)
        elif value.default is None:
            self._positionals.append(value)
        else:
            self._kwargs.append(value)

    def __iter__(self):
        return iter(chain(self._positionals, self._kwargs, self._internals))


class ShaderBuilder:
    _info: GPUShaderCreateInfo
    _shader: Optional[GPUShader]
    _uniforms: UniformsSpecStorage
    _samplers: List[SamplerSpec]
    _vert_in_attributes: List[VertexInAttribute]

    def __init__(self,
                 name: str,
                 primitive: PRIMITIVE_TYPES = 'AUTO',
                 ndim: int = 3,
                 tooltip: Optional[str] = None,
                 pos_name: str = "pos",
                 init_ModelViewProjectionMatrix: bool = True,
                 init_fragColor_output: bool = True):
        self.uid = uuid4().hex
        self.name = name
        self.tooltip = tooltip
        self._ndim = ndim
        self.primitive = primitive
        self._vert_in_count = 0
        self._vert_out_count = 0
        self._fragment_out_count = 0
        self._info = GPUShaderCreateInfo()
        self._shader = None
        self._vert_in_attributes = []
        self._uniforms = UniformsSpecStorage()
        self._samplers = []
        self._varyings_iface: Optional[GPUStageInterfaceInfo] = None
        self.use_mvp_matrix = init_ModelViewProjectionMatrix
        self.use_fragColor_output = init_fragColor_output

        pos_tooltip = "Vertex coordinates"
        ndim_tooltip = "(2D | 3D)" if self.is_ndim_agnostic() else f"({self.ndim}D)"
        match primitive:
            case 'POINTS':
                pos_tooltip = f"{ndim_tooltip} Point coordinates"
            case 'LINES':
                pos_tooltip = f"{ndim_tooltip} Line coordinates"
            case 'TRIS':
                pos_tooltip = f"{ndim_tooltip} GeomSpec or a tuple with (tris_coords, tris_indices)"
            case 'ALL':
                pos_tooltip = f"For points and lines: sequence of primitives' {ndim_tooltip} coordinates. For shapes: use a {ndim_tooltip} GeomSpec or a tuple with (tris_coords, tris_indices)"
        self.vert_in_coords(name=pos_name, tooltip=pos_tooltip)

        global _shaders
        _shaders[self.name] = self

    @property
    def ndim(self) -> int:
        if self._ndim == 0:
            return 3
        return self._ndim

    def is_ndim_supported(self, ndim: int) -> bool:
        if self._ndim == 0:
            return True
        return self.ndim == ndim

    def is_ndim_agnostic(self) -> bool:
        return self._ndim == 0

    @property
    def is_compiled(self) -> bool:
        return self._shader is not None

    def define(self, name: str, value: str) -> 'ShaderBuilder':
        self._info.define(name, value)
        return self

    def _vertex_in(self, gpu_type: GPU_TYPES, name: str, *, add_to_vertex_out: bool = True, tooltip: Optional[str] = None) -> 'ShaderBuilder':
        """ If add_to_vertex_out is used, the name for the vertex-out/frament-in will be 'v_{name}'. """
        if add_to_vertex_out:
            self.vertex_out_flat(gpu_type, f"v_{name}")
        self._vert_in_attributes.append(VertexInAttribute(name, gpu_type, tooltip=tooltip))
        self._info.vertex_in(self._vert_in_count, gpu_type, name)
        self._vert_in_count += 1
        return self

    def vert_in_coords(self, name: str = "pos", *, add_to_vertex_out: bool = True, tooltip: Optional[str] = None) -> 'ShaderBuilder':
        """ If add_to_vertex_out is used, the name for the vertex-out/frament-in will be 'v_{name}'. """
        return self._vertex_in(f"VEC{self.ndim}", name, add_to_vertex_out=add_to_vertex_out, tooltip=tooltip)

    def vert_in_color_rgb(self, name: str = "color", *, add_to_vertex_out: bool = True, tooltip: Optional[str] = None) -> 'ShaderBuilder':
        """ If add_to_vertex_out is used, the name for the vertex-out/frament-in will be 'v_{name}'. """
        return self._vertex_in("VEC3", name, add_to_vertex_out=add_to_vertex_out, tooltip=tooltip)

    def vert_in_color_rgba(self, name: str = "color", *, add_to_vertex_out: bool = True, tooltip: Optional[str] = None) -> 'ShaderBuilder':
        """ If add_to_vertex_out is used, the name for the vertex-out/frament-in will be 'v_{name}'. """
        return self._vertex_in("VEC4", name, add_to_vertex_out=add_to_vertex_out, tooltip=tooltip)

    def vert_in_tex_coords(self, name: str = "tex_coords", *, add_to_vertex_out: bool = True, tooltip: Optional[str] = None) -> 'ShaderBuilder':
        """ If add_to_vertex_out is used, the name for the vertex-out/frament-in will be 'v_{name}'. """
        return self._vertex_in("VEC2", name, add_to_vertex_out=add_to_vertex_out, tooltip=tooltip)

    def vert_in_uv(self, name: str = "uv", *, add_to_vertex_out: bool = True, tooltip: Optional[str] = None) -> 'ShaderBuilder':
        """ If add_to_vertex_out is used, the name for the vertex-out/frament-in will be 'v_{name}'. """
        return self._vertex_in("VEC2", name, add_to_vertex_out=add_to_vertex_out, tooltip=tooltip)

    def vert_in_state(self, name: str = "enabled", *, add_to_vertex_out: bool = True, tooltip: Optional[str] = None) -> 'ShaderBuilder':
        """ If add_to_vertex_out is used, the name for the vertex-out/frament-in will be 'v_{name}'. """
        return self._vertex_in("BOOL", name, add_to_vertex_out=add_to_vertex_out, tooltip=tooltip)

    def _vert_out(self, interface_type: str, gpu_type: GPU_TYPES, name: str, *, interface_name: str = "vert_out") -> 'ShaderBuilder':
        if self._varyings_iface is None:
            self._varyings_iface = GPUStageInterfaceInfo(interface_name)
        getattr(self._varyings_iface, interface_type)(gpu_type, name)
        self._vert_out_count += 1
        return self

    def vertex_out_flat(self, gpu_type: GPU_TYPES, name: str) -> 'ShaderBuilder':
        return self._vert_out('flat', gpu_type, name)

    def vertex_out_smooth(self, gpu_type: GPU_TYPES, name: str) -> 'ShaderBuilder':
        return self._vert_out('smooth', gpu_type, name)
    
    def vertex_out_no_perspective(self, gpu_type: GPU_TYPES, name: str) -> 'ShaderBuilder':
        return self._vert_out('no_perspective', gpu_type, name)

    def _fragment_out(self, gpu_type: GPU_TYPES, name: str) -> 'ShaderBuilder':
        """ A fragment output corresponding to a framebuffer target slot. """
        self._info.fragment_out(self._fragment_out_count, gpu_type, name)
        self._fragment_out_count += 1
        return self

    def fragment_out(self, gpu_type: GPU_TYPES, name: str) -> 'ShaderBuilder':
        return self._fragment_out(gpu_type, name)

    def vertex_source(self, source: str) -> 'ShaderBuilder':
        self._info.vertex_source(source)
        return self

    def fragment_source(self, source: str) -> 'ShaderBuilder':
        self._info.fragment_source(source)
        return self

    def uniform(
        self,
        name: str,
        type: str,
        *,
        default: Any = None,
        internal: bool = False,
        getter: Optional[UniformGetter] = None,
        tooltip: Optional[str] = None
    ) -> 'ShaderBuilder':
        self._info.push_constant(type, name, size=0)
        self._uniforms.append(UniformSpec(
            name=name, type=type, default=default, internal=internal, getter=getter
        ))
        return self

    def uniform_float(self, name: str, *, default: Any = None, internal: bool = False, getter=None, tooltip: Optional[str] = None):
        return self.uniform(name, UniformType.FLOAT, default=default, internal=internal, getter=getter, tooltip=tooltip)

    def uniform_int(self, name: str, *, default: Any = None, internal: bool = False, getter=None, tooltip: Optional[str] = None):
        return self.uniform(name, UniformType.INT, default=default, internal=internal, getter=getter, tooltip=tooltip)

    def uniform_bool(self, name: str, *, default: Any = None, internal: bool = False, getter=None, tooltip: Optional[str] = None):
        return self.uniform(name, UniformType.BOOL, default=default, internal=internal, getter=getter, tooltip=tooltip)

    def uniform_vec2(self, name: str, *, default: Any = None, internal: bool = False, getter=None, tooltip: Optional[str] = None):
        return self.uniform(name, UniformType.VEC2, default=default, internal=internal, getter=getter, tooltip=tooltip)

    def uniform_vec3(self, name: str, *, default: Any = None, internal: bool = False, getter=None, tooltip: Optional[str] = None):
        return self.uniform(name, UniformType.VEC3, default=default, internal=internal, getter=getter, tooltip=tooltip)

    def uniform_vec4(self, name: str, *, default: Any = None, internal: bool = False, getter=None, tooltip: Optional[str] = None):
        return self.uniform(name, UniformType.VEC4, default=default, internal=internal, getter=getter, tooltip=tooltip)

    def uniform_mat4(self, name: str, *, default: Any = None, internal: bool = False, getter=None, tooltip: Optional[str] = None):
        return self.uniform(name, UniformType.MAT4, default=default, internal=internal, getter=getter, tooltip=tooltip)

    def sampler(self, name: str, type: str, *, tooltip: Optional[str] = None):
        self._info.sampler(len(self._samplers), type, name)
        self._samplers.append(SamplerSpec(name, type, tooltip=tooltip))
        return self

    def _build(self):
        if self.use_mvp_matrix:
            self.uniform_mat4('ModelViewProjectionMatrix', internal=True)
        if self._varyings_iface is not None:
            self._info.vertex_out(self._varyings_iface)
        if self.use_fragColor_output: # self._fragment_out_count == 0
            self.fragment_out('VEC4', 'fragColor')
        self._shader = create_from_info(self._info)

    def _draw(self, context: Context, *args, **kwargs):
        if not self.is_compiled:
            # jit compilation
            self._build()
        if self._shader is None:
            raise RuntimeError("Shader is not compiled.")

        attributes = {}
        uniforms = {}
        samplers = {}

        indices: TrisIndices | None = None
        effective_primitive: PRIMITIVE_TYPES = self.primitive
        pos_value: Any = None
        args_start: int = 0

        if self.primitive == "TRIS":
            if len(args) < 2:
                raise TypeError("TRIS draw expects at least (pos, indices)")
            pos_value = args[0]
            indices = args[1]
            effective_primitive = "TRIS"
            args_start = 2
        elif self.primitive == "ALL":
            if len(args) < 1:
                raise TypeError("ALL draw expects at least (pos) or ((pos, indices))")
            first = args[0]
            if isinstance(first, tuple) and len(first) == 2:
                pos_value, indices = first
                effective_primitive = "TRIS"
                args_start = 1
            else:
                pos_value = first
                indices = None
                # Default to LINES when not TRIS; adjust if needed
                effective_primitive = "LINES"
                args_start = 1
        else:
            if len(args) < 1:
                raise TypeError(f"{self.primitive} draw expects at least (pos)")
            pos_value = args[0]
            indices = None
            effective_primitive = self.primitive
            args_start = 1

        # Assign attributes: first attribute is pos, the rest come from subsequent args.
        if self._vert_in_count >= 1:
            attributes[self._vert_in_attributes[0].name] = pos_value
            for i in range(1, self._vert_in_count):
                value = args[args_start + (i - 1)]
                attributes[self._vert_in_attributes[i].name] = value

        shader = self._shader
        
        if cache_idname := kwargs.get("_cache_idname", None):
            trackers_changed = any(t.changed for t in RuntimeDrawGlobals.get().trackers)
            cache_key = (self.uid, cache_idname, effective_primitive) if isinstance(cache_idname, str) and cache_idname else None
        else:
            cache_key = None
        if cache_key is not None and (not trackers_changed) and cache_key in _batch_cache:
            batch = _batch_cache[cache_key]
        else:
            batch = batch_for_shader(
                shader,
                effective_primitive,
                attributes,
                indices=indices if effective_primitive == "TRIS" else None,
            )
            if cache_key is not None:
                _batch_cache[cache_key] = batch

        args_offset = args_start + max(0, self._vert_in_count - 1)

        # Match args with samplers, take into account offset.
        for i in range(len(self._samplers)):
            value = args[i + args_offset]
            if not isinstance(value, GPUTexture):
                raise TypeError(f"Argument {i + args_offset} ({self._samplers[i].name}) expects {GPUTexture} type")
            samplers[self._samplers[i]] = value

        args_offset += len(self._samplers)

        # Match args with positional uniforms, take into account offset.
        for i, uniform in enumerate(self._uniforms._positionals):
            value = args[i + args_offset]
            # if not isinstance(value, self._uniforms[i].type):
            #     raise TypeError(f"Argument {i + args_offset} ({self._uniforms[i].name}) expects {self._uniforms[i].type}")
            uniforms[uniform] = value

        # Match kwargs with keyword uniforms.
        for uniform in self._uniforms._kwargs:
            if uniform.name not in kwargs:
                raise TypeError(f"Keyword argument '{uniform.name}' is not a valid uniform")
            value = kwargs[uniform.name]
            # if not isinstance(value, uniform.type):
            #     raise TypeError(f"Keyword argument '{uniform.name}' expects {uniform.type}")
            uniforms[uniform] = value if uniform.getter is None else uniform.getter(context, value)

        # Add internal uniforms.
        for uniform in self._uniforms._internals:
            if uniform.name in {'ModelViewProjectionMatrix'}:
                # Super internal ones that Blender feeds automatically!
                continue
            if uniform.getter is None and uniform.default is None:
                raise ValueError(f"Internal uniform '{uniform.name}' must have a default value or a valid getter function")
            uniforms[uniform] = uniform.default if uniform.getter is None else uniform.getter(context, uniform.default)

        # Apply samplers.
        for sampler, gpu_texture in samplers.items():
            _apply_uniform(shader, sampler.name, UniformType.SAMPLER, gpu_texture)

        # Apply remaining uniforms.
        for uniform, value in uniforms.items():
            _apply_uniform(shader, uniform.name, uniform.type, value)

        batch.draw(shader)


def _apply_uniform(shader: GPUShader, name: str, uniform_type: str, value: Any) -> None:
    if uniform_type in {
        UniformType.INT,
        UniformType.UINT,
        UniformType.UVEC2,
        UniformType.UVEC3,
        UniformType.UVEC4,
        UniformType.IVEC2,
        UniformType.IVEC3,
        UniformType.IVEC4,
    }:
        shader.uniform_int(name, value)
    elif uniform_type in {
        UniformType.FLOAT,
        UniformType.VEC2,
        UniformType.VEC3,
        UniformType.VEC4,
        UniformType.MAT3,
        UniformType.MAT4,
    }:
        shader.uniform_float(name, value)
    elif uniform_type == UniformType.BOOL:
        shader.uniform_bool(name, value)
    elif uniform_type == UniformType.SAMPLER:
        if not isinstance(value, GPUTexture):
            raise TypeError(f"Uniform '{name}' expects GPUTexture")
        shader.uniform_sampler(name, value)
    else:
        raise ValueError(f"Unsupported uniform type: {uniform_type} ({name})")
