from functools import wraps
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Tuple
import sys


@dataclass
class _WrappedFunction:
    module_name: str
    func_name: str
    original: Callable
    pre_hooks: List[Callable] = field(default_factory=list)
    post_hooks: List[Callable] = field(default_factory=list)
    patched_locations: List[Tuple[object, str, Callable]] = field(default_factory=list)
    wrapper: Callable | None = None

    def apply(self):
        if self.wrapper is not None:
            return

        @wraps(self.original)
        def wrapper(*args, **kwargs):
            for pre in list(self.pre_hooks):
                pre(*args, **kwargs)
            res = self.original(*args, **kwargs)
            if res is False:
                return False
            for post in list(self.post_hooks):
                post(*args, **kwargs)
            return res

        self.wrapper = wrapper

        modules = list(sys.modules.values())
        patched: list[tuple[object, str, Callable]] = []
        for mod in modules:
            if mod is None:
                continue
            try:
                current = getattr(mod, self.func_name)
            except Exception:
                continue
            if current is self.original:
                patched.append((mod, self.func_name, current))
                setattr(mod, self.func_name, wrapper)

        module_original = sys.modules.get(self.module_name, None)
        if module_original is not None:
            try:
                current = getattr(module_original, self.func_name)
            except Exception:
                current = None
            if current is not wrapper:
                patched.append((module_original, self.func_name, current))
                setattr(module_original, self.func_name, wrapper)

        self.patched_locations = patched

    def restore(self):
        if self.wrapper is None:
            return

        for mod, name, prev in self.patched_locations:
            try:
                setattr(mod, name, prev)
            except Exception:
                pass

        self.patched_locations.clear()
        self.wrapper = None


_wrapped: Dict[Tuple[str, str], _WrappedFunction] = {}


def wrap_function(original_func: Callable, pre_func: Callable | None = None, post_func: Callable | None = None) -> Callable:
    module_name = original_func.__module__
    func_name = original_func.__name__

    module_original = sys.modules.get(module_name, None)
    assert module_original, f"Module {module_name} not found for function {func_name}"

    current = getattr(module_original, func_name, None)
    original = current if callable(current) else original_func

    key = (module_name, func_name)
    wf = _wrapped.get(key)
    if wf is None or wf.original is not original:
        if wf is not None:
            wf.restore()
        wf = _WrappedFunction(module_name=module_name, func_name=func_name, original=original)
        _wrapped[key] = wf

    if pre_func is not None:
        wf.pre_hooks.append(pre_func)
    if post_func is not None:
        wf.post_hooks.append(post_func)

    wf.apply()

    def restore():
        existing = _wrapped.get(key)
        if existing is None:
            return
        if pre_func is not None:
            try:
                existing.pre_hooks.remove(pre_func)
            except ValueError:
                pass
        if post_func is not None:
            try:
                existing.post_hooks.remove(post_func)
            except ValueError:
                pass
        if not existing.pre_hooks and not existing.post_hooks:
            existing.restore()
            _wrapped.pop(key, None)

    return restore


def unregister():
    for wf in list(_wrapped.values()):
        wf.restore()
    _wrapped.clear()
