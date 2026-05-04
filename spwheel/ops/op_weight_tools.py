"""Weight specific helper operators used by weight wheel buttons."""

from bpy.props import EnumProperty

from ..core.bl_types import OperatorAction


class OpWeightBoxSelectToolOptions(OperatorAction):
    """Popup with face/vertex masking toggles for weight paint box select."""
    bl_label = "Box Select Options"

    option: EnumProperty(
        items=(
            ("use_paint_mask", "Faces", "Face selection masking for weight paint", "FACESEL", 0),
            ("use_paint_mask_vertex", "Vertex", "Vertex selection masking for weight paint", "VERTEXSEL", 1),
        ),
        default="use_paint_mask_vertex",
    )

    @classmethod
    def poll_operator(cls, context):
        return context.mode == "PAINT_WEIGHT" and context.active_object and context.active_object.type == "MESH"

    def draw(self, context):
        data = context.active_object.data
        row = self.layout.row(align=True)
        row.prop(data, "use_paint_mask", text="", icon="FACESEL")
        row.prop(data, "use_paint_mask_vertex", text="", icon="VERTEXSEL")

    def invoke(self, context, event):
        return context.window_manager.invoke_popup(self, width=90)

    def action(self, context, event):
        data = context.active_object.data
        setattr(data, self.option, not bool(getattr(data, self.option)))
