import bpy
from typing import Dict, Tuple, Any

from .descriptors import BlenderPropertyDescriptor  # used for 'DescriptorProps_Props'


__all__ = [
    'DescriptorProps_DrawUILayout',
    'DescriptorProps_DrawProps',
    'DescriptorProps_Props',
    'DescriptorProps_PropsTuple',
]


# ----------------------------------------------------------------
# # Inside draw_ui(context, layout: EnhancedLayout) method.
# layout.operator_prop.my_prop(text="Something")
# ----------------------------------------------------------------

class LayoutPropertyDrawer:
    """Enhanced property drawer attached to layout"""
    def __init__(self, layout: bpy.types.UILayout, operator: bpy.types.Operator):
        self._layout = layout
        self._operator = operator

    def __getattr__(self, name: str):
        def draw_property(**kwargs):
            prop = getattr(type(self._operator), name)
            prop.draw_in_layout(self._layout, self._operator, **kwargs)
        return draw_property


class EnhancedLayout:
    """Layout wrapper that adds operator_prop functionality"""
    def __init__(self, layout: bpy.types.UILayout, operator: bpy.types.Operator):
        self._layout = layout
        self._operator = operator
        self._property_drawer = None

    @property
    def operator_prop(self) -> LayoutPropertyDrawer:
        if self._property_drawer is None:
            self._property_drawer = LayoutPropertyDrawer(self._layout, self._operator)
        return self._property_drawer

    def column(self, align: bool = False) -> 'EnhancedLayout':
        return EnhancedLayout(self._layout.column(align=align), self._operator)

    def row(self, align: bool = False) -> 'EnhancedLayout':
        return EnhancedLayout(self._layout.row(align=align), self._operator)

    def box(self) -> 'EnhancedLayout':
        return EnhancedLayout(self._layout.box(), self._operator)

    def split(self, factor: float = 0.5, align: bool = False) -> 'EnhancedLayout':
        return EnhancedLayout(self._layout.split(factor=factor, align=align), self._operator)

    def __getattr__(self, name: str):
        # Forward any other layout attributes
        return getattr(self._layout, name)


class DescriptorProps_DrawUILayout:
    """Base class for operators with typed properties"""
    layout: EnhancedLayout

    def draw(self, context):
        """Default draw implementation that calls draw_ui with enhanced layout"""
        layout = EnhancedLayout(self.layout, self)
        self.draw_ui(context, layout)

    def draw_ui(self, context: bpy.types.Context, layout: EnhancedLayout):
        """Override this method to draw the operator's UI"""
        pass


# ----------------------------------------------------------------
# self.draw_prop.my_prop(layout, text="Something")
# ----------------------------------------------------------------

class DrawProperty:
    """Helper class for drawing properties with a cleaner syntax"""
    def __init__(self, instance: 'BlenderOperator'):
        self._instance = instance

    def __getattr__(self, name: str):
        def draw_in_layout(layout: bpy.types.UILayout):
            # Call the draw_in_layout from the descriptor... ( layout.prop(prop_owner, self._prop_name) )
            getattr(type(self._instance), name).draw_in_layout(layout, self._instance)
        return draw_in_layout


class DescriptorProps_DrawProps:
    """Base class for operators with typed properties"""

    @property
    def draw_prop(self) -> DrawProperty:
        return DrawProperty(self)


# ----------------------------------------------------------------
# self.props.my_prop.draw_in_layout(layout, text="Something")
# ----------------------------------------------------------------

class DescriptorPropertyCollection:
    """
    Dynamic container for accessing property descriptors through instance.
    Uses class introspection to discover properties.
    """
    def __init__(self, instance: bpy.types.Operator | bpy.types.PropertyGroup):
        self._instance = instance
        self._descriptors: Dict[str, BlenderPropertyDescriptor] = {
            name: prop for name, prop in type(instance).__dict__.items()
            if isinstance(prop, BlenderPropertyDescriptor)
        }
        print("Available descriptors:", self._descriptors.keys())  # Debugging line

    def __getattr__(self, name: str) -> 'BlenderPropertyDescriptor':
        if name in self._descriptors:
            return self._descriptors[name]
        raise AttributeError(f"Property '{name}' not found")


class DescriptorProps_Props:
    """Base class for operators with typed properties"""

    @property
    def props(self) -> DescriptorPropertyCollection:
        return DescriptorPropertyCollection(self)


# ----------------------------------------------------------------
# layout.prop(*self.props.my_prop, text="Something")
# ----------------------------------------------------------------

class PropertyCollection:
    """Dynamic container for accessing property descriptors"""
    def __init__(self, instance: 'BlenderOperator'):
        self._instance = instance
        self._descriptors: Dict[str, BlenderPropertyDescriptor] = {}

        self._descriptors: Dict[str, BlenderPropertyDescriptor] = {
            name: prop for name, prop in type(instance).__dict__.items()
            if isinstance(prop, BlenderPropertyDescriptor)
        }

        '''
        for base in type(instance).__mro__:
            for name, prop in base.__dict__.items():
                if isinstance(prop, BlenderPropertyDescriptor):
                    self._descriptors[name] = prop
        '''

    def __getattr__(self, name: str) -> Tuple[Any, str]:
        if name in self._descriptors:
            # descriptor = self._descriptors[name]
            return (self._instance, name)
        raise AttributeError(f"Property '{name}' not found")


class DescriptorProps_PropsTuple:
    """Base class for operators with typed properties"""

    @property
    def props(self) -> PropertyCollection:
        return PropertyCollection(self)
