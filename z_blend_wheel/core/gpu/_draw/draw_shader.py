import inspect
from typing import Any, Callable, Concatenate, Generic, ParamSpec, Tuple, TypeVar, overload, Sequence

from bpy.types import Context

from ..globals import RuntimeDrawGlobals
from ..geom_specs import GeomSpec
from .shader_builder import ShaderBuilder


P = ParamSpec("P")
R = ParamSpec("R")
PosT = TypeVar("PosT")


'''
EXPECTED RESULT WHEN SERIALIZING THE ShaderBuilder creations to Drawing functions ready to be used:

@draw_shader
def {shader_builder.name}({vert_in_attributes}, {samplers}, {uniforms_without_defaults}, *, {uniforms_with_defaults}): pass
'''


def _coords_ndim(coords: Any) -> int | None:
    try:
        it = iter(coords)
        first = next(it)
    except Exception:
        return None
    try:
        return len(first)
    except Exception:
        return None


class _DrawShaderCallableBase(Generic[P]):
    def __init__(self, func: Callable[P, Any]):
        self._func = func
        self.name = func.__name__
        self.__name__ = func.__name__
        self.__doc__ = func.__doc__

    @property
    def shader_builder(self) -> ShaderBuilder:
        from .shader_builder import _shaders
        shader_builder = _shaders.get(self.name)
        if shader_builder is None:
            raise KeyError(f"Unknown shader builder: {self.name}")
        return shader_builder

    def draw(self, context: Context, *args: P.args, **kwargs: P.kwargs) -> None:
        self._validate_args_ndim(args)
        norm = self._normalize_args(args)
        self.shader_builder._draw(context, *norm, **kwargs)

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> None:
        self._validate_args_ndim(args)
        norm = self._normalize_args(args)
        self.shader_builder._draw(RuntimeDrawGlobals.get().context, *norm, **kwargs)
        return None

    def _validate_coords_ndim(self, coords: Any) -> None:
        shader_builder = self.shader_builder
        if shader_builder.ndim == 0:
            return None
        ndim = _coords_ndim(coords)
        if ndim is None:
            return None
        if ndim != shader_builder.ndim:
            raise TypeError("coords ndim must match shader_builder.ndim")
        return None

    def _validate_args_ndim(self, args: Tuple[Any, ...]) -> None:
        shader_builder = self.shader_builder
        if not args:
            return None
        first = args[0]
        if isinstance(first, tuple) and len(first) == 2:
            coords, _indices = first
            self._validate_coords_ndim(coords)
        elif isinstance(first, GeomSpec):
            # GeomSpec overrides ndim relevance for TRIS/ALL; skip strict validation.
            return None
        else:
            self._validate_coords_ndim(first)
        return None

class DrawShaderCallable(_DrawShaderCallableBase[P]):
    def _normalize_args(self, args: Tuple[Any, ...]) -> Tuple[Any, ...]:
        shader_builder = self.shader_builder
        if not args:
            return args
        first = args[0]
        rest = args[1:]
        if shader_builder.primitive in {"TRIS", "ALL"}:
            if isinstance(first, tuple) and len(first) == 2 and type(first[1][0]) == int:
                coords, indices = first
                # Validate indices shape when provided
                if indices is not None:
                    if not isinstance(indices, (list, tuple)) or not indices:
                        raise TypeError("indices must be a non-empty sequence of index triples")
                    first_tri = indices[0]
                    if not isinstance(first_tri, (list, tuple)) or len(first_tri) != 3:
                        raise TypeError("indices must be a sequence of triples (i0, i1, i2)")
                coords = self._adapt_coords_ndim(coords, shader_builder.ndim)
            elif isinstance(first, GeomSpec):
                coords = first.coords()
                indices = first.indices()
                coords = self._adapt_coords_ndim(coords, shader_builder.ndim)
            else:
                coords = first
                indices = None
                if shader_builder.primitive == "TRIS":
                    if isinstance(coords, (list, tuple)):
                        L = len(coords)
                        if L % 3 == 0 and L >= 3:
                            indices = [(i, i + 1, i + 2) for i in range(0, L, 3)]
                        else:
                            raise TypeError("TRIS expects coords in triples or provide indices via tuple[(pos, indices)] or GeomSpec")
                    else:
                        raise TypeError("TRIS expects coords Sequence or GeomSpec")
            # Normalize output tuple according to primitive.
            if shader_builder.primitive == "TRIS":
                return (coords, indices, *rest)
            else:
                # 'ALL' builder: pass tuple if indices detected, else coords
                first_norm = (coords, indices) if indices is not None else coords
                return (first_norm, *rest)
        # Non TRIS/ALL builders: passthrough
        return args

    def _adapt_coords_ndim(self, coords: Sequence[tuple], target_ndim: int) -> Sequence[tuple]:
        try:
            inner_ndim = len(coords[0])
        except Exception:
            return coords
        if target_ndim == 0:
            return coords
        if inner_ndim == target_ndim:
            return coords
        if inner_ndim == 2 and target_ndim == 3:
            return [(x, y, 0.0) for (x, y) in coords]
        if inner_ndim == 3 and target_ndim == 2:
            return [(x, y) for (x, y, _z) in coords]
        return coords


# -----------------------------------------------------------------------------------------
# Decorators for drawing shaders (no builder lookup)

@overload
def draw_shader_tris(func: Callable[P, Any]) -> DrawShaderCallable[P]: ...

def draw_shader_tris(func: Callable[..., Any]) -> Any:
    return DrawShaderCallable(func)


@overload
def draw_shader_lines(func: Callable[P, Any]) -> DrawShaderCallable[P]: ...

def draw_shader_lines(func: Callable[..., Any]) -> Any:
    return DrawShaderCallable(func)


@overload
def draw_shader_points(func: Callable[P, Any]) -> DrawShaderCallable[P]: ...

def draw_shader_points(func: Callable[..., Any]) -> Any:
    return DrawShaderCallable(func)


@overload
def draw_shader_auto(func: Callable[P, Any]) -> DrawShaderCallable[P]: ...

def draw_shader_auto(func: Callable[..., Any]) -> Any:
    return DrawShaderCallable(func)
