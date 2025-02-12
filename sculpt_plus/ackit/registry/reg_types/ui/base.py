from typing import Tuple, Union

from bpy.types import UILayout, Context

from ..base_type import BaseType


class DrawExtension:
    def ui_section(self, 
                  layout: UILayout,
                  title: str,
                  icon: Union[str, int] = 'NONE',
                  use_box: bool = True,
                  align: bool = True,
                  direction: str = 'VERTICAL') -> Tuple[UILayout, UILayout]:
        """Create a section with header and content layouts.
        
        Args:
            layout: Parent layout to create section in
            title: Title text for the section header
            icon: Icon identifier (str) or icon_value (int) for the header
            use_box: Whether to wrap header and content in boxes
            align: Whether to align items in the content
            direction: Content layout direction ('VERTICAL' or 'HORIZONTAL')
        
        Returns:
            Tuple of (header_layout, content_layout)
        """
        # Create main column for the section
        section_col = layout.column(align=True)
        
        # Create header
        if use_box:
            header_box = section_col.box()
            header = header_box.row()
        else:
            header = section_col.row()
        
        # Add title with icon or icon_value
        if isinstance(icon, str):
            header.label(text=title, icon=icon)
        else:  # integer icon_value
            header.label(text=title, icon_value=icon)
        
        # Create content area
        if use_box:
            content_box = section_col.box()
            if direction == 'VERTICAL':
                content = content_box.column(align=align)
            else:
                content = content_box.row(align=align)
        else:
            if direction == 'VERTICAL':
                content = section_col.column(align=align)
            else:
                content = section_col.row(align=align)
        
        return header, content

    def section(self,
                layout: UILayout,
                title: str,
                icon: str = 'NONE',
                header_scale: float = 0.8,
                content_scale: float = 1.2) -> tuple[UILayout, UILayout]:
        section = layout.column(align=True)
        header = section.box().row(align=True)
        header.scale_y = header_scale
        header.label(text=title, icon=icon)
        content = section.box().column()
        content.scale_y = content_scale
        return header, content

    def row_scale(self, layout: UILayout, scale: float = 1.4) -> UILayout:
        row = layout.row()
        row.scale_y = scale
        return row


class BaseUI(BaseType):
    layout: UILayout
    bl_idname: str
    bl_label: str

    @property
    def layout(self) -> UILayout:
        return self.layout

    def draw(self, context: Context):
        self.draw_ui(context, self.layout)

    def draw_ui(self, context: Context, layout: UILayout):
        pass

    ###################################

    @classmethod
    def draw_in_layout(cls, layout: UILayout) -> None:
        pass
