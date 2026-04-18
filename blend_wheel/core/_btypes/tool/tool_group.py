from typing import Dict, List, Optional, Set, Type, TypeVar
from dataclasses import dataclass, field

import bpy
from bpy.types import Context
from bpy.utils import register_class, unregister_class

from .btype_tool import BType_WorkSpaceTool
from ..gz.btype_gz_tool_multi import BType_GZ_ToolMulti, BType_GZG_ToolMulti

T = TypeVar('T', bound=BType_WorkSpaceTool)


tool_groups: Dict[str, 'ToolGroup'] = {}


@dataclass
class ToolbarItem:
    tool: Type[T]
    label: str
    icon: Optional[str | int] = None
    order: int = 0

    @property
    def idname(self) -> str:
        return self.tool.bl_idname


@dataclass
class ToolGroup:
    name: str
    space_type: str
    after: str
    separator: bool = True
    use_toolbar: bool = True

    tool_items: List[ToolbarItem] = field(default_factory=list)
    _gz_cls: Optional[Type[BType_GZ_ToolMulti]] = None
    _gzg_cls: Optional[Type[BType_GZG_ToolMulti]] = None

    def __post_init__(self):
        tool_groups[self.name] = self
        self._setup_toolbar()

    def __hash__(self) -> int:
        return hash(f"{self.space_type}_{self.name}")

    @property
    def tools(self) -> Set[Type[T]]:
        return {item.tool for item in self.tool_items}

    @property
    def tool_ids(self) -> Set[str]:
        return {item.tool.bl_idname for item in self.tool_items}

    @property
    def ordered_tool_items(self) -> List[ToolbarItem]:
        return sorted(self.tool_items, key=lambda x: x.order)

    @property
    def ordered_tools(self) -> List[Type[T]]:
        return [item.tool for item in self.ordered_tool_items]

    def add_tool(self, label: str, icon: Optional[str | int] = None, order: int = 0) -> Type[T]:
        """ Decorator to add a tool to the group.
        """
        def decorator(tool_cls: Type[T]) -> Type[T]:
            tool_cls.register_kwargs = {
                'group': True if order == 0 else False,
                'separator': self.separator,
                'after': self.after,
            }
            tool_cls.bl_space_type = self.space_type
            tool_cls.bl_region_type = 'WINDOW'
            tool_cls.group = self
            self.tool_items.append(ToolbarItem(tool_cls, label, icon, order))
            return tool_cls
        return decorator

    def select_tool(self, context: Context, tool_item: ToolbarItem) -> None:
        if tool_item in self.tool_items:
            bpy.ops.wm.tool_set_by_id(name=tool_item.tool.bl_idname, cycle=False)
        else:
            raise ValueError(f"Tool {tool_item.tool.bl_idname} is not in the group {self.name}")

    def get_tool_item_at_order(self, order: int) -> Optional[ToolbarItem]:
        return self.ordered_tool_items[order] if order < len(self.ordered_tool_items) else None

    def _setup_toolbar(self) -> None:
        if not self.use_toolbar:
            return

        name = self.name.replace(' ', '_')
        if self._gz_cls is None:
            self._gz_cls = type(f'GZ_ToolGroup_{name}', (BType_GZ_ToolMulti,), {
                '_tool_group': self,
            })
            self._gz_cls.tag_register()
        if self._gzg_cls is None:
            self._gzg_cls = type(f'GZG_ToolGroup_{name}', (BType_GZG_ToolMulti,), {
                'bl_label': f'{self.name} Toolbar',
                'bl_space_type': self.space_type,
                '_tool_group': self,
                '_gizmos_cls': (self._gz_cls, )
            })
            self._gzg_cls.tag_register()

    def __del__(self):
        global tool_groups
        if self.name in tool_groups:
            del tool_groups[self.name]


def late_init():
    group: ToolGroup
    first_tool_idname: Optional[str] = None
    for group in tool_groups.values():
        for i, item in enumerate(group.ordered_tool_items):
            if i == 0:
                item.tool.register_kwargs['group'] = True
                item.tool.register_kwargs['separator'] = group.separator
                item.tool.register_kwargs['after'] = group.after
                first_tool_idname = item.tool.bl_idname
            else:
                item.tool.register_kwargs['group'] = False
                item.tool.register_kwargs['separator'] = False
                item.tool.register_kwargs['after'] = first_tool_idname

def register():
    global tool_groups
    for group in tool_groups.values():
        if not group.use_toolbar:
            continue
        if group._gzg_cls is not None:
            register_class(group._gzg_cls)
        if group._gz_cls is not None:
            register_class(group._gz_cls)

def unregister():
    global tool_groups
    for group in tool_groups.values():
        if not group.use_toolbar:
            continue
        if group._gzg_cls is not None:
            unregister_class(group._gzg_cls)
            group._gzg_cls = None
        if group._gz_cls is not None:
            unregister_class(group._gz_cls)
            group._gz_cls = None
