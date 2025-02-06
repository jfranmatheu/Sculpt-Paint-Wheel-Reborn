from ..ackit import types, props, OpsOptions, Poll, Property


@OpsOptions.REGISTER
@OpsOptions.UNDO
@Poll.ACTIVE_OBJECT.MESH
@Poll.MODE.OBJECT
class ActionOperator(types.Action):
    use_something = Property.BOOL(name="Use Something")
    my_value = Property.FLOAT(name="Value")

    def draw_ui(self, context, layout):
        # print(self.props.__dict__)  # This will show you all properties in the DescriptorPropertyCollection
        row = layout.row()
        row.prop(*self.props.use_something, text="Enable Feature")
        row.prop(*self.props.my_value, text="Nice value")

    def action(self, context) -> None:
        if self.use_something:
            context.active_object.location.z = self.my_value
            self.report({'INFO'}, f"Value {self.my_value}")
