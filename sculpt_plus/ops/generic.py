from ..ackit import types, props, Poll, Property, OpsReturn


@Poll.ACTIVE_OBJECT.ANY
class GenericOperator(types.Operator):
    new_name = Property.STRING(name="Object Name", default="Best Name Ever")

    def invoke(self, context, event) -> None:
        context.active_object.name = self.new_name
        self.report({'INFO'}, f"New Name {self.new_name}")
        return OpsReturn.FINISH
