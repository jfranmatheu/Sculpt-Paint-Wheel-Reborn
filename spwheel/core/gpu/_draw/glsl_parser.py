from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Dict, List, Optional, Sequence, Tuple

from gpu.types import GPUShaderCreateInfo, GPUStageInterfaceInfo


_RE_BLOCK_COMMENT = re.compile(r"/\*[\s\S]*?\*/")
_RE_LINE_COMMENT = re.compile(r"//.*$")


@dataclass(frozen=True)
class GLSLAttributeSpec:
    name: str
    glsl_type: str
    location: Optional[int] = None


@dataclass(frozen=True)
class GLSLVaryingSpec:
    name: str
    glsl_type: str
    interpolation: str = "smooth"


@dataclass(frozen=True)
class GLSLFragmentOutputSpec:
    name: str
    glsl_type: str
    location: Optional[int] = None


@dataclass(frozen=True)
class GLSLUniformSpec:
    name: str
    glsl_type: str
    binding: Optional[int] = None
    kind: str = "push_constant"


@dataclass(frozen=True)
class GLSLShaderSpec:
    idname: str
    vertex_source: str
    fragment_source: str
    vertex_inputs: Tuple[GLSLAttributeSpec, ...]
    varyings: Tuple[GLSLVaryingSpec, ...]
    fragment_outputs: Tuple[GLSLFragmentOutputSpec, ...]
    uniforms: Tuple[GLSLUniformSpec, ...]

    def to_create_info(self) -> GPUShaderCreateInfo:
        info = GPUShaderCreateInfo()

        _apply_vertex_inputs_from_spec(info, self.vertex_inputs)
        _apply_varyings_from_spec(info, self.idname, self.varyings)
        _apply_fragment_outputs_from_spec(info, self.fragment_outputs)
        _apply_uniforms_from_spec(info, self.uniforms)

        info.vertex_source(self.vertex_source)
        info.fragment_source(self.fragment_source)
        return info


def parse_glsl_spec(idname: str) -> GLSLShaderSpec:
    glsl_path = Path(__file__).parent / "glsl" / f"{idname}.glsl"
    source = glsl_path.read_text(encoding="utf-8")

    vertex_block = _extract_stage_block(source, "GPU_VERTEX_SHADER")
    fragment_block = _extract_stage_block(source, "GPU_FRAGMENT_SHADER")

    vertex_decls = _parse_global_decls(vertex_block)
    fragment_decls = _parse_global_decls(fragment_block)

    vertex_inputs = [d for d in vertex_decls if d.qualifier == "in"]

    vertex_outs = [d for d in vertex_decls if d.qualifier in {"out_smooth", "out_flat", "out_noperspective"}]
    fragment_ins = [d for d in fragment_decls if d.qualifier in {"in_smooth", "in_flat", "in_noperspective"}]
    fragment_outs = [d for d in fragment_decls if d.qualifier == "out"]

    varyings = _merge_varyings(vertex_outs, fragment_ins)
    uniforms = _merge_uniforms(vertex_decls, fragment_decls)

    return GLSLShaderSpec(
        idname=idname,
        vertex_source=_strip_interface_decls(vertex_block),
        fragment_source=_strip_interface_decls(fragment_block),
        vertex_inputs=tuple(
            GLSLAttributeSpec(name=d.name, glsl_type=d.glsl_type, location=d.location) for d in vertex_inputs
        ),
        varyings=tuple(varyings),
        fragment_outputs=tuple(
            GLSLFragmentOutputSpec(name=d.name, glsl_type=d.glsl_type, location=d.location) for d in fragment_outs
        ),
        uniforms=tuple(uniforms),
    )


def parse_glsl(idname: str) -> GPUShaderCreateInfo:
    return parse_glsl_spec(idname).to_create_info()


@dataclass(frozen=True)
class _Decl:
    name: str
    glsl_type: str
    qualifier: Optional[str] = None
    location: Optional[int] = None
    binding: Optional[int] = None


