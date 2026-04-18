from __future__ import annotations

from .types import _uniformtype_to_pytype

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Set, Tuple

from . import shader_builder


def generate_draw_py(out_path: str | Path | None = None, *, uids: Iterable[str] | None = None) -> Path:
    print("generate_draw_py:", uids)
    target = Path(out_path) if out_path is not None else (Path(__file__).parent.parent / "draw.py")

    builders = _resolve_builders(uids=uids)
    needs_geom_spec = any(b.primitive in {"TRIS", "ALL"} for b in builders)
    used_typing: Set[str] = {"Any"}
    used_gpu_types: Set[str] = set()
    used_local_types: Set[str] = set()
    used_geom_types: Set[str] = set()

    for b in builders:
        for attr in b._vert_in_attributes:
            _collect_types(_vertex_attr_pytype(attr.type), used_typing, used_gpu_types, used_local_types, used_geom_types)
        for sampler in b._samplers:
            _collect_types("GPUTexture", used_typing, used_gpu_types, used_local_types, used_geom_types)
        for u in b._uniforms._positionals:
            if u.internal:
                continue
            _collect_types(_uniform_pytype(u.type), used_typing, used_gpu_types, used_local_types, used_geom_types)
        for u in b._uniforms._kwargs:
            if u.internal:
                continue
            _collect_types(_uniform_pytype(u.type), used_typing, used_gpu_types, used_local_types, used_geom_types)

    lines: list[str] = []
    lines.append("from __future__ import annotations")
    if used_typing:
        lines.append(f"from typing import {', '.join(sorted(used_typing))}")
    if used_gpu_types:
        lines.append(f"from gpu.types import {', '.join(sorted(used_gpu_types))}")
    if needs_geom_spec:
        lines.append("from .geom_specs import GeomSpec")
    if used_local_types:
        lines.append(f"from .shapes import {', '.join(sorted(used_local_types))}")
    if used_geom_types:
        lines.append(f"from .geom_specs import {', '.join(sorted(used_geom_types))}")
    decorators: Set[str] = set()
    for b in builders:
        if b.primitive == "TRIS":
            decorators.add("draw_shader_tris")
        elif b.primitive == "LINES":
            decorators.add("draw_shader_lines")
        elif b.primitive == "POINTS":
            decorators.add("draw_shader_points")
        elif b.primitive == "ALL":
            decorators.add("draw_shader_auto")
    if decorators:
        lines.append(f"from ._draw.draw_shader import {', '.join(sorted(decorators))}")
    lines.append("")

    for b in builders:
        lines.extend(_emit_draw_fn(b))
        lines.append("")

    target.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return target


def _resolve_builders(*, uids: Iterable[str] | None) -> Tuple[shader_builder.ShaderBuilder, ...]:
    shaders = shader_builder._shaders
    if uids is None:
        builders = tuple(shaders.values())
    else:
        resolved: list[shader_builder.ShaderBuilder] = []
        for uid in uids:
            b = shaders.get(uid)
            if b is None:
                by_uid = next((x for x in shaders.values() if getattr(x, "uid", None) == uid), None)
                if by_uid is None:
                    raise KeyError(f"Unknown ShaderBuilder id: {uid}")
                b = by_uid
            resolved.append(b)
        builders = tuple(resolved)

    builders = tuple(sorted(builders, key=lambda x: (str(x.name), str(x.uid))))
    return builders


