from bpy.types import Context, Event

from ...gpu.draw import draw_textured_circle
from ...pg.pg_wheel_theme import ButtonTheme
from .button import ButtonCircle
from ...pg.pg_brush_metadata import BrushMetadata
from ..widget import WheelTheme


ICON_INSET = 0.84  # Preview radius, as a fraction of the slot: the backplate shows around it.


class PickerBrushButton(ButtonCircle):
    _brush_metadata: BrushMetadata
    button_theme_datapath = 'brush_picker_button'

    def init(self) -> None:
        super().init()
        self._brush_metadata = None

    def set_brush_metadata(self, brush_metadata: BrushMetadata, show_label: bool = True) -> None:
        self.interactable = True
        self._brush_metadata = brush_metadata
        self.icon_gputex = brush_metadata.gputex
        self.label = brush_metadata.name if show_label else ''

    @property
    def hover_label(self) -> str | None:
        """Brush name, shown by the wheel's centre widget while hovered."""
        return self._brush_metadata.name if self._brush_metadata is not None else None

    def clear_brush_metadata(self) -> None:
        self.interactable = False
        self._brush_metadata = None
        self.icon_gputex = None
        self.label = ''

    def on_left_press(self, context: Context, event: Event) -> bool:
        if not self.interactable or self._brush_metadata is None:
            return False
        self._brush_metadata.activate()
        self.parent.deactivate_all_pickers()
        self.active = True
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
            self.radius * ICON_INSET,
            tex,
            opacity=button_theme.icon_opacity,
            softness=0.025,
        )

    def draw(self, context: Context, theme: WheelTheme) -> None:
        super().draw(context, theme)