def _extract_stage_block(source: str, stage_macro: str) -> str:
    patterns = [
        rf"(?s)#ifdef\s+{re.escape(stage_macro)}\s*(.*?)\s*#endif",
        rf"(?s)#if\s+defined\s*\(\s*{re.escape(stage_macro)}\s*\)\s*(.*?)\s*#endif",
        rf"(?s)#if\s+defined\s+{re.escape(stage_macro)}\s*(.*?)\s*#endif",
    ]
    for pat in patterns:
        m = re.search(pat, source)
        if m:
            return m.group(1).strip("\n")
    raise ValueError(f"Missing stage block for {stage_macro}")


def _strip_comments(src: str) -> str:
    src = _RE_BLOCK_COMMENT.sub("", src)
    return "\n".join(_RE_LINE_COMMENT.sub("", line) for line in src.splitlines())


def _parse_global_decls(stage_block: str) -> List[_Decl]:
    decls: List[_Decl] = []
    lines = _strip_comments(stage_block).splitlines()
    depth = 0
    for line in lines:
        depth += line.count("{") - line.count("}")
        if depth != 0:
            continue
        line_stripped = line.strip()
        if not line_stripped or ";" not in line_stripped:
            continue
        decls.extend(_parse_decl_line(line_stripped))
    return decls


def _parse_decl_line(line: str) -> List[_Decl]:
    layout, rest = _split_layout(line)
    location = layout.get("location")
    binding = layout.get("binding")

    m = re.match(r"^(uniform)\s+([A-Za-z_]\w*)\s+(.+?)\s*;\s*$", rest)
    if m:
        glsl_type = m.group(2)
        names = _split_names(m.group(3))
        return [
            _Decl(name=n, glsl_type=glsl_type, qualifier="uniform", location=location, binding=binding) for n in names
        ]

    m = re.match(r"^((?:smooth|flat|noperspective)\s+)?(in|out)\s+([A-Za-z_]\w*)\s+(.+?)\s*;\s*$", rest)
    if m:
        interp = (m.group(1) or "").strip() or None
        direction = m.group(2)
        glsl_type = m.group(3)
        names = _split_names(m.group(4))

        if direction == "in":
            qual = f"in_{interp}" if interp else "in"
        else:
            qual = f"out_{interp}" if interp else "out"

        return [
            _Decl(name=n, glsl_type=glsl_type, qualifier=qual, location=location, binding=binding) for n in names
        ]

    return []


def _split_layout(line: str) -> Tuple[Dict[str, int], str]:
    m = re.match(r"^layout\s*\(\s*([^)]+)\s*\)\s*(.*)$", line)
    if not m:
        return {}, line

    inside = m.group(1)
    rest = m.group(2)
    kv: Dict[str, int] = {}
    for part in inside.split(","):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        k = k.strip()
        v = v.strip()
        if not v.isdigit():
            continue
        kv[k] = int(v)
    return kv, rest


def _split_names(names_expr: str) -> List[str]:
    names: List[str] = []
    for part in names_expr.split(","):
        n = part.strip()
        if not n:
            continue
        n = re.sub(r"\[\s*\d*\s*\]$", "", n).strip()
        if not re.match(r"^[A-Za-z_]\w*$", n):
            continue
        names.append(n)
    return names


def _merge_varyings(vertex_outs: Sequence[_Decl], fragment_ins: Sequence[_Decl]) -> List[GLSLVaryingSpec]:
    by_name_vert: Dict[str, _Decl] = {d.name: d for d in vertex_outs}
    by_name_frag: Dict[str, _Decl] = {d.name: d for d in fragment_ins}

    varyings: List[GLSLVaryingSpec] = []
    for name in by_name_vert:
        v = by_name_vert[name]
        f = by_name_frag.get(name)
        if f and f.glsl_type != v.glsl_type:
            raise ValueError(f"Varying '{name}' type mismatch: {v.glsl_type} vs {f.glsl_type}")

        interpolation = "smooth"
        if v.qualifier == "out_flat":
            interpolation = "flat"
        elif v.qualifier == "out_noperspective":
            interpolation = "noperspective"

        varyings.append(GLSLVaryingSpec(name=v.name, glsl_type=v.glsl_type, interpolation=interpolation))
    return varyings


