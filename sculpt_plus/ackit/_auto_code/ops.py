import inspect
from pathlib import Path
from typing import List, Type, Dict

from .._globals import GLOBALS
from .._register.register import BTypes
from .._register.props.descriptors import BlenderPropertyDescriptor


def _get_property_type_hint(prop: 'BlenderPropertyDescriptor') -> str:
    """Get the appropriate type hint for a property descriptor"""
    type_map = {
        'BoolProperty': 'bool',
        'BoolVectorProperty': 'Tuple[bool, ...]',
        'FloatProperty': 'float', 
        'FloatVectorProperty': 'Tuple[float, ...]',
        'IntProperty': 'int',
        'IntVectorProperty': 'Tuple[int, ...]',
        'StringProperty': 'str',
        'EnumProperty': 'str',
        'PointerProperty': 'Any',
        'CollectionProperty': 'Any'
    }
    return type_map.get(prop.__class__.__name__, 'Any')

def _get_property_default(prop: 'BlenderPropertyDescriptor') -> str:
    """Get the default value for a property descriptor"""
    if not prop._kwargs.get('default'):
        return 'None'
    return repr(prop._kwargs['default'])

def _format_prop_docstring(name: str, prop: 'BlenderPropertyDescriptor') -> str:
    """Format a property's docstring"""
    type_hint = _get_property_type_hint(prop)
    description = prop._kwargs.get('description', '')
    return f"        - `{name}` ({type_hint}): {description}"

def generate_ops_py(filename: str = 'ops.py'):
    """Generate an {prefix}_ops.py file with typed operator classes"""

    output_path = GLOBALS.ADDON_SOURCE_PATH / f'{filename}.py'

    # Get all operator classes
    operator_classes = BTypes.Operator.get_classes()
    
    # Template for the output file
    output = [
        "from typing import Any, Tuple, Optional, ClassVar",
        "from bpy.types import UILayout, OperatorProperties",
        "import bpy",
        "",
        "# Auto-generated operator classes",
        "# DO NOT EDIT MANUALLY",
        "",
        "class __base_op:",
        "    bl_idname: ClassVar[str]",
        "",
        "    @classmethod",
        "    def draw_in_layout(",
        "        cls,",
        "        layout: UILayout,",
        "        text: Optional[str] = '',",
        "        icon: Optional[str | int] = 'NONE',",
        "        depress: bool = False,",
        "        emboss: bool = False,",
        "        op_props: Optional[dict] = None,",
        "        **draw_kwargs: dict,",
        "    ) -> OperatorProperties:",
        '        """Draw operator in the given layout.',
        "",
        "        Args:",
        "            layout (UILayout): The layout to draw in",
        "            text (Optional[str], optional): Button text. Defaults to an empty string.",
        "            icon (Optional[str | int], optional): Button icon. Defaults to 'NONE'.",
        "            depress (bool, optional): Draw button as pressed. Defaults to False.",
        "            emboss (bool, optional): Draw button embossed. Defaults to False.", 
        "            op_props (Optional[dict], optional): Operator properties. Defaults to None.",
        "            **draw_kwargs: Additional keyword arguments for layout.operator()",
        "",
        "        Returns:",
        "            OperatorProperties: The operator properties",
        '        """',
        "        op = layout.operator(",
        "            cls.bl_idname,",
        "            text=text,",
        "            icon=icon if isinstance(icon, str) else 'NONE',",
        "            icon_value=icon if isinstance(icon, int) else 0,",
        "            depress=depress,",
        "            emboss=emboss,",
        "            **draw_kwargs",
        "        )",
        "        if op_props:",
        "            for key, value in op_props.items():",
        "                setattr(op, key, value)",
        "        return op",
        "",
    ]

    for op_cls in operator_classes:
        # Get properties from class
        properties: Dict[str, 'BlenderPropertyDescriptor'] = {
            name: value for name, value in op_cls.__dict__.items() 
            if isinstance(value, BlenderPropertyDescriptor)
        }

        # Generate class
        class_name = op_cls.original_name  # bl_idname.split('.')[-1].title()
        
        output.extend([
            "",
            f"class {class_name}(__base_op):",
            f'    """',
            f"    {op_cls.bl_label}",
            "",
            f"    {op_cls.bl_description}" if op_cls.bl_description else "",
            '    """',
            f"    bl_idname: ClassVar[str] = '{op_cls.bl_idname}'",
            "",
        ])

        # Generate run method
        output.extend([
            "    @classmethod",
            "    def run(",
            "        cls,",
            "        *,  # Force keyword arguments" if properties else "        # No properties.",
        ])
        
        # Add parameters
        for name, prop in properties.items():
            type_hint = _get_property_type_hint(prop)
            default = _get_property_default(prop)
            output.append(f"        {name}: Optional[{type_hint}] = {default},")
        
        # Add method docstring and body
        output.extend([
            "    ) -> None:",
            f'        """Execute the {op_cls.bl_label} operator.',
            "",
            "        Args:",
        ])
        
        # Add property documentation
        for name, prop in properties.items():
            output.append(_format_prop_docstring(name, prop))
            
        output.extend([
            '        """',
            "        props = {",
        ])
        
        # Add property assignments
        for name in properties:
            output.append(f"            '{name}': {name} if {name} is not None else None,")
        
        output.extend([
            "        }",
            "        # Filter out None values",
            "        props = {k: v for k, v in props.items() if v is not None}",
            f"        bpy.ops.{op_cls.bl_idname}(**props)",
            "",
        ])

        # Generate run_invoke method
        output.extend([
            "    @classmethod",
            "    def run_invoke(",
            "        cls,",
            "        *,  # Force keyword arguments" if properties else "        # No properties",
        ])
        
        # Add parameters
        for name, prop in properties.items():
            type_hint = _get_property_type_hint(prop)
            default = _get_property_default(prop)
            output.append(f"        {name}: Optional[{type_hint}] = {default},")
        
        # Add method docstring and body
        output.extend([
            "    ) -> None:",
            f'        """Execute the {op_cls.bl_label} operator in INVOKE_DEFAULT mode.',
            "",
            "        This mode shows the operator's UI if it has one.",
            "",
            "        Args:",
        ])
        
        # Add property documentation
        for name, prop in properties.items():
            output.append(_format_prop_docstring(name, prop))
            
        output.extend([
            '        """',
            "        props = {",
        ])
        
        # Add property assignments
        for name in properties:
            output.append(f"            '{name}': {name} if {name} is not None else None,")
        
        output.extend([
            "        }",
            "        # Filter out None values",
            "        props = {k: v for k, v in props.items() if v is not None}",
            f"        bpy.ops.{op_cls.bl_idname}('INVOKE_DEFAULT', **props)",
            "",
        ])

    # Write to file
    output_path = Path(output_path)
    output_path.write_text('\n'.join(output))
