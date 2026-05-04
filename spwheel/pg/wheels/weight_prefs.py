from bpy.props import BoolProperty, IntProperty

from ...core.bl_types import PropertyGroup


class WeightWheelPrefs(PropertyGroup):
    show_markers : BoolProperty(default=True, name="Show Markers")
    use_interactable_markers : BoolProperty(default=True, name="Interactable Markers")
    marker_count : IntProperty(default=10, min=3, max=20, name="Marker Count")
    
    set_weight_of_selection_directly : BoolProperty(default=True, name="Direct Selection Weight", description="When changing weight value will directly update the weight of the selection mask")

    use_add_substract_brush : BoolProperty(default=False, name="Add/Substract Brush Toggle", description="Instead of 'Draw' brush will use Add/Substract brushes in the brush tool")