def _merge_uniforms(vertex_decls: Sequence[_Decl], fragment_decls: Sequence[_Decl]) -> List[GLSLUniformSpec]:
    merged: Dict[str, _Decl] = {}
    for d in list(vertex_decls) + list(fragment_decls):
        if d.qualifier != "uniform":
            continue
        prev = merged.get(d.name)
        if prev is None:
            merged[d.name] = d
            continue
        if prev.glsl_type != d.glsl_type:
            raise ValueError(f"Uniform '{d.name}' type mismatch: {prev.glsl_type} vs {d.glsl_type}")
        merged[d.name] = _Decl(
            name=d.name,
            glsl_type=d.glsl_type,
            qualifier="uniform",
            location=prev.location if prev.location is not None else d.location,
            binding=prev.binding if prev.binding is not None else d.binding,
        )

    specs: List[GLSLUniformSpec] = []
    for d in merged.values():
        kind = "sampler" if _glsl_sampler_to_gpu_type(d.glsl_type) is not None else "push_constant"
        specs.append(GLSLUniformSpec(name=d.name, glsl_type=d.glsl_type, binding=d.binding, kind=kind))
    return specs


def _apply_vertex_inputs_from_spec(info: GPUShaderCreateInfo, vertex_inputs: Sequence[GLSLAttributeSpec]) -> None:
    explicit = [d for d in vertex_inputs if d.location is not None]
    implicit = [d for d in vertex_inputs if d.location is None]

    used = {d.location for d in explicit if d.location is not None}
    next_index = 0

    for d in sorted(explicit, key=lambda x: x.location or 0):
        gpu_type = _glsl_to_gpu_type(d.glsl_type)
        if gpu_type is None:
            raise ValueError(f"Unsupported vertex input type: {d.glsl_type} ({d.name})")
        info.vertex_in(int(d.location), gpu_type, d.name)

    for d in implicit:
        while next_index in used:
            next_index += 1
        gpu_type = _glsl_to_gpu_type(d.glsl_type)
        if gpu_type is None:
            raise ValueError(f"Unsupported vertex input type: {d.glsl_type} ({d.name})")
        info.vertex_in(next_index, gpu_type, d.name)
        used.add(next_index)
        next_index += 1


def _apply_varyings_from_spec(info: GPUShaderCreateInfo, idname: str, varyings: Sequence[GLSLVaryingSpec]) -> None:
    if not varyings:
        return

    iface = GPUStageInterfaceInfo(f"{idname}_vert_out")
    for v in varyings:
        gpu_type = _glsl_to_gpu_type(v.glsl_type)
        if gpu_type is None:
            raise ValueError(f"Unsupported varying type: {v.glsl_type} ({v.name})")

        if v.interpolation == "flat" and hasattr(iface, "flat"):
            iface.flat(gpu_type, v.name)
        elif v.interpolation == "noperspective" and hasattr(iface, "no_perspective"):
            getattr(iface, "no_perspective")(gpu_type, v.name)
        else:
            iface.smooth(gpu_type, v.name)

    info.vertex_out(iface)


def _apply_fragment_outputs_from_spec(info: GPUShaderCreateInfo, fragment_outs: Sequence[GLSLFragmentOutputSpec]) -> None:
    explicit = [d for d in fragment_outs if d.location is not None]
    implicit = [d for d in fragment_outs if d.location is None]

    used = {d.location for d in explicit if d.location is not None}
    next_index = 0

    for d in sorted(explicit, key=lambda x: x.location or 0):
        gpu_type = _glsl_to_gpu_type(d.glsl_type)
        if gpu_type is None:
            raise ValueError(f"Unsupported fragment output type: {d.glsl_type} ({d.name})")
        info.fragment_out(int(d.location), gpu_type, d.name)

    for d in implicit:
        while next_index in used:
            next_index += 1
        gpu_type = _glsl_to_gpu_type(d.glsl_type)
        if gpu_type is None:
            raise ValueError(f"Unsupported fragment output type: {d.glsl_type} ({d.name})")
        info.fragment_out(next_index, gpu_type, d.name)
        used.add(next_index)
        next_index += 1


