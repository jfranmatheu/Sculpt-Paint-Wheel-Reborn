from bpy.types import Context
import inspect
from functools import wraps
from typing import Any, List, Optional

try:
    import bpy  # fallback context
except Exception:  # pragma: no cover
    bpy = None


class RuntimeDrawGlobals:
    _instance = None
    context: Context = None
    trackers: List['ContextTracker'] = []

    @classmethod
    def get(cls) -> 'RuntimeDrawGlobals':
        if cls._instance is None:
            cls._instance = RuntimeDrawGlobals()
        return cls._instance

    @classmethod
    def _resolve_context(cls) -> Context:
        runtime = cls.get()
        if runtime.context is not None:
            return runtime.context
        if bpy is not None:
            return bpy.context
        raise RuntimeError("No available Blender context")

    @classmethod
    def wrap_context(cls, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            runtime = cls.get()
            context = None

            try:
                bound = inspect.signature(func).bind_partial(*args, **kwargs)
            except (TypeError, ValueError):
                bound = None

            if bound is not None:
                for value in bound.arguments.values():
                    if isinstance(value, Context):
                        context = value
                        break
            else:
                for value in kwargs.values():
                    if isinstance(value, Context):
                        context = value
                        break
                if context is None:
                    for value in args:
                        if isinstance(value, Context):
                            context = value
                            break

            if context is not None:
                runtime.context = context

            try:
                return func(*args, **kwargs)
            finally:
                runtime.context = None

        return wrapper


class ContextTracker:
    def __init__(self, data_path: str):
        self.data_path = data_path
        self._last_value: Any = _UNSET
        self._current_value: Any = _UNSET
        self.changed: bool = False

    def _resolve(self) -> Any:
        ctx = RuntimeDrawGlobals._resolve_context()
        try:
            return ctx.path_resolve(self.data_path, coerce=True)
        except Exception:
            return _UNSET

    def __enter__(self) -> 'ContextTracker':
        self._current_value = self._resolve()
        self.changed = (self._last_value is _UNSET) or (self._current_value != self._last_value)
        RuntimeDrawGlobals.get().trackers.append(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            runtime = RuntimeDrawGlobals.get()
            try:
                runtime.trackers.remove(self)
            except ValueError:
                pass
            self._last_value = self._current_value
        finally:
            self._current_value = _UNSET
            self.changed = False


def context_tracker(data_path: str) -> ContextTracker:
    return ContextTracker(data_path)


def track_context(data_path: str):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            tracker = ContextTracker(data_path)
            with tracker:
                return func(*args, **kwargs)
        return wrapper
    return decorator


class _Unset:
    pass

_UNSET = _Unset()
