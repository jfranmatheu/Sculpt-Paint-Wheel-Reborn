from .ops_options import OperatorOptionsDecorators as OpsOptions
from .polling import Polling as Poll
from .ops_modal_flags import ModalFlagsDecorators as ModalFlags

__all__ = ['Poll', 'OpsOptions']

''' EXAMPLE OF OPERATOR DEFINITION:

@Poll.ACTIVE_OBJECT.MESH
@Poll.MODE.EDIT_MESH
@OpsOptions.REGISTER
@OpsOptions.UNDO
@RegisterOperator.ACTION
class TestOperator:

    def action(self, context) -> None:
        print("Hello world!")
'''

'''
import bpy
from typing import Any, Callable, Dict, Type

class Property:
    class Bool:
        def __init__(self, default: bool = False):
            self.default = default

        def __set_name__(self, owner, name: str):
            if name in owner.__dict__:
                delattr(owner, name)
            owner.__annotations__[name] = bpy.props.BoolProperty(default=self.default)

        def __get__(self, instance: Any, owner: Any) -> bool:
            return getattr(instance, self.__name__)

    class Int:
        def __init__(self, default: int = 0):
            self.default = default

        def __set_name__(self, owner, name: str):
            if name in owner.__dict__:
                delattr(owner, name)
            owner.__annotations__[name] = bpy.props.IntProperty(default=self.default)

        def __get__(self, instance: Any, owner: Any) -> int:
            return getattr(instance, self.__name__)

    class Float:
        def __init__(self, default: float = 0.0):
            self.default = default

        def __set_name__(self, owner, name: str):
            if name in owner.__dict__:
                delattr(owner, name)
            owner.__annotations__[name] = bpy.props.FloatProperty(default=self.default)

        def __get__(self, instance: Any, owner: Any) -> float:
            return getattr(instance, self.__name__)

    class String:
        def __init__(self, default: str = ""):
            self.default = default

        def __set_name__(self, owner, name: str):
            if name in owner.__dict__:
                delattr(owner, name)
            owner.__annotations__[name] = bpy.props.StringProperty(default=self.default)

        def __get__(self, instance: Any, owner: Any) -> str:
            return getattr(instance, self.__name__)

    class Enum:
        def __init__(self, items: list, default: str):
            self.items = items
            self.default = default

        def __set_name__(self, owner, name: str):
            if name in owner.__dict__:
                delattr(owner, name)
            owner.__annotations__[name] = bpy.props.EnumProperty(items=self.items, default=self.default)

        def __get__(self, instance: Any, owner: Any) -> str:
            return getattr(instance, self.__name__)

    class FloatVector:
        def __init__(self, default: tuple = (0.0, 0.0, 0.0)):
            self.default = default

        def __set_name__(self, owner, name: str):
            if name in owner.__dict__:
                delattr(owner, name)
            owner.__annotations__[name] = bpy.props.FloatVectorProperty(default=self.default)

        def __get__(self, instance: Any, owner: Any) -> tuple:
            return getattr(instance, self.__name__)

    class IntVector:
        def __init__(self, default: tuple = (0, 0, 0)):
            self.default = default

        def __set_name__(self, owner, name: str):
            if name in owner.__dict__:
                delattr(owner, name)
            owner.__annotations__[name] = bpy.props.IntVectorProperty(default=self.default)

        def __get__(self, instance: Any, owner: Any) -> tuple:
            return getattr(instance, self.__name__)

    class Collection:
        def __init__(self, type: Type):
            self.type = type

        def __set_name__(self, owner, name: str):
            if name in owner.__dict__:
                delattr(owner, name)
            owner.__annotations__[name] = bpy.props.CollectionProperty(type=self.type)

        def __get__(self, instance: Any, owner: Any) -> list:
            return getattr(instance, self.__name__)

    class Pointer:
        def __init__(self, type: Type):
            self.type = type

        def __set_name__(self, owner, name: str):
            if name in owner.__dict__:
                delattr(owner, name)
            owner.__annotations__[name] = bpy.props.PointerProperty(type=self.type)

        def __get__(self, instance: Any, owner: Any) -> Any:
            return getattr(instance, self.__name__)

def RegisterOperator(cls: Type) -> Type:
    """Decorator to register a Blender operator class."""
    bpy.utils.register_class(cls)
    return cls

@RegisterOperator
class MyOperator(bpy.types.Operator):
    bl_idname = "object.my_operator"
    bl_label = "My Operator"
    bl_options = {'REGISTER', 'UNDO'}

    my_bool = Property.Bool(default=True)
    my_int = Property.Int(default=10)
    my_float = Property.Float(default=1.0)
    my_string = Property.String(default="Hello")
    my_enum = Property.Enum(items=[("OPT_A", "Option A", ""), ("OPT_B", "Option B", "")], default="OPT_A")
    my_float_vector = Property.FloatVector(default=(1.0, 2.0, 3.0))
    my_int_vector = Property.IntVector(default=(1, 2, 3))
    my_collection = Property.Collection(type=bpy.types.PropertyGroup)
    my_pointer = Property.Pointer(type=bpy.types.PropertyGroup)

    def execute(self, context):
        bool_value = self.my_bool
        int_value = self.my_int
        float_value = self.my_float.is_integer()
        string_value = self.my_string.capitalize()
        enum_value = self.my_enum.endswith('.')

        self.report({'INFO'}, f"Bool: {bool_value}, Int: {int_value}, Float: {float_value}, String: {string_value}, Enum: {enum_value}")
        return {'FINISHED'}
'''

