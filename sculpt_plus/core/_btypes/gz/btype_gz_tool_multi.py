from typing import TYPE_CHECKING, Optional, Tuple

from bpy.types import Context
from mathutils import Color

from ...debug import print_debug
from .btype_gzg import BType_GZG
from .btype_gz import BType_GZ
from ..tool.multi.tool_multi import Tool
from ..tool.common import get_active_tool
from ...gpu import imm_2d
from ...utils.op_return import OpReturn

if TYPE_CHECKING:
    from ..tool.multi.btype_tool_multi import BType_WorkSpaceToolMulti
    from ..tool.tool_group import ToolGroup, ToolbarItem
else:
    BType_WorkSpaceToolMulti = None
    ToolGroup = None
    ToolbarItem = None


class BType_GZG_ToolMulti(BType_GZG):
    # defaults
    bl_space_type: str = 'VIEW_3D'
    bl_region_type: str = 'WINDOW'
    bl_options = {'EXCLUDE_MODAL', 'PERSISTENT'}

    _btype_tool_cls: Optional['BType_WorkSpaceToolMulti'] = None
    _tool_group: Optional['ToolGroup'] = None

    @classmethod
    def poll(cls, context: Context) -> bool:
        if active_tool := get_active_tool(context, cls.bl_space_type):
            if cls._tool_group is not None:
                return active_tool.idname in cls._tool_group.tool_ids
            elif cls._btype_tool_cls is not None:
                return active_tool.idname == cls._btype_tool_cls.bl_idname
        return False


