from dataclasses import dataclass
from typing import List, Tuple, Optional
from ..vector import Vector2, Vector3


@dataclass
class BoundingBox2D:
    min_point: Vector2
    max_point: Vector2

    @classmethod
    def from_points(cls, points: List[Vector2]) -> 'BoundingBox2D':
        if not points:
            raise ValueError("Cannot create bounding box from empty point list")
        
        min_x = min(p.x for p in points)
        min_y = min(p.y for p in points)
        max_x = max(p.x for p in points)
        max_y = max(p.y for p in points)
        
        return cls(Vector2(min_x, min_y), Vector2(max_x, max_y))

    @property
    def width(self) -> float:
        return self.max_point.x - self.min_point.x

    @property
    def height(self) -> float:
        return self.max_point.y - self.min_point.y

    @property
    def center(self) -> Vector2:
        return (self.min_point + self.max_point) * 0.5

    @property
    def corners(self) -> List[Vector2]:
        return [
            Vector2(self.min_point.x, self.min_point.y),  # Top-left
            Vector2(self.max_point.x, self.min_point.y),  # Top-right
            Vector2(self.max_point.x, self.max_point.y),  # Bottom-right
            Vector2(self.min_point.x, self.max_point.y)   # Bottom-left
        ]

    def expand(self, margin: float) -> 'BoundingBox2D':
        return BoundingBox2D(
            self.min_point - Vector2(margin, margin),
            self.max_point + Vector2(margin, margin)
        )

@dataclass
class BoundingBox3D:
    min_point: Vector3
    max_point: Vector3

    @property
    def center(self) -> Vector3:
        return (self.min_point + self.max_point) * 0.5

    @property
    def size(self) -> Vector3:
        return self.max_point - self.min_point