'''
import bpy
from typing import Any, TypeVar, Generic, Type, Optional, get_type_hints

T = TypeVar('T')

class PropertyCollection:
    """Container for accessing property descriptors through instance."""
    def __init__(self, instance):
        self._instance = instance

    def __getattr__(self, name):
        return getattr(type(self._instance), name)

class BlenderPropertyDescriptor(Generic[T]):
    """
    A property descriptor that creates a bpy.props property on the owner class
    while providing better typing support.
    """
    def __init__(
        self,
        prop_type: Any,
        name: str = "",
        description: str = "",
        default: Optional[T] = None,
        **kwargs
    ):
        self.prop_type = prop_type
        self.name = name
        self.description = description
        self.default = default
        self.kwargs = kwargs
        self._prop_name = None

    def __set_name__(self, owner, name):
        """Called when the descriptor is assigned to the owner class"""
        self._prop_name = name
        # Create the actual bpy.props annotation
        owner.__annotations__[name] = self.prop_type(
            name=self.name or name,
            description=self.description,
            default=self.default,
            **self.kwargs
        )

    def __get__(self, instance, owner):
        if instance is None:
            return self
        # Direct access to the Blender property through instance
        return getattr(instance, self._prop_name)

    def draw_in_layout(self, layout: 'bpy.types.UILayout', prop_owner: Any):
        """Draw the property in a layout"""
        layout.prop(prop_owner, self._prop_name)

class BoolProperty(BlenderPropertyDescriptor[bool]):
    def __init__(self, **kwargs):
        super().__init__(bpy.props.BoolProperty, **kwargs)

class FloatProperty(BlenderPropertyDescriptor[float]):
    def __init__(self, **kwargs):
        super().__init__(bpy.props.FloatProperty, **kwargs)

class StringProperty(BlenderPropertyDescriptor[str]):
    def __init__(self, **kwargs):
        super().__init__(bpy.props.StringProperty, **kwargs)

# Example usage:
class ExampleOperator(bpy.types.Operator):
    """Example operator using the new property system"""
    bl_idname = "example.operator"
    bl_label = "Example Operator"
    bl_options = {'REGISTER', 'UNDO'}

    # Define properties using the new descriptors
    use_something: bool = BoolProperty(
        name="Use Something",
        description="Enable something",
        default=False
    )

    value: float = FloatProperty(
        name="Value",
        description="Some value",
        default=1.0,
        min=0.0,
        max=10.0
    )

    @property
    def props(self):
        """Access to property descriptors"""
        return PropertyCollection(self)

    def draw(self, context):
        layout = self.layout
        # Access descriptors through self.props
        self.props.use_something.draw_in_layout(layout, self)
        self.props.value.draw_in_layout(layout, self)

    def execute(self, context):
        # Access properties directly
        if self.use_something:
            print(f"Value is: {self.value}")
        return {'FINISHED'}


bpy.utils.register_class(ExampleOperator)
'''

