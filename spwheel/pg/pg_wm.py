from bpy.props import FloatVectorProperty
from ..core.bl_types import PropertyGroupRoot


class PG_WM(PropertyGroupRoot.WINDOW_MANAGER):
    """Window Manager Properties"""
    
    sep_color_custom_buttons_set: FloatVectorProperty(
        name="Custom Button Set Separator Color",
        description="Color of the separator line between custom-button sets",
        default=(0.0, 0.8, 1.0),
        subtype="COLOR",
        min=0.0,
        max=1.0,
        size=3,
        options={'READ_ONLY'}
    )

    sep_color_brush_set: FloatVectorProperty(
        name="Brush Set Separator Color",
        description="Color of the separator line between brush-sets",
        default=(1.0, 0.8, 0.0),
        subtype="COLOR",
        min=0.0,
        max=1.0,
        size=3,
        options={'READ_ONLY'}
    )