class BType_GZ_ToolMulti(BType_GZ):
    """
    Toolbar Gizmo for multi-tool selection.
    """
    _btype_tool_cls: Optional['BType_WorkSpaceToolMulti'] = None
    _tool_group: Optional['ToolGroup'] = None

    toolbar_position: str = 'TOP'
    toolbar_margin: int = 8
    toolbar_slot_size: int = 35
    toolbar_slot_spacing: int = 16
    toolbar_slots_padding: int = 4
    toolbar_slot_icon_padding: int = 0
    toolbar_fill_color: Color = (0.12, 0.12, 0.12, .98)
    toolbar_slot_fill_color: Color = (0.08, 0.08, 0.08, 0.2)
    toolbar_slot_outline_color: Color = (0, 0, 0, 0) # (0.5, 0.5, 0.5, 0.5)
    toolbar_slot_active_outline_color: Color = (0.5, 0.65, .92, 0.8)
    toolbar_slot_hover_fill_color: Color = (0.24, 0.24, 0.24, 0.8)
    toolbar_slot_active_fill_color: Color = (0.5, 0.65, .92, 0.8)
    toolbar_slot_spacing_line_color: Color = (0.5, 0.5, 0.5, 0.5)

    hovered_tool: Optional[Tool | ToolbarItem] = None

    @classmethod
    def select_hovered_tool(cls, context: Context):
        if cls.hovered_tool is None:
            return
        if cls._tool_group is not None:
            cls._tool_group.select_tool(context, cls.hovered_tool)
        elif cls._btype_tool_cls is not None:
            cls._btype_tool_cls.select_tool(context, cls.hovered_tool)

    def test_select(self, ctx, m):
        return self.test_slot(ctx, m)

    def invoke(self, ctx, evt):
        if self.__class__.hovered_tool is not None:
            self.__class__.select_hovered_tool(ctx)
            return OpReturn.FINISH
        return OpReturn.CANCEL

    def draw(self, context):
        self.draw_toolbar(context)

    @classmethod
    def _compute_toolbar_coords(cls, context: Context):
        mid_region_x = context.region.width // 2
        if cls._tool_group is not None:
            tool_count = len(cls._tool_group.tool_items)
        else:
            tool_count = len(cls._btype_tool_cls.tools or [])
        if tool_count <= 0:
            return None, None
        inner_spacing = cls.toolbar_slot_spacing * max(0, tool_count - 1)
        toolbar_width = cls.toolbar_slot_size * tool_count + inner_spacing + cls.toolbar_slots_padding * 2
        toolbar_height = cls.toolbar_slot_size + cls.toolbar_slots_padding * 2
        x = mid_region_x - toolbar_width // 2
        if cls.toolbar_position == 'TOP':
            y = cls.toolbar_margin
        else:
            y = context.region.height - toolbar_height - cls.toolbar_margin

        # not needed inside gizmo drawing callback!
        # x += context.region.x        
        # y += context.region.y

        toolbar_x = x
        toolbar_y = y

        x += cls.toolbar_slots_padding
        y += cls.toolbar_slots_padding

        slots_coords = []
        for i in range(tool_count):
            slots_coords.append((x, y))
            x += cls.toolbar_slot_size + cls.toolbar_slot_spacing

        return (
            (toolbar_x, toolbar_y, toolbar_width, toolbar_height),
            slots_coords
        )

    @classmethod
    def test_slot(cls, context: Context, xy: Tuple[int, int]):
        toolbar_coords, slots_coords = cls._compute_toolbar_coords(context)
        if toolbar_coords is None or slots_coords is None:
            return -1
        for i, slot_coords in enumerate(slots_coords):
            x, y = slot_coords
            if x <= xy[0] <= x + cls.toolbar_slot_size and y <= xy[1] <= y + cls.toolbar_slot_size:
                if cls._tool_group is not None:
                    hovered_tool = cls._tool_group.get_tool_item_at_order(i)
                else:
                    hovered_tool = cls._btype_tool_cls.tools[i].get_instance()
                if hovered_tool != cls.hovered_tool:
                    cls.hovered_tool = hovered_tool
                    context.region.tag_redraw()
                return 1
        else:
            if cls.hovered_tool is not None:
                cls.hovered_tool = None
                context.region.tag_redraw()
            return -1

    @classmethod
    def draw_toolbar(cls, context: Context):
        if cls._tool_group is not None:
            tools = cls._tool_group.ordered_tool_items
            active_tool = get_active_tool(context, cls._tool_group.space_type)
            active_tool_idname = active_tool.idname if active_tool else ''
            is_active_fn = lambda tool, active_tool_idname=active_tool_idname: tool.idname == active_tool_idname
            is_hovered_fn = lambda tool: tool == cls.hovered_tool
        else:
            tools = cls._btype_tool_cls.tools
            is_active_fn = lambda tool: tool.get_instance() == cls._btype_tool_cls.active_tool
            is_hovered_fn = lambda tool: tool.get_instance() == cls.hovered_tool
        if not tools:
            print_debug(f"⚠️ WARN! No tools to draw for multi-tool: {cls.__name__}")
            return
        toolbar_coords, slots_coords = cls._compute_toolbar_coords(context)
        if toolbar_coords is None or slots_coords is None:
            print_debug(f"⚠️ WARN! Failed to compute toolbar coords for multi-tool: {cls.__name__}")
            return

        # Draw main toolbar rectangle
        imm_2d.draw_rect_fill(*toolbar_coords, cls.toolbar_fill_color)
        
        max_index = len(tools) - 1

        for i, tool in enumerate(tools):
            x, y = slots_coords[i]
            is_active = is_active_fn(tool)
            is_hovered = is_hovered_fn(tool)
            if is_active or is_hovered:
                fill_color = cls.toolbar_slot_active_fill_color if is_active else cls.toolbar_slot_hover_fill_color if is_hovered else cls.toolbar_slot_fill_color
                # outline_color = cls.toolbar_slot_active_outline_color if is_active else cls.toolbar_slot_outline_color
                # imm_2d.draw_rect(x, y, cls.toolbar_slot_size, cls.toolbar_slot_size, fill_color, outline_color, line_width=2 if is_active else 1)
                
                act_x = x
                act_y = y
                act_w = cls.toolbar_slot_size
                act_h = cls.toolbar_slot_size
                if i > 0 and i < max_index:
                    act_x -= cls.toolbar_slot_spacing / 2
                    act_y -= cls.toolbar_slots_padding
                    act_w += cls.toolbar_slot_spacing
                    act_h += cls.toolbar_slots_padding * 2
                    act_y += 0.75
                    act_h -= 1.5
                elif i == 0:
                    act_x -= cls.toolbar_slot_spacing / 4
                    act_y -= cls.toolbar_slots_padding
                    act_w += cls.toolbar_slot_spacing / 1.5
                    act_h += cls.toolbar_slots_padding * 2
                    act_x += 0.75
                    act_y += 0.75
                    act_h -= 1.5
                elif i == max_index:
                    act_x -= cls.toolbar_slot_spacing / 2.5
                    act_y -= cls.toolbar_slots_padding
                    act_w += cls.toolbar_slot_spacing / 1.5
                    act_h += cls.toolbar_slots_padding * 2
                    act_y += 0.75
                    act_w -= 1.5
                    act_h -= 1.5
                imm_2d.draw_rect_fill(act_x, act_y, act_w, act_h, fill_color)
            if tool.icon is not None and hasattr(tool.icon, 'gputex'):
                if gputex := tool.icon.gputex:
                    imm_2d.draw_texture(gputex,
                                        x + cls.toolbar_slot_icon_padding,
                                        y + cls.toolbar_slot_icon_padding,
                                        cls.toolbar_slot_size - cls.toolbar_slot_icon_padding * 2,
                                        cls.toolbar_slot_size - cls.toolbar_slot_icon_padding * 2)

            if i > 0:
                mid_x = x - cls.toolbar_slot_spacing / 2
                imm_2d.draw_lines(
                    (
                        (mid_x, cls.toolbar_margin),
                        (mid_x, cls.toolbar_margin + cls.toolbar_slot_size + cls.toolbar_slots_padding * 2)
                    ),
                    cls.toolbar_slot_spacing_line_color,
                    line_width=2
                )
