"""Weight wheel toolbar widget (ported from legacy weight toolbar behavior)."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from pathlib import Path
from typing import TYPE_CHECKING, Callable

import bpy
from mathutils import Vector

from ..gpu.button_texture import get_custom_button_texture
from ..gpu.draw import draw_circle_fill, draw_ring, draw_text, draw_textured_circle
from .widget import Widget
from ..ops.op_weight_tools import OpWeightBoxSelectToolOptions

if TYPE_CHECKING:
    from bpy.types import Context, Event
    from ..pg.pg_wheel_theme import WheelTheme


@dataclass(frozen=True)
class _ToolSpec:
    label: str
    name: str
    is_brush: bool
    icon_relpath: str
    always_trigger: bool = False
    op_call: str | Callable = ""
    offset: tuple[float, float] = (0.0, 0.0)

    @property
    def identifier(self) -> str:
        return f"builtin_brush.{self.name}" if self.is_brush else f"builtin.{self.name}"


_TOOLS: tuple[_ToolSpec, ...] = (
    _ToolSpec("Draw", "draw", True, "Paint_Draw.png"),
    _ToolSpec("Blur", "blur", True, "Paint_Blur.png", offset=(0.0, -10.0)),
    _ToolSpec("Average", "average", True, "Paint_Average.png", offset=(0.0, -10.0)),
    _ToolSpec("Smear", "smear", True, "Paint_Smear.png"),
    _ToolSpec("Gradient", "gradient", False, "Paint_Gradient.png", op_call=lambda: bpy.ops.paint.weight_gradient(type='LINEAR')),
    _ToolSpec("Sample Weight", "sample_weight", False, "Paint_Sample_Weight.png", offset=(0.0, -10.0)), #, op_call=lambda: bpy.ops.paint.weight_sample()),
    _ToolSpec("Sample Vertex Group", "sample_vertex_group", False, "Paint_Sample_Vertex_Group.png", offset=(0.0, -10.0)), #, op_call=lambda: bpy.ops.paint.weight_sample_group()),
    _ToolSpec("Select Box", "select_box", False, "Select_Box.png", always_trigger=True) #, op_call=lambda: OpWeightBoxSelectToolOptions.run_invoke()),
)


class WeightToolbarWidget(Widget):
    interactable = True
    use_modal = False

    def init(self) -> None:
        self.item_size = 28.0
        self.spacing = Vector((6.0, 5.0))
        self.rows = 2
        self.items_per_row = max(1, int(ceil(len(_TOOLS) / max(1, self.rows))))
        self._positions: list[Vector] = []
        self._centers: list[Vector] = []
        self._hover_idx = -1
        self._active_idx = -1
        self._icon_paths: list[str] = []
        self._base_y = -90.0

    def _tool_button_radius(self) -> float:
        return self.item_size * 0.5

    def _tool_icon_half(self) -> float:
        return self._tool_button_radius() * 0.92

    def _active_tool_idname(self, context: "Context") -> str:
        tool = context.workspace.tools.from_space_view3d_mode(context.mode)
        return tool.idname if tool else ""

    def _sync_active_index(self, context: "Context") -> None:
        aid = self._active_tool_idname(context)
        self._active_idx = -1
        for i, spec in enumerate(_TOOLS):
            if aid == spec.identifier:
                self._active_idx = i
                break

    def _layout(self) -> None:
        self._positions.clear()
        self._centers.clear()
        total_w = self.item_size * self.items_per_row + self.spacing.x * max(0, self.items_per_row - 1)
        x0 = self.offset.x - total_w * 0.5
        y0 = self.offset.y + self._base_y
        row_col = 0
        row_idx = 0
        for spec in _TOOLS:
            px = x0 + row_col * (self.item_size + self.spacing.x) + spec.offset[0]
            py = y0 - row_idx * (self.item_size + self.spacing.y) + spec.offset[1]
            p = Vector((px, py))
            self._positions.append(p)
            self._centers.append(p + Vector((self.item_size * 0.5, self.item_size * 0.5)))
            row_col += 1
            if row_col >= self.items_per_row:
                row_col = 0
                row_idx += 1

    def on_wheel_activate(self, context: "Context", wheel_prefs, storage, wg_prefs=None) -> None:
        wr = self.wheel.radius
        self.item_size = max(32.0, min(36.0, wr * 0.17))
        # Place the toolbar closer to the lower outer edge of the wheel.
        self._base_y = -max(84.0, wr * 0.66)
        assets_tools_dir = Path(__file__).resolve().parents[1] / "assets" / "images" / "tools"
        self._icon_paths = [
            str(assets_tools_dir / s.icon_relpath)
            for s in _TOOLS
        ]
        self._layout()
        self._sync_active_index(context)
        self._hover_idx = -1

    def test_hit(self, context: "Context", p: Vector) -> bool:
        self._sync_active_index(context)
        self._hover_idx = -1
        sz = self.item_size
        for i, pos in enumerate(self._positions):
            if pos.x <= p.x <= pos.x + sz and pos.y <= p.y <= pos.y + sz:
                self._hover_idx = i
                return True
        return False

    def _set_weight_draw_toggle(self, context: "Context") -> None:
        ts = context.tool_settings
        wpaint = getattr(ts, "weight_paint", None)
        if wpaint is None or not getattr(wpaint, "brush", None):
            return
        current = wpaint.brush
        if current.name == "Add":
            name = "Subtract"
        elif current.name == "Subtract":
            name = "Add"
        else:
            name = "Add"
        nxt = bpy.data.brushes.get(name)
        if nxt is not None:
            wpaint.brush = nxt

    def on_left_press(self, context: "Context", event: "Event") -> bool:
        if self._hover_idx < 0:
            return False
        spec = _TOOLS[self._hover_idx]
        current_id = self._active_tool_idname(context)
        prefs = self.wheel.prefs.weight if hasattr(self.wheel, "prefs") else None
        if (
            context.mode == "PAINT_WEIGHT"
            and spec.name == "Draw"
            and current_id == spec.identifier
            and prefs is not None
            and getattr(prefs, "use_add_substract_brush", False)
        ):
            self._set_weight_draw_toggle(context)
        if current_id != spec.identifier or spec.always_trigger:
            bpy.ops.wm.tool_set_by_id(name=spec.identifier)
        if spec.op_call:
            if callable(spec.op_call):
                spec.op_call()
            else:
                op_ref = bpy.ops
                for part in spec.op_call.split("."):
                    op_ref = getattr(op_ref, part, None)
                    if op_ref is None:
                        break
                if callable(op_ref):
                    op_ref("INVOKE_DEFAULT")
        self._sync_active_index(context)
        context.region.tag_redraw()
        return True

    def draw(self, context: "Context", theme: "WheelTheme") -> None:
        col_hover = (0.25, 0.45, 0.7, 0.8)
        col_active = (0.1, 0.3, 0.55, 0.8)
        col_idle_hov = (0.04, 0.04, 0.04, 0.8)
        col_idle = (0.015, 0.015, 0.015, 0.8)
        rad = self._tool_button_radius()
        icon_half = self._tool_icon_half()
        for i, (p, c) in enumerate(zip(self._positions, self._centers)):
            is_hover = i == self._hover_idx
            is_active = i == self._active_idx
            if is_active:
                col = col_hover if is_hover else col_active
            else:
                col = col_idle_hov if is_hover else col_idle
            draw_circle_fill(c.x, c.y, rad, col, softness=0.015)
            draw_ring(c.x, c.y, rad, (0.14, 0.14, 0.2, 0.8), thickness=1.0, softness=0.08)
            tex = get_custom_button_texture(self._icon_paths[i]) if i < len(self._icon_paths) else None
            if tex is not None:
                draw_textured_circle(c.x, c.y, icon_half * (1.06 if is_hover else 1.0), tex, opacity=1.0 if is_hover else 0.90, softness=0.2)
            else:
                draw_text(_TOOLS[i].label[:8], c.x, c.y, size=8.5, color=(0.9, 0.9, 0.9, 0.9), align="CENTER", shadow=True)
