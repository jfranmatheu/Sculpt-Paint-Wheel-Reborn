from bpy import types as bpy_types


__all__ = ['Layout']


class Layout:
    layout: bpy_types.UILayout

    def draw(self, context: bpy_types.Context) -> None:
        self.draw_ui(context, self.layout)
    
    def draw_ui(self, context: bpy_types.Context, layout: bpy_types.UILayout) -> None:
        pass