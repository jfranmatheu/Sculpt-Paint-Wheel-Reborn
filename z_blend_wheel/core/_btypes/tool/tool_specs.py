from dataclasses import dataclass
from typing import Callable, Literal, Set, Tuple

from bpy.types import Context


SNAP_RADIUS = 16.0 # pixels
SNAP_DISTANCE = 0.1 # blender units


@dataclass
class ToolRaycastSpecs:
    mode: Literal['SCENE', 'OBJECT', 'BVHTREE']  # 'SCENE', 'OBJECT', 'BVHTREE'
    use_in_modal: bool = False  # The raycast is ONLY used for preselection and tool init.
    block_tool_init: bool = True  # The tool is initialized and called ONLY if the raycast hit is valid.
    block_tool_modal: bool = True  # The tool modal is called ONLY if the raycast hit is valid.


_PreselGeomType = Literal['FACE', 'EDGE', 'VERT', 'EDGE_LOOP_BOUNDARY', 'EDGE_BOUNDARY', 'EDGE_LOOP_RING']


@dataclass
class ToolPreselectionSpecs:
    geom_types: Set[_PreselGeomType] | Callable[[Context], Set[_PreselGeomType]]
    use_in_modal: bool = False
    color: Tuple[float, float, float, float] | dict[_PreselGeomType, Tuple[float, float, float, float]] = (0.9, 0.5, 0.05, 0.5)
    point_size: float = 8.0
    line_width: float = 3.0
    only_direct_hits: bool = True
    only_boundary: bool = False
    snap_radius: float | Callable[[Context], float] = SNAP_RADIUS
    snap_distance: float | Callable[[Context], float] = SNAP_DISTANCE

    def get_geom_types(self, context: Context) -> Set[_PreselGeomType]:
        if callable(self.geom_types):
            return self.geom_types(context)
        return self.geom_types

    def get_color(self, primitive_type: _PreselGeomType):
        if isinstance(self.color, dict):
            return self.color.get(primitive_type, (0.9, 0.5, 0.05, 0.5))
        return self.color

    def get_snap_radius(self, context: Context):
        if callable(self.snap_radius):
            return self.snap_radius(context)
        return self.snap_radius

    def get_snap_distance(self, context: Context):
        if callable(self.snap_distance):
            return self.snap_distance(context)
        return self.snap_distance
