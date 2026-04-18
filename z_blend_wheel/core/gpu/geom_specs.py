

from typing import Sequence, Tuple, TypeAlias


TrisIndices: TypeAlias = Sequence[tuple[int, int, int]]
Coord2: TypeAlias = tuple[int, int]
Coord3: TypeAlias = tuple[float, float, float]
Coord: TypeAlias = Coord2 | Coord3


class GeomSpec:
    """Base class for geometry specifications."""

    def coords(self) -> Sequence[Tuple[float, ...]]:
        raise NotImplementedError

    def indices(self) -> TrisIndices | None:
        return None

    @property
    def ndim(self) -> int:
        pts = self.coords()
        try:
            return len(pts[0])
        except Exception:
            return 0


class RectSpec(GeomSpec):
    """Rectangle specification supporting 2D and 3D (XY plane with constant Z)."""

    def __init__(self, pos: Tuple[float, ...], size: Tuple[float, ...]):
        if len(pos) not in (2, 3):
            raise ValueError("RectSpec pos must be 2D or 3D")
        if len(size) not in (2, 3):
            raise ValueError("RectSpec size must be 2D or 3D")
        self._pos = pos
        self._size = size

    def coords(self) -> Sequence[Tuple[float, ...]]:
        if len(self._pos) == 2:
            x, y = self._pos
            w, h = self._size[:2]
            return [
                (x, y),
                (x + w, y),
                (x + w, y + h),
                (x, y + h),
            ]
        else:
            x, y, z = self._pos
            w, h = self._size[:2]
            return [
                (x, y, z),
                (x + w, y, z),
                (x + w, y + h, z),
                (x, y + h, z),
            ]

    def indices(self) -> TrisIndices | None:
        return [(0, 1, 2), (0, 2, 3)]


class TriaSpec(GeomSpec):
    """Triangle specification supporting 2D and 3D."""

    def __init__(self, p0: Tuple[float, ...], p1: Tuple[float, ...], p2: Tuple[float, ...]):
        if len(p0) != len(p1) or len(p1) != len(p2):
            raise ValueError("TriaSpec points must have same dimensionality")
        if len(p0) not in (2, 3):
            raise ValueError("TriaSpec points must be 2D or 3D")
        self._pts = [p0, p1, p2]

    def coords(self) -> Sequence[Tuple[float, ...]]:
        return list(self._pts)

    def indices(self) -> TrisIndices | None:
        return [(0, 1, 2)]


class CubeSpec(GeomSpec):
    """Cube specification (axis-aligned) with 3D pos and 3D size."""

    def __init__(self, pos: Tuple[float, float, float], size: Tuple[float, float, float]):
        if len(pos) != 3 or len(size) != 3:
            raise ValueError("CubeSpec requires 3D pos and 3D size")
        self._pos = pos
        self._size = size

    def coords(self) -> Sequence[Tuple[float, ...]]:
        x, y, z = self._pos
        w, h, d = self._size
        # 8 vertices
        return [
            (x, y, z),             # 0
            (x + w, y, z),         # 1
            (x + w, y + h, z),     # 2
            (x, y + h, z),         # 3
            (x, y, z + d),         # 4
            (x + w, y, z + d),     # 5
            (x + w, y + h, z + d), # 6
            (x, y + h, z + d),     # 7
        ]

    def indices(self) -> TrisIndices | None:
        # 12 triangles (two per face)
        return [
            (0, 1, 2), (0, 2, 3),  # front
            (4, 6, 5), (4, 7, 6),  # back
            (0, 4, 5), (0, 5, 1),  # bottom
            (3, 2, 6), (3, 6, 7),  # top
            (0, 3, 7), (0, 7, 4),  # left
            (1, 5, 6), (1, 6, 2),  # right
        ]
