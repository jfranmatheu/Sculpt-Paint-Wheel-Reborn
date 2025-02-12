from typing import Callable

import bpy
from bpy.types import Menu as BlMenu

from .base import BaseUI, UILayout


__all__ = [
    'Menu',
    'menu_from_function',
]


class Menu(BaseUI):
    '''
    A class for creating a menu.
    '''

    @classmethod
    def tag_register(deco_cls) -> 'Menu':
        return super().tag_register(BlMenu, 'MT')

    @classmethod
    def from_function(cls, label: str, **kwargs) -> 'Menu':
        def decorator(func: Callable) -> 'Menu':
            cls = type(
                func.__name__,
                (Menu, ),
                {
                    **kwargs,
                    'label': label,
                    'draw_ui': func,
                }
            )
            cls.tag_register()
            return cls
        return decorator

    @classmethod
    def popup(cls) -> None:
        bpy.ops.wm.call_menu('INVOKE_DEFAULT', name=cls.bl_idname)

    @classmethod
    def draw_in_layout(cls, layout: UILayout, label: str = None, icon: str = 'NONE'):
        layout.menu(cls.bl_idname, text=label if label is not None else cls.bl_label, icon=icon)


def menu_from_function(label: str) -> Menu:
    def decorator(func: Callable) -> Menu:
        new_cls = Menu.new_from_func(func, label=label)
        return new_cls

    return decorator