def _emit_draw_fn(builder: shader_builder.ShaderBuilder) -> list[str]:
    params: list[str] = []
    doc: list[str] = []

    if builder.tooltip:
        doc.append(f"    ''' {builder.tooltip}")
    doc_params = []

    for i, attr in enumerate(builder._vert_in_attributes):
        name = attr.name
        if i == 0:
            # Use naming convention for first parameter.
            match builder.primitive:
                case 'TRIS':
                    name = "geom_spec"
                case 'LINES':
                    name = "lines_coords"
                case 'POINTS':
                    name = "points_coords"
                case 'ALL':
                    name = "primitives_coords"
        if attr.tooltip:
            doc_params.append(f"    - {name}: {attr.tooltip}")
        if i == 0 and builder.primitive in {"TRIS", "ALL"}:
            # Base coord type may be dimension-agnostic when builder supports 2D and 3D.
            if builder.is_ndim_agnostic():
                base = "Sequence[tuple[float, ...]]"
            else:
                base = _vertex_attr_pytype(attr.type)
            if builder.primitive == 'ALL':
                union = f"{base} | GeomSpec"
            else:
                union = f"GeomSpec"
            params.append(_format_param(name, union, default=_MISSING))
        else:
            # For first coord param in LINES/POINTS, allow dimension-agnostic typing when supported.
            if i == 0 and builder.primitive in {"LINES", "POINTS"} and builder.is_ndim_agnostic():
                params.append(_format_param(name, "Sequence[tuple[float, ...]]", default=_MISSING))
            else:
                params.append(_format_param(name, _vertex_attr_pytype(attr.type), default=_MISSING))

    for sampler in builder._samplers:
        if sampler.tooltip:
            doc_params.append(f"    - {sampler.name}: {sampler.tooltip}")
        params.append(_format_param(sampler.name, "GPUTexture", default=_MISSING))

    for u in builder._uniforms._positionals:
        if u.internal:
            continue
        if u.tooltip:
            doc_params.append(f"    - {u.name}: {u.tooltip}")
        params.append(_format_param(u.name, _uniform_pytype(u.type), default=_MISSING))

    kw_params: list[str] = []
    for u in builder._uniforms._kwargs:
        if u.internal:
            continue
        if u.tooltip:
            doc_params.append(f"    - {u.name}: {u.tooltip}")
        kw_params.append(_format_param(u.name, _uniform_pytype(u.type), default=u.default))

    sig = ", ".join(params)
    if kw_params and sig:
        sig = sig + ", *, " + ", ".join(kw_params)
    elif kw_params:
        sig = "*, " + ", ".join(kw_params)
    # Ensure cache id kwarg is present
    if "*" in sig:
        sig = sig + ", _cache_idname: str | None = None"
    elif sig:
        sig = sig + ", *, _cache_idname: str | None = None"
    else:
        sig = "*, _cache_idname: str | None = None"

    if builder.primitive == "TRIS":
        deco = "@draw_shader_tris"
    elif builder.primitive == "LINES":
        deco = "@draw_shader_lines"
    elif builder.primitive == "POINTS":
        deco = "@draw_shader_points"
    elif builder.primitive == "ALL":
        deco = "@draw_shader_auto"
    else:
        deco = "@draw_shader_auto"
    
    if doc_params:
        if builder.tooltip:
            doc.append("")
            doc.append("    Parameters:")
        else:
            doc.append("    ''' Parameters:")
        doc.extend(doc_params)
    doc.append("    '''")
    
    if builder.tooltip or doc_params:
        docstring = "\n".join(doc)
    else:
        docstring = ""

    return [
        deco,
        f"def {builder.name}({sig}) -> None:",
        f"{docstring}",
        "    pass"
    ]


_MISSING = object()


def _format_param(name: str, type_str: str, *, default: Any) -> str:
    if default is _MISSING:
        if type_str:
            return f"{name}: {type_str}"
        return name
    if type_str:
        return f"{name}: {type_str} = {default!r}"
    return f"{name} = {default!r}"


def _uniform_pytype(gpu_type: str) -> str:
    return _uniformtype_to_pytype(gpu_type)