'''
import bpy
from typing import Any, TypeVar, Generic, Type, Optional, get_type_hints, Dict, cast

T = TypeVar('T')

class PropertyCollection:
    """
    Dynamic container for accessing property descriptors through instance.
    Uses class introspection to discover properties.
    """
    def __init__(self, instance: 'BlenderOperator'):
        self._instance = instance
        # Cache descriptor references
        self._descriptors: Dict[str, BlenderPropertyDescriptor] = {
            name: prop for name, prop in type(instance).__dict__.items()
            if isinstance(prop, BlenderPropertyDescriptor)
        }

    def __getattr__(self, name: str) -> 'BlenderPropertyDescriptor':
        if name in self._descriptors:
            return self._descriptors[name]
        raise AttributeError(f"Property '{name}' not found")

class BlenderPropertyDescriptor(Generic[T]):
    """
    A property descriptor that creates a bpy.props property on the owner class
    while providing better typing support.
    """
    def __init__(
        self,
        prop_type: Any,
        name: str = "",
        description: str = "",
        default: Optional[T] = None,
        **kwargs
    ):
        self.prop_type = prop_type
        self.name = name
        self.description = description
        self.default = default
        self.kwargs = kwargs
        self._prop_name = None

    def __set_name__(self, owner, name):
        """Called when the descriptor is assigned to the owner class"""
        self._prop_name = name
        # Create the actual bpy.props annotation
        owner.__annotations__[name] = self.prop_type(
            name=self.name or name,
            description=self.description,
            default=self.default,
            **self.kwargs
        )

    def __get__(self, instance, owner) -> T:
        if instance is None:
            return self
        return getattr(instance, self._prop_name)

    def draw_in_layout(self, layout: 'bpy.types.UILayout', prop_owner: Any):
        """Draw the property in a layout"""
        layout.prop(prop_owner, self._prop_name)

class BoolProperty(BlenderPropertyDescriptor[bool]):
    """Boolean property with proper typing"""
    def __init__(self, **kwargs):
        super().__init__(bpy.props.BoolProperty, **kwargs)

    def __get__(self, instance, owner) -> bool:
        return super().__get__(instance, owner)

class FloatProperty(BlenderPropertyDescriptor[float]):
    """Float property with proper typing"""
    def __init__(self, **kwargs):
        super().__init__(bpy.props.FloatProperty, **kwargs)

    def __get__(self, instance, owner) -> float:
        return super().__get__(instance, owner)

class StringProperty(BlenderPropertyDescriptor[str]):
    """String property with proper typing"""
    def __init__(self, **kwargs):
        super().__init__(bpy.props.StringProperty, **kwargs)

    def __get__(self, instance, owner) -> str:
        return super().__get__(instance, owner)

class BlenderOperator(bpy.types.Operator):
    """Base class for operators with typed properties"""
    @property
    def props(self) -> PropertyCollection:
        """Access to property descriptors with proper typing"""
        return PropertyCollection(self)

# Example usage:
class ExampleOperator(BlenderOperator):
    """Example operator using the new property system"""
    bl_idname = "example.operator"
    bl_label = "Example Operator"

    use_something = BoolProperty(
        name="Use Something",
        description="Enable something",
        default=False
    )

    value = FloatProperty(
        name="Value",
        description="Some value",
        default=1.0,
        min=0.0,
        max=10.0
    )

    def draw(self, context):
        layout = self.layout
        # Properties are discovered automatically
        self.props.use_something.draw_in_layout(layout, self)
        self.props.value.draw_in_layout(layout, self)

    def execute(self, context):
        if self.use_something:
            print(f"Value is: {self.value}")
        return {'FINISHED'}

# Type hint helper for development
def get_operator_props(op: BlenderOperator) -> PropertyCollection:
    """Helper function to get properly typed property collection during development"""
    return op.props
'''