def _apply_uniforms_from_spec(info: GPUShaderCreateInfo, uniforms: Sequence[GLSLUniformSpec]) -> None:
    sampler_slot = 0

    explicit = [u for u in uniforms if u.binding is not None]
    implicit = [u for u in uniforms if u.binding is None]

    for u in sorted(explicit, key=lambda x: x.binding or 0):
        if u.kind == "sampler":
            sampler_type = _glsl_sampler_to_gpu_type(u.glsl_type)
            if sampler_type is None:
                raise ValueError(f"Unsupported sampler type: {u.glsl_type} ({u.name})")
            if hasattr(info, "sampler"):
                info.sampler(int(u.binding), sampler_type, u.name)
                continue
        gpu_type = _glsl_to_gpu_type(u.glsl_type)
        if gpu_type is None:
            raise ValueError(f"Unsupported uniform type: {u.glsl_type} ({u.name})")
        info.push_constant(gpu_type, u.name)

    for u in implicit:
        if u.kind == "sampler":
            sampler_type = _glsl_sampler_to_gpu_type(u.glsl_type)
            if sampler_type is None:
                raise ValueError(f"Unsupported sampler type: {u.glsl_type} ({u.name})")
            if hasattr(info, "sampler"):
                info.sampler(sampler_slot, sampler_type, u.name)
                sampler_slot += 1
                continue
        gpu_type = _glsl_to_gpu_type(u.glsl_type)
        if gpu_type is None:
            raise ValueError(f"Unsupported uniform type: {u.glsl_type} ({u.name})")
        info.push_constant(gpu_type, u.name)


def _glsl_sampler_to_gpu_type(glsl_type: str) -> Optional[str]:
    m = re.match(r"^(u|i)?sampler(1D|2D|3D|Cube|2DArray|CubeArray)$", glsl_type)
    if not m:
        return None
    prefix = m.group(1)
    dim = m.group(2)

    base = "FLOAT"
    if prefix == "i":
        base = "INT"
    elif prefix == "u":
        base = "UINT"

    dim_map = {
        "1D": "1D",
        "2D": "2D",
        "3D": "3D",
        "Cube": "CUBE",
        "2DArray": "2D_ARRAY",
        "CubeArray": "CUBE_ARRAY",
    }
    return f"{base}_{dim_map[dim]}"


def _glsl_to_gpu_type(glsl_type: str) -> Optional[str]:
    table = {
        "float": "FLOAT",
        "int": "INT",
        "uint": "UINT",
        "bool": "BOOL",
        "vec2": "VEC2",
        "vec3": "VEC3",
        "vec4": "VEC4",
        "ivec2": "IVEC2",
        "ivec3": "IVEC3",
        "ivec4": "IVEC4",
        "uvec2": "UVEC2",
        "uvec3": "UVEC3",
        "uvec4": "UVEC4",
        "mat3": "MAT3",
        "mat4": "MAT4",
    }
    return table.get(glsl_type)


def _strip_interface_decls(stage_block: str) -> str:
    lines = stage_block.splitlines()
    out_lines: List[str] = []
    depth = 0
    for raw_line in lines:
        line = _RE_LINE_COMMENT.sub("", raw_line)
        depth += line.count("{") - line.count("}")
        if depth == 0:
            stripped = line.strip()
            if not stripped:
                out_lines.append(raw_line)
                continue
            _, rest = _split_layout(stripped)
            if re.match(r"^(uniform)\s+", rest):
                continue
            if re.match(r"^((?:smooth|flat|noperspective)\s+)?(in|out)\s+", rest):
                continue
        out_lines.append(raw_line)
    return "\n".join(out_lines).strip("\n")
