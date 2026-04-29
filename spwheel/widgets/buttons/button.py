from typing import Literal
import bpy
from bpy.types import Context, Event
from mathutils import Vector

from ..widget import Widget, WidgetCircle, WidgetRect, WheelTheme
from ...gpu.button_texture import get_custom_button_texture
from ...gpu.draw import draw_text, draw_circle_fill, draw_ring, draw_textured_quad, draw_textured_circle
from ...pg.pg_wheel_theme import ButtonTheme


class ButtonBase:
    button_theme_datapath = 'button'

    action_type: Literal['OPERATOR', 'POPUP']
    operator_id: str
    popup_id: str
    popup_type: Literal['PANEL', 'MENU']
    icon_filepath: str
    label: str = ''
    label_offset: Vector

    active: bool

    def init(self) -> None:
        super().init()
        self.action_type = 'OPERATOR'
        self.operator_id = ''
        self.popup_id = ''
        self.popup_type = ''
        self.icon_filepath = ''
        self.label = ''
        self.label_offset = Vector((0, 0))
        self.active = False

    def set_action(self, action_type: Literal['OPERATOR', 'POPUP'], operator_id: str = '', popup_id: str = '', popup_type: Literal['PANEL', 'MENU'] = '') -> None:
        self.action_type = action_type
        self.operator_id = operator_id
        self.popup_id = popup_id
        self.popup_type = popup_type

    def set_icon(self, icon_filepath: str) -> None:
        self.icon_filepath = icon_filepath
        self.icon_gputex = get_custom_button_texture(icon_filepath)

    def set_label(self, label: str) -> None:
        self.label = label

    def on_left_press(self, context: Context, event: Event) -> bool:
        if self.action_type == 'OPERATOR':
            if self.operator_id == '':
                return False
            op_call = getattr(bpy.ops, self.operator_id, None)
            if op_call is None:
                raise ValueError(f"Operator {self.operator_id} does not exist")
            op_call()
        elif self.action_type == 'POPUP':
            if self.popup_id == '' or self.popup_type == '':
                return False
            if self.popup_type == 'PANEL':
                bpy.ops.wm.call_panel(name=self.popup_id)
            elif self.popup_type == 'MENU':
                bpy.ops.wm.popup_menu(name=self.popup_id)
            else:
                raise ValueError("Popup type must be PANEL or MENU")
        return True

    def _get_button_theme(self, theme: WheelTheme) -> ButtonTheme:
        return getattr(theme, self.button_theme_datapath)

    def draw(self, context: Context, theme: WheelTheme) -> None:
        button_theme = self._get_button_theme(theme)
        self.draw_base(context, button_theme)
        self.draw_icon(context, button_theme)
        self.draw_label(context, button_theme)

    def draw_base(self, context: Context, button_theme: ButtonTheme) -> None:
        raise NotImplementedError("Button base drawing is not implemented yet")

    def draw_label(self, context: Context, button_theme: ButtonTheme) -> None:
        if not self.label:
            return
        draw_text(
            self.label,
            self.label_offset.x, self.label_offset.y,
            size=11.0,
            color=button_theme.label_color,
            align='CENTER',
            shadow=True,
        )

    def draw_icon(self, context: Context, button_theme: ButtonTheme) -> None:
        if not self.icon_gputex:
            return
        draw_textured_circle(
            0.0, 0.0,
            self.radius,
            self.icon_gputex,
            opacity=button_theme.icon_opacity,
            softness=0.025
        )


class ButtonCircle(ButtonBase, WidgetCircle):
    def draw_base(self, context: Context, button_theme: ButtonTheme) -> None:
        base_color, outline_color = button_theme.get_color(self.hovered, self.active)
        print(f"Drawing base: {self.radius}")
        draw_circle_fill(0.0, 0.0, self.radius, base_color, softness=0.015)
        draw_ring(0.0, 0.0, self.radius, outline_color, thickness=2.0 if self.active else 1.5 if self.hovered else 1.0, softness=0.012)

class ButtonRect(ButtonBase, WidgetRect):
    def draw_base(self, context: Context, button_theme: ButtonTheme) -> None:
        raise NotImplementedError("WidgetRect button drawing is not implemented yet")
        # draw_rect_fill(*self.offset, self.width, self.height, col, softness=0.015)
