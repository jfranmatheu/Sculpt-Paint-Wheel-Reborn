from inspect import getattr_static
from typing import Set, TypeVar


T = TypeVar('T')


def get_subclasses(cls: T) -> Set[T]:
    return set(cls.__subclasses__())


def get_subclasses_recursive(cls: T, only_last=False, exclude_from_module: str = None) -> Set[T]:
    """Get all subclasses of cls, recursively.
        only_last: excluding from the result those that have subclasses (we'll just look into their subclasses)"""
    result = set()
    seen = set()
    stack = [cls]
    while stack:
        base = stack.pop()
        if base in seen:
            continue
        seen.add(base)
        subs = get_subclasses(base)
        for sub in subs:
            stack.append(sub)
            if exclude_from_module is not None and sub.__module__.startswith(exclude_from_module):
                continue
            if not only_last:
                result.add(sub)
            else:
                if len(get_subclasses(sub)) == 0:
                    result.add(sub)
    return result


def is_method_overridden(cls, method_name: str, base_class: type) -> bool:
    cls_method = getattr_static(cls, method_name, object())
    base_method = getattr_static(base_class, method_name, object())
    return cls_method is not base_method