'''
import bpy
from typing import Any, TypeVar, Generic, Type, Optional, get_type_hints, Dict, cast

T = TypeVar('T')

class DrawProperty:
    """Helper class for drawing properties with a cleaner syntax"""
    def __init__(self, instance: 'BlenderOperator'):
        self._instance = instance

    def __getattr__(self, name: str):
        def draw_in_layout(layout: 'bpy.types.UILayout'):
            getattr(type(self._instance), name).draw_in_layout(layout, self._instance)
        return draw_in_layout

class PropertyCollection:
    """
    Dynamic container for accessing property descriptors through instance.
    Uses class introspection to discover properties.
    """
    def __init__(self, instance: 'BlenderOperator'):
        self._instance = instance
        self._descriptors: Dict[str, BlenderPropertyDescriptor] = {
            name: prop for name, prop in type(instance).__dict__.items()
            if isinstance(prop, BlenderPropertyDescriptor)
        }

    def __getattr__(self, name: str) -> 'BlenderPropertyDescriptor':
        if name in self._descriptors:
            return self._descriptors[name]
        raise AttributeError(f"Property '{name}' not found")

class BlenderPropertyDescriptor(Generic[T]):
    """
    A property descriptor that creates a bpy.props property on the owner class
    while providing better typing support.
    """
    def __init__(
        self,
        prop_type: Any,
        name: str = "",
        description: str = "",
        default: Optional[T] = None,
        **kwargs
    ):
        self.prop_type = prop_type
        self.name = name
        self.description = description
        self.default = default
        self.kwargs = kwargs
        self._prop_name = None

    def __set_name__(self, owner, name):
        """Called when the descriptor is assigned to the owner class"""
        self._prop_name = name
        owner.__annotations__[name] = self.prop_type(
            name=self.name or name,
            description=self.description,
            default=self.default,
            **self.kwargs
        )

    def __get__(self, instance, owner) -> T:
        if instance is None:
            return self
        return getattr(instance, self._prop_name)

    def draw_in_layout(self, layout: 'bpy.types.UILayout', prop_owner: Any):
        """Draw the property in a layout"""
        layout.prop(prop_owner, self._prop_name)

class BoolProperty(BlenderPropertyDescriptor[bool]):
    """Boolean property with proper typing"""
    def __init__(self, **kwargs):
        super().__init__(bpy.props.BoolProperty, **kwargs)

    def __get__(self, instance, owner) -> bool:
        return super().__get__(instance, owner)

class FloatProperty(BlenderPropertyDescriptor[float]):
    """Float property with proper typing"""
    def __init__(self, **kwargs):
        super().__init__(bpy.props.FloatProperty, **kwargs)

    def __get__(self, instance, owner) -> float:
        return super().__get__(instance, owner)

class StringProperty(BlenderPropertyDescriptor[str]):
    """String property with proper typing"""
    def __init__(self, **kwargs):
        super().__init__(bpy.props.StringProperty, **kwargs)

    def __get__(self, instance, owner) -> str:
        return super().__get__(instance, owner)

class BlenderOperator(bpy.types.Operator):
    """Base class for operators with typed properties"""
    @property
    def props(self) -> PropertyCollection:
        """Access to property descriptors with proper typing"""
        return PropertyCollection(self)

    @property
    def draw_prop(self) -> DrawProperty:
        """Access to property drawing with clean syntax"""
        return DrawProperty(self)

# Example usage:
class ExampleOperator(BlenderOperator):
    """Example operator using the new property system"""
    bl_idname = "example.operator"
    bl_label = "Example Operator"
    bl_options = {'REGISTER', 'UNDO'}

    use_something = BoolProperty(
        name="Use Something",
        description="Enable something",
        default=False
    )

    value = FloatProperty(
        name="Value",
        description="Some value",
        default=1.0,
        min=0.0,
        max=10.0
    )

    def draw(self, context):
        layout = self.layout
        layout.label(text="Hi")
        self.draw_prop.use_something(layout)
        self.draw_prop.value(layout)

        layout.operator_prop: DrawProperty = self.draw_prop
        
        layout.operator_prop.value(layout)

    def draw_ui(self, context, layout):
        layout = self.layout
        layout.label(text="Hi")
        self.draw_prop.use_something(layout)
        self.draw_prop.value(layout)

    def execute(self, context):
        if self.use_something:
            print(f"Value is: {self.value}")
        return {'FINISHED'}

# Type hint helper for development
def get_operator_props(op: BlenderOperator) -> PropertyCollection:
    """Helper function to get properly typed property collection"""
    return op.props


bpy.utils.register_class(ExampleOperator)
'''

