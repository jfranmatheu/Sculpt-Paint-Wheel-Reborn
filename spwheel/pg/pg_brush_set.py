from bpy.props import BoolProperty, CollectionProperty, EnumProperty, IntProperty, StringProperty, FloatProperty
from bpy.types import Brush, Context, UILayout

from ..utils.ups import has_brush_color_capabilities
from .pg_brush_metadata import BrushMetadata
from ..core.bl_types import PropertyGroup
from ..ui.lists.ul_brush_metadata_list import BrushMetadataList



class BrushSetPreferences(PropertyGroup):

    slot_size: FloatProperty(
        name="Slot Size",
        description="Size of each brush slot",
        default=56.0,
        min=24.0,
        max=92.0,
    )

    slot_padding: FloatProperty(
        name="Slot Padding",
        description="Padding between neighbor brush slots",
        default=11.0,
        min=0.0,
        max=20.0,
    )

    ring_padding: IntProperty(
        name="Ring Padding",
        description="Margin between ring edges and brush slots",
        default=8,
        min=0,
        max=20,
    )

    allow_double_ring: BoolProperty(
        name="Allow Double Ring",
        description="When a brush set has more brushes than one ring holds, show them on two rings (the wheel grows "
                    "to fit the second one). Sets that fit in one ring keep a single ring",
        default=False,
    )

    @property
    def row_gap(self) -> float:
        """Space between the two rings of slots."""
        return max(2.0, self.slot_padding * 0.5)

    def ring_thickness(self, rows: int = 1) -> float:
        return rows * self.slot_size + (rows - 1) * self.row_gap + self.ring_padding * 2.0

    def extra_radius(self, rows: int = 1) -> float:
        """How much the wheel grows for the extra ring(s), so everything inside keeps its size."""
        return (rows - 1) * (self.slot_size + self.row_gap)

    thickness_factor: FloatProperty(
        name="Thickness Factor",
        description="Thickness factor for the brush set ring thickness",
        default=0.4,
        min=0.2,
        max=0.5,
    )


class BrushSet(PropertyGroup):

    name: StringProperty(
        name="Name",
        description="Name of the brush set",
        default="Brush Set"
    )
    items: CollectionProperty(type=BrushMetadata)
    active_item_index: IntProperty(
        name="Active Item Index",
        description="Index of the active item",
        default=-1
    )

    page_index: IntProperty(
        name="Page Index",
        description="Index of the page",
        default=0
    )

    use_color_picker: BoolProperty(
        name="Show Color Picker",
        description="Whether to show the color picker for this brush set",
        default=False
    )

    wheel_type: EnumProperty(
        name="Wheel Type",
        description="Type of the wheel",
        default="UNDEFINED",
        items=[
            ("UNDEFINED", "Undefined", ""),
            ("SCULPT", "Sculpt", ""),
            ("PAINT", "Paint", ""),
            ("VERTEX", "Vertex Paint", ""),
            ("WEIGHT", "Weight", ""),
        ]
    )

    @property
    def brushes(self) -> list[Brush]:
        """
        Get the ACTIVATED brushes in the brush set.
        """
        brushes = [item.brush for item in self.items]
        return [b for b in brushes if b is not None]

    def get_brushes_metadata(self) -> list[BrushMetadata]:
        """
        Get the brushes metadata in the brush set. (typed)
        """
        return self.items

    def add_active_brush(self, context: Context) -> BrushMetadata:
        """
        Add a brush to the brush set.
        :param context: The current context.
        :return: None.
        """
        brush_metadata: BrushMetadata = self.items.add()
        brush_metadata.setup_from_active(context)
        brush_metadata.wheel_order = len(self.items) - 1
        has_color_capabilities = has_brush_color_capabilities(context)
        if has_color_capabilities:
            self.use_color_picker = True
        return brush_metadata

    def add_brush_from_essential(self, mode: str, brush_name: str) -> BrushMetadata:
        """
        Add a brush to the brush set from a brush metadata.
        :param brush_metadata: The brush metadata to add.
        :return: None.
        """
        brush_metadata: BrushMetadata = self.items.add()
        brush_metadata.setup_from_essential(mode, brush_name)
        return brush_metadata

    def draw_list(self, layout: UILayout):
        """
        Draw the brush set list in the UI.
        :param context: The current context.
        :param layout: The layout to draw in.
        :return: None.
        """
        BrushMetadataList.draw_list(layout, self, 'items', 'active_item_index')
