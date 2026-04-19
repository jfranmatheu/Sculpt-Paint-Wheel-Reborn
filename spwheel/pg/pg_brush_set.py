from bpy.props import CollectionProperty, IntProperty, StringProperty
from bpy.types import Brush, Context, UILayout

from .pg_brush_metadata import BrushMetadata
from ..core.bl_types import PropertyGroup
from ..ui.lists.ul_brush_metadata_list import BrushMetadataList


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
        return brush_metadata

    def draw_list(self, layout: UILayout):
        """
        Draw the brush set list in the UI.
        :param context: The current context.
        :param layout: The layout to draw in.
        :return: None.
        """
        BrushMetadataList.draw_list(layout, self, 'items', 'active_item_index')