'''
import bpy
from typing import Any, TypeVar, Generic, Type, Optional, get_type_hints, Dict, cast, Callable

T = TypeVar('T')

class LayoutPropertyDrawer:
    """Enhanced property drawer attached to layout"""
    def __init__(self, layout: 'bpy.types.UILayout', operator: 'BlenderOperator'):
        self._layout = layout
        self._operator = operator

    def __getattr__(self, name: str):
        def draw_property(**kwargs):
            prop = getattr(type(self._operator), name)
            prop.draw_in_layout(self._layout, self._operator, **kwargs)
        return draw_property

class EnhancedLayout:
    """Layout wrapper that adds operator_prop functionality"""
    def __init__(self, layout: 'bpy.types.UILayout', operator: 'BlenderOperator'):
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

class DrawProperty:
    """Helper class for drawing properties with a cleaner syntax"""
    def __init__(self, instance: 'BlenderOperator'):
        self._instance = instance

    def __getattr__(self, name: str):
        def draw_in_layout(layout: 'bpy.types.UILayout'):
            getattr(type(self._instance), name).draw_in_layout(layout, self._instance)
        return draw_in_layout

class PropertyCollection:
    """Dynamic container for accessing property descriptors"""
    def __init__(self, instance: 'BlenderOperator'):
        self._instance = instance
        self._descriptors: Dict[str, BlenderPropertyDescriptor] = {
            name: prop for name, prop in type(instance).__dict__.items()
            if isinstance(prop, BlenderPropertyDescriptor)
        }

    def __getattr__(self, name: str) -> 'BlenderPropertyDescriptor':
        if name in self._descriptors:
            return self._descriptors[name]
        raise AttributeError(f"Property '{name}' not found")

class BlenderPropertyDescriptor(Generic[T]):
    """Property descriptor with bpy.props integration"""
    def __init__(
        self,
        prop_type: Any,
        name: str = "",
        description: str = "",
        default: Optional[T] = None,
        **kwargs
    ):
        self.prop_type = prop_type
        self.name = name
        self.description = description
        self.default = default
        self.kwargs = kwargs
        self._prop_name = None

    def __set_name__(self, owner, name):
        self._prop_name = name
        owner.__annotations__[name] = self.prop_type(
            name=self.name or name,
            description=self.description,
            default=self.default,
            **self.kwargs
        )

    def __get__(self, instance, owner) -> T:
        if instance is None:
            return self
        return getattr(instance, self._prop_name)

    def draw_in_layout(self, layout: 'bpy.types.UILayout', prop_owner: Any, **kwargs):
        layout.prop(prop_owner, self._prop_name, **kwargs)

class BoolProperty(BlenderPropertyDescriptor[bool]):
    def __init__(self, **kwargs):
        super().__init__(bpy.props.BoolProperty, **kwargs)
    
    def __get__(self, instance, owner) -> bool:
        return super().__get__(instance, owner)

class FloatProperty(BlenderPropertyDescriptor[float]):
    def __init__(self, **kwargs):
        super().__init__(bpy.props.FloatProperty, **kwargs)
    
    def __get__(self, instance, owner) -> float:
        return super().__get__(instance, owner)

class StringProperty(BlenderPropertyDescriptor[str]):
    def __init__(self, **kwargs):
        super().__init__(bpy.props.StringProperty, **kwargs)
    
    def __get__(self, instance, owner) -> str:
        return super().__get__(instance, owner)

class BlenderOperator(bpy.types.Operator):
    """Base class for operators with typed properties"""
    @property
    def props(self) -> PropertyCollection:
        return PropertyCollection(self)
    
    @property
    def draw_prop(self) -> DrawProperty:
        return DrawProperty(self)
    
    def draw(self, context):
        """Default draw implementation that calls draw_ui with enhanced layout"""
        layout = EnhancedLayout(self.layout, self)
        self.draw_ui(layout)
    
    def draw_ui(self, layout: EnhancedLayout):
        """Override this method to draw the operator's UI"""
        pass

# Example usage:
class ExampleOperator(BlenderOperator):
    bl_idname = "example.operator"
    bl_label = "Example Operator"
    bl_options = {'REGISTER', 'UNDO'}

    use_something: bool = BoolProperty(
        name="Use Something",
        description="Enable something",
        default=False
    )
    
    value: float = FloatProperty(
        name="Value",
        description="Some value",
        default=1.0,
        min=0.0,
        max=10.0
    )

    def draw_ui(self, layout: EnhancedLayout):
        # New super clean drawing syntax
        layout.operator_prop.use_something(text="Enable Feature")
        
        # Create a new column with enhanced layout
        col = layout.column()
        col.operator_prop.value()
        
        # Create a box with enhanced layout
        box = layout.box()
        box.operator_prop.use_something()

    def execute(self, context):
        if self.use_something:
            print(f"Value is: {self.value}")
        return {'FINISHED'}

bpy.utils.register_class(ExampleOperator)
'''