def _vertex_attr_pytype(gpu_type: str) -> str:
    if gpu_type.startswith("VEC"):
        n_str = gpu_type[3:]
        if n_str.isdigit():
            n = int(n_str)
            if n == 2:
                return "Sequence[tuple[float, float]]"
            if n == 3:
                return "Sequence[tuple[float, float, float]]"
            if n == 4:
                return "Sequence[tuple[float, float, float, float]]"
    if gpu_type == "FLOAT":
        return "Sequence[float]"
    if gpu_type in {"INT", "UINT"}:
        return "Sequence[int]"
    if gpu_type == "BOOL":
        return "Sequence[bool]"
    return "Sequence[Any]"


def _collect_types(type_str: str, used_typing: Set[str], used_gpu_types: Set[str], used_local_types: Set[str], used_geom_types: Set[str]) -> None:
    if "Any" in type_str:
        used_typing.add("Any")
    if "Sequence" in type_str:
        used_typing.add("Sequence")
    if "GPUTexture" in type_str:
        used_gpu_types.add("GPUTexture")
    if "GeomSpec" in type_str:
        used_geom_types.add("GeomSpec")



# --------------------
# Codegen Cache.
# --------------------

_CACHE_VERSION = 1


def late_init(
    out_path: str | Path | None = None,
    *,
    uids: Iterable[str] | None = None,
    cache_path: str | Path | None = None,
) -> bool:
    draw_py_path = Path(out_path) if out_path is not None else (Path(__file__).parent.parent / "draw.py")
    shaders_dat_path = (
        Path(cache_path) if cache_path is not None else (Path(__file__).parent / "shaders.dat")
    )

    builders = _resolve_builders(uids=uids)
    state = _state_from_builders(builders)
    fingerprint = _fingerprint_state(state)

    prev = _read_cache(shaders_dat_path)
    if prev is not None and prev.get("version") == _CACHE_VERSION and prev.get("fingerprint") == fingerprint:
        if draw_py_path.exists():
            print(f"draw.py and shaders.dat are up-to-date at {draw_py_path} and {shaders_dat_path}")
            return False

    generate_draw_py(draw_py_path, uids=uids)
    _write_cache(shaders_dat_path, {"version": _CACHE_VERSION, "fingerprint": fingerprint, "state": state})
    print(f"Generated draw.py and shaders.dat at {draw_py_path} and {shaders_dat_path}")
    return True

def late_init():
    # the original init does not work... because the cache logic is not ok. so let's fallback to generate it always.
    generate_draw_py()


def _fingerprint_state(state: Dict[str, Any]) -> str:
    payload = json.dumps(state, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _state_from_builders(builders: Tuple[shader_builder.ShaderBuilder, ...]) -> Dict[str, Any]:
    return {"builders": [_builder_state(b) for b in builders]}


def _builder_state(builder: shader_builder.ShaderBuilder) -> Dict[str, Any]:
    return {
        "uid": builder.uid,
        "name": builder.name,
        "primitive": builder.primitive,
        "ndim": builder.ndim,
        "use_mvp_matrix": getattr(builder, "use_mvp_matrix", None),
        "use_fragColor_output": getattr(builder, "use_fragColor_output", None),
        "vert_in": [(a.name, a.type) for a in builder._vert_in_attributes],
        "samplers": [(s.name, s.type) for s in builder._samplers],
        "uniforms": {
            "positionals": [_uniform_state(u) for u in builder._uniforms._positionals],
            "kwargs": [_uniform_state(u) for u in builder._uniforms._kwargs],
            "internals": [_uniform_state(u) for u in builder._uniforms._internals],
        },
    }


def _uniform_state(uniform: Any) -> Dict[str, Any]:
    default_value = getattr(uniform, "default", None)
    return {
        "name": getattr(uniform, "name", None),
        "type": getattr(uniform, "type", None),
        "internal": bool(getattr(uniform, "internal", False)),
        "has_getter": getattr(uniform, "getter", None) is not None,
        "default": _json_safe(default_value),
    }


def _json_safe(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except TypeError:
        return repr(value)


def _read_cache(path: Path) -> Dict[str, Any] | None:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        v = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(v, dict):
        return None
    return v


def _write_cache(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
