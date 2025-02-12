import bpy
from typing import Any, TypeVar, Generic, Type, Optional, Tuple


__all__ = [
    'BoolProperty',
    'BoolVectorProperty',
    'CollectionProperty',
    'EnumProperty',
    'FloatProperty',
    'FloatVectorProperty',
    'IntProperty',
    'IntVectorProperty',
    'PointerProperty',
    'StringProperty',
]


T = TypeVar('T')


class BlenderPropertyDescriptor(Generic[T]):
    """
    A property descriptor that creates a bpy.props property on the owner class
    while providing better typing support.
    """
    def __init__(self, prop_type: Any, **kwargs):
        self._prop_type = prop_type
        self._kwargs = kwargs
        self._prop_name = None

    def __set_name__(self, owner, name):
        """Called when the descriptor is assigned to the owner class"""
        self._prop_name = name
        if not hasattr(owner, '__annotations__'):
            owner.__annotations__ = {}
        # print(f"Registering {name} in {owner.__name__}")  # Debugging line
        owner.__annotations__[name] = self._prop_type(**self._kwargs)

    def __get__(self, instance, owner) -> T:
        if instance is None:
            return self
        return getattr(instance, self._prop_name or self._get_name(instance))

    def _get_name(self, instance) -> str:
        for name, value in type(instance).__dict__.items():
            if value is self:
                return name
        return None

    def initialize(self, owner, name):
        self._prop_name = name
        if not hasattr(owner, '__annotations__'):
            owner.__annotations__ = {}
        owner.__annotations__[name] = self._prop_type(**self._kwargs)

    def draw_in_layout(self, layout: bpy.types.UILayout, prop_owner: Any):
        """Draw the property in a layout"""
        layout.prop(prop_owner, self._prop_name)

    def copy(self):
        """Create a new instance of the descriptor with the same settings"""
        return type(self)(**self._kwargs)


class BoolProperty(BlenderPropertyDescriptor[bool]):
    """Boolean property with proper typing"""
    def __init__(self, name='', description='', translation_context='*', default=False, options={'ANIMATABLE'}, override=set(), tags=set(), subtype='NONE', update=None, get=None, set=None):
        super().__init__(bpy.props.BoolProperty, name=name, description=description, translation_context=translation_context, default=default, options=options, override=override, tags=tags, subtype=subtype, update=update, get=get, set=set)

    def __get__(self, instance: Any, owner: Type) -> bool:
        return super().__get__(instance, owner)

class BoolVectorProperty(BlenderPropertyDescriptor[Tuple[bool, ...]]):
    """Boolean vector property with proper typing"""
    def __init__(self, name='', description='', translation_context='*', default=(False, False, False), options={'ANIMATABLE'}, override=set(), tags=set(), subtype='NONE', size=3, update=None, get=None, set=None):
        super().__init__(bpy.props.BoolVectorProperty, name=name, description=description, translation_context=translation_context, default=default, options=options, override=override, tags=tags, subtype=subtype, size=size, update=update, get=get, set=set)

    def __get__(self, instance: Any, owner: Type) -> Tuple[bool, ...]:
        return super().__get__(instance, owner)

class CollectionProperty(BlenderPropertyDescriptor[Type]):
    """Collection property with proper typing"""
    def __init__(self, type: Type, name='', description='', translation_context='*', options={'ANIMATABLE'}, override=set(), tags=set()):
        super().__init__(bpy.props.CollectionProperty, name=name, description=description, translation_context=translation_context, type=type, options=options, override=override, tags=tags)

    def __get__(self, instance: Any, owner: Type) -> Type:
        return super().__get__(instance, owner)

class EnumProperty(BlenderPropertyDescriptor[str]):
    """Enum property with proper typing"""
    def __init__(self, items=[], name='', description='', translation_context='*', default=None, options={'ANIMATABLE'}, override=set(), tags=set(), update=None, get=None, set=None):
        super().__init__(bpy.props.EnumProperty, name=name, description=description, translation_context=translation_context, items=items, default=default, options=options, override=override, tags=tags, update=update, get=get, set=set)

    def __get__(self, instance: Any, owner: Type) -> str:
        return super().__get__(instance, owner)