'''
import bpy
from typing import Any, TypeVar, Generic, Type, Optional, Dict, Tuple

T = TypeVar('T')

class PropertyCollection:
    """Dynamic container for accessing property descriptors"""
    def __init__(self, instance: 'BlenderOperator'):
        self._instance = instance
        self._descriptors: Dict[str, BlenderPropertyDescriptor] = {
            name: prop for name, prop in type(instance).__dict__.items()
            if isinstance(prop, BlenderPropertyDescriptor)
        }

    def __getattr__(self, name: str) -> Tuple[Any, str]:
        if name in self._descriptors:
            descriptor = self._descriptors[name]
            # Return a tuple of (operator_instance, property_name)
            return (self._instance, descriptor._prop_name)
        raise AttributeError(f"Property '{name}' not found")

class BlenderPropertyDescriptor(Generic[T]):
    """Property descriptor with bpy.props integration"""
    def __init__(
        self,
        prop_type: Any,
        name: str = "",
        description: str = "",
        default: Optional[T] = None,
        **kwargs
    ):
        self.prop_type = prop_type
        self.name = name
        self.description = description
        self.default = default
        self.kwargs = kwargs
        self._prop_name = None

    def __set_name__(self, owner, name):
        self._prop_name = name
        owner.__annotations__[name] = self.prop_type(
            name=self.name or name,
            description=self.description,
            default=self.default,
            **self.kwargs
        )

    def __get__(self, instance, owner) -> T:
        if instance is None:
            return self
        return getattr(instance, self._prop_name)

class BoolProperty(BlenderPropertyDescriptor[bool]):
    def __init__(self, **kwargs):
        super().__init__(bpy.props.BoolProperty, **kwargs)
    
    def __get__(self, instance, owner) -> bool:
        return super().__get__(instance, owner)

class FloatProperty(BlenderPropertyDescriptor[float]):
    def __init__(self, **kwargs):
        super().__init__(bpy.props.FloatProperty, **kwargs)
    
    def __get__(self, instance, owner) -> float:
        return super().__get__(instance, owner)

class StringProperty(BlenderPropertyDescriptor[str]):
    def __init__(self, **kwargs):
        super().__init__(bpy.props.StringProperty, **kwargs)
    
    def __get__(self, instance, owner) -> str:
        return super().__get__(instance, owner)

class BlenderOperator(bpy.types.Operator):
    """Base class for operators with typed properties"""
    @property
    def props(self) -> PropertyCollection:
        return PropertyCollection(self)

# Example usage:
class ExampleOperator(BlenderOperator):
    bl_idname = "example.operator"
    bl_label = "Example Operator"
    bl_options = {'REGISTER', 'UNDO'}

    use_something: bool = BoolProperty(
        name="Use Something",
        description="Enable something",
        default=False
    )
    
    value: float = FloatProperty(
        name="Value",
        description="Some value",
        default=1.0,
        min=0.0,
        max=10.0
    )

    def draw(self, context):
        layout = self.layout
        
        # Clean property drawing syntax using tuple unpacking
        layout.prop(*self.props.use_something)
        layout.prop(*self.props.value, text="Custom Value Label")
        
        # Works with all layout types
        box = layout.box()
        col = box.column(align=True)
        col.prop(*self.props.use_something, text="Alternative Label")
        col.prop(*self.props.value)

    def execute(self, context):
        if self.use_something:
            print(f"Value is: {self.value}")
        return {'FINISHED'}

bpy.utils.register_class(ExampleOperator)
'''