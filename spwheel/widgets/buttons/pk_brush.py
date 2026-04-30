from bpy.types import Context, Event

from ...gpu.draw import draw_textured_circle
from ...pg.pg_wheel_theme import ButtonTheme
from .button import ButtonCircle
from ...pg.pg_brush_metadata import BrushMetadata
from ..widget import WheelTheme


class PickerBrushButton(ButtonCircle):
    _brush_metadata: BrushMetadata
    button_theme_datapath = 'brush_picker_button'

    def init(self) -> None:
        super().init()
        self._brush_metadata = None

    def set_brush_metadata(self, brush_metadata: BrushMetadata, show_label: bool = True) -> None:
        self._brush_metadata = brush_metadata
        self.icon_gputex = brush_metadata.gputex
        self.label = brush_metadata.name if show_label else ''

    def clear_brush_metadata(self) -> None:
        self._brush_metadata = None
        self.icon_gputex = None
        self.label = ''

    def on_left_press(self, context: Context, event: Event) -> bool:
        self._brush_metadata.activate()
        return True

    def draw_icon(self, context: Context, button_theme: ButtonTheme) -> None:
        tex = None
        if self._brush_metadata is not None:
            tex = self._brush_metadata.gputex
        if not tex:
            tex = self.icon_gputex
        if not tex:
            return
        draw_textured_circle(
            0.0,
            0.0,
            self.radius,
            tex,
            opacity=button_theme.icon_opacity,
            softness=0.025,
        )

    def draw(self, context: Context, theme: WheelTheme) -> None:
        super().draw(context, theme)
