from ..ackit import types, props, Poll, Property, OpsReturn, ModalFlags

import blf


# @ModalFlags.USE_MOUSE
@ModalFlags.DRAW_POST_PIXEL.VIEW_3D
@Poll.ACTIVE_OBJECT.ANY
class ModalDrawOperator(types.Modal):
    def modal_enter(self, context, event):
        self.text = "Hello, world!"

    def modal_update(self, context, event) -> OpsReturn:
        if event.type == 'ESC':
            return OpsReturn.FINISH
        if event.unicode:
            self.text += event.unicode
            self.tag_redraw(context)
            return OpsReturn.RUN
        elif event.type == 'BACKSPACE' and self.text != '':
            self.text = self.text[:-1]
            self.tag_redraw(context)
            return OpsReturn.RUN
        return OpsReturn.PASS

    def draw_2d(self, context):
        blf.size(0, 12)
        blf.position(0, 100, 50, 0)
        blf.color(0, 1, 0, 0, 1)
        blf.draw(0, self.text)