class FloatProperty(BlenderPropertyDescriptor[float]):
    """Float property with proper typing"""
    def __init__(self, name='', description='', translation_context='*', default=0.0, min=-3.402823e+38, max=3.402823e+38, soft_min=-3.402823e+38, soft_max=3.402823e+38, step=3, precision=2, options={'ANIMATABLE'}, override=set(), tags=set(), subtype='NONE', unit='NONE', update=None, get=None, set=None):
        super().__init__(bpy.props.FloatProperty, name=name, description=description, translation_context=translation_context, default=default, min=min, max=max, soft_min=soft_min, soft_max=soft_max, step=step, precision=precision, options=options, override=override, tags=tags, subtype=subtype, unit=unit, update=update, get=get, set=set)

    def __get__(self, instance: Any, owner: Type) -> float:
        return super().__get__(instance, owner)

class FloatVectorProperty(BlenderPropertyDescriptor[Tuple[float, ...]]):
    """Float vector property with proper typing"""
    def __init__(self, name='', description='', translation_context='*', default=(0.0, 0.0, 0.0), min=-3.402823e+38, max=3.402823e+38, soft_min=-3.402823e+38, soft_max=3.402823e+38, step=3, precision=2, options={'ANIMATABLE'}, override=set(), tags=set(), subtype='NONE', unit='NONE', size=3, update=None, get=None, set=None):
        super().__init__(bpy.props.FloatVectorProperty, name=name, description=description, translation_context=translation_context, default=default, min=min, max=max, soft_min=soft_min, soft_max=soft_max, step=step, precision=precision, options=options, override=override, tags=tags, subtype=subtype, unit=unit, size=size, update=update, get=get, set=set)

    def __get__(self, instance: Any, owner: Type) -> Tuple[float, ...]:
        return super().__get__(instance, owner)

class IntProperty(BlenderPropertyDescriptor[int]):
    """Integer property with proper typing"""
    def __init__(self, name='', description='', translation_context='*', default=0, min=-2**31, max=2**31 - 1, soft_min=-2**31, soft_max=2**31 - 1, step=1, options={'ANIMATABLE'}, override=set(), tags=set(), update=None, get=None, set=None):
        super().__init__(bpy.props.IntProperty, name=name, description=description, translation_context=translation_context, default=default, min=min, max=max, soft_min=soft_min, soft_max=soft_max, step=step, options=options, override=override, tags=tags, update=update, get=get, set=set)

    def __get__(self, instance: Any, owner: Type) -> int:
        return super().__get__(instance, owner)

class IntVectorProperty(BlenderPropertyDescriptor[Tuple[int, ...]]):
    """Integer vector property with proper typing"""
    def __init__(self, name='', description='', translation_context='*', default=(0, 0, 0), min=-2**31, max=2**31 - 1, soft_min=-2**31, soft_max=2**31 - 1, step=1, options={'ANIMATABLE'}, override=set(), tags=set(), size=3, update=None, get=None, set=None):
        super().__init__(bpy.props.IntVectorProperty, name=name, description=description, translation_context=translation_context, default=default, min=min, max=max, soft_min=soft_min, soft_max=soft_max, step=step, options=options, override=override, tags=tags, size=size, update=update, get=get, set=set)

    def __get__(self, instance: Any, owner: Type) -> Tuple[int, ...]:
        return super().__get__(instance, owner)

class PointerProperty(BlenderPropertyDescriptor[Any]):
    """Pointer property with proper typing"""
    def __init__(self, type: Type, name='', description='', translation_context='*', options={'ANIMATABLE'}, override=set(), tags=set(), poll=None, update=None):
        super().__init__(bpy.props.PointerProperty, name=name, description=description, translation_context=translation_context, type=type, options=options, override=override, tags=tags, poll=poll, update=update)

    def __get__(self, instance: Any, owner: Type) -> Any:
        return super().__get__(instance, owner)

class StringProperty(BlenderPropertyDescriptor[str]):
    """String property with proper typing"""
    def __init__(self, name='', description='', translation_context='*', default='', maxlen=0, options={'ANIMATABLE'}, override=set(), tags=set(), subtype='NONE', update=None, get=None, set=None, search=None, search_options={'SUGGESTION'}):
        super().__init__(bpy.props.StringProperty, name=name, description=description, translation_context=translation_context, default=default, maxlen=maxlen, options=options, override=override, tags=tags, subtype=subtype, update=update, get=get, set=set, search=search, search_options=search_options)

    def __get__(self, instance: Any, owner: Type) -> str:
        return super().__get__(instance, owner)
