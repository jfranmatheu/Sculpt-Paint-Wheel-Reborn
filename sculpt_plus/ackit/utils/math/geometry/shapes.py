from dataclasses import dataclass
from typing import List, Tuple, Optional, Union, Iterator
import math
from ..vector import Vector2
from ..basic import clamp


@dataclass
class Point2D:
    """2D Point with additional geometric utilities"""
    x: float
    y: float

    @classmethod
    def from_vector2(cls, vector: Vector2) -> 'Point2D':
        return cls(vector.x, vector.y)

    @classmethod
    def from_tuple(cls, tup: Tuple[float, float]) -> 'Point2D':
        return cls(tup[0], tup[1])

    @classmethod
    def origin(cls) -> 'Point2D':
        return cls(0.0, 0.0)

    def to_vector2(self) -> Vector2:
        return Vector2(self.x, self.y)

    def to_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)

    def distance_to(self, other: Union['Point2D', Vector2, Tuple[float, float]]) -> float:
        """Calculate distance to another point"""
        if isinstance(other, tuple):
            other = Point2D.from_tuple(other)
        elif isinstance(other, Vector2):
            other = Point2D.from_vector2(other)
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

    def manhattan_distance_to(self, other: Union['Point2D', Vector2, Tuple[float, float]]) -> float:
        """Calculate Manhattan distance to another point"""
        if isinstance(other, tuple):
            other = Point2D.from_tuple(other)
        elif isinstance(other, Vector2):
            other = Point2D.from_vector2(other)
        return abs(self.x - other.x) + abs(self.y - other.y)

    def midpoint_to(self, other: Union['Point2D', Vector2, Tuple[float, float]]) -> 'Point2D':
        """Calculate midpoint between this point and another"""
        if isinstance(other, tuple):
            other = Point2D.from_tuple(other)
        elif isinstance(other, Vector2):
            other = Point2D.from_vector2(other)
        return Point2D((self.x + other.x) * 0.5, (self.y + other.y) * 0.5)

    def rotate_around(self, center: 'Point2D', angle_rad: float) -> 'Point2D':
        """Rotate point around a center point by given angle in radians"""
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        dx = self.x - center.x
        dy = self.y - center.y
        return Point2D(
            center.x + dx * cos_a - dy * sin_a,
            center.y + dx * sin_a + dy * cos_a
        )

    def lerp_to(self, other: 'Point2D', t: float) -> 'Point2D':
        """Linear interpolation to another point"""
        t = clamp(t, 0.0, 1.0)
        return Point2D(
            self.x + (other.x - self.x) * t,
            self.y + (other.y - self.y) * t
        )

    def __add__(self, other: Union['Point2D', Vector2, Tuple[float, float]]) -> 'Point2D':
        if isinstance(other, tuple):
            return Point2D(self.x + other[0], self.y + other[1])
        return Point2D(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Union['Point2D', Vector2, Tuple[float, float]]) -> Vector2:
        """Subtracting points yields a vector"""
        if isinstance(other, tuple):
            return Vector2(self.x - other[0], self.y - other[1])
        return Vector2(self.x - other.x, self.y - other.y)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, (Point2D, Vector2, tuple)):
            return NotImplemented
        if isinstance(other, tuple):
            return self.x == other[0] and self.y == other[1]
        return self.x == other.x and self.y == other.y

    def __str__(self) -> str:
        return f"Point2D({self.x:.3f}, {self.y:.3f})"


@dataclass
class Circle:
    """Circle with comprehensive geometric utilities"""
    center: Point2D
    radius: float

    @classmethod
    def from_points(cls, points: List[Point2D]) -> 'Circle':
        """Create minimum circle that contains all given points (simple average method)"""
        if not points:
            raise ValueError("Cannot create circle from empty point list")
        
        # Calculate center as average of points
        center_x = sum(p.x for p in points) / len(points)
        center_y = sum(p.y for p in points) / len(points)
        center = Point2D(center_x, center_y)
        
        # Calculate radius as maximum distance to any point
        radius = max(center.distance_to(p) for p in points)
        
        return cls(center, radius)

    @classmethod
    def from_three_points(cls, p1: Point2D, p2: Point2D, p3: Point2D) -> 'Circle':
        """Create circle that passes through three points"""
        # Calculate midpoints of two chords
        mid1 = p1.midpoint_to(p2)
        mid2 = p2.midpoint_to(p3)

        # Calculate perpendicular bisector slopes
        if p2.x - p1.x != 0:
            slope1 = -(p2.x - p1.x) / (p2.y - p1.y)
        else:
            slope1 = float('inf')
            
        if p3.x - p2.x != 0:
            slope2 = -(p3.x - p2.x) / (p3.y - p2.y)
        else:
            slope2 = float('inf')

        # Handle special cases
        if slope1 == slope2:
            raise ValueError("Points are collinear")

        # Calculate center
        if slope1 == float('inf'):
            center_x = mid1.x
            center_y = slope2 * (center_x - mid2.x) + mid2.y
        elif slope2 == float('inf'):
            center_x = mid2.x
            center_y = slope1 * (center_x - mid1.x) + mid1.y
        else:
            center_x = (mid2.y - mid1.y + slope1 * mid1.x - slope2 * mid2.x) / (slope1 - slope2)
            center_y = slope1 * (center_x - mid1.x) + mid1.y

        center = Point2D(center_x, center_y)
        radius = center.distance_to(p1)
        return cls(center, radius)

    @property
    def area(self) -> float:
        """Get circle area"""
        return math.pi * self.radius * self.radius

    @property
    def circumference(self) -> float:
        """Get circle circumference"""
        return 2 * math.pi * self.radius

    @property
    def bounding_box(self) -> 'Rectangle':
        """Get the bounding box of the circle"""
        return Rectangle(
            Point2D(self.center.x - self.radius, self.center.y - self.radius),
            Point2D(self.center.x + self.radius, self.center.y + self.radius)
        )

    def contains_point(self, point: Union[Point2D, Vector2, Tuple[float, float]]) -> bool:
        """Check if point is inside circle"""
        return self.center.distance_to(point) <= self.radius

    def intersects_circle(self, other: 'Circle') -> bool:
        """Check if this circle intersects with another circle"""
        return self.center.distance_to(other.center) <= self.radius + other.radius

    def get_point_on_circumference(self, angle_rad: float) -> Point2D:
        """Get point on circle's circumference at given angle"""
        return Point2D(
            self.center.x + self.radius * math.cos(angle_rad),
            self.center.y + self.radius * math.sin(angle_rad)
        )

    def get_points_on_circumference(self, num_points: int) -> List[Point2D]:
        """Get evenly distributed points on circle's circumference"""
        points = []
        for i in range(num_points):
            angle = (2 * math.pi * i) / num_points
            points.append(self.get_point_on_circumference(angle))
        return points

    def get_tangent_points(self, point: Point2D) -> Optional[Tuple[Point2D, Point2D]]:
        """Get tangent points from external point to circle"""
        if self.contains_point(point):
            return None
        
        dist = self.center.distance_to(point)
        if dist < self.radius:
            return None
            
        # Calculate angle between tangent lines
        angle = math.acos(self.radius / dist)
        
        # Calculate base angle to point
        base_angle = math.atan2(point.y - self.center.y, point.x - self.center.x)
        
        # Calculate tangent points
        return (
            self.get_point_on_circumference(base_angle + angle),
            self.get_point_on_circumference(base_angle - angle)
        )

    def scale(self, factor: float) -> 'Circle':
        """Return new circle scaled by given factor"""
        return Circle(self.center, self.radius * factor)

    def project_point(self, point: Point2D) -> Point2D:
        """Project point onto circle's circumference"""
        if point == self.center:
            return self.get_point_on_circumference(0)
            
        vector = point - self.center
        normalized = vector.normalized()
        return Point2D.from_vector2(self.center.to_vector2() + normalized * self.radius)

    def __str__(self) -> str:
        return f"Circle(center={self.center}, radius={self.radius:.3f})"

@dataclass
class Rectangle:
    min_point: Vector2  # Top-left corner
    max_point: Vector2  # Bottom-right corner

    @property
    def corners(self) -> List[Vector2]:
        """Get rectangle corners in clockwise order: top-left, top-right, bottom-right, bottom-left"""
        return [
            self.min_point,  # Top-left
            Vector2(self.max_point.x, self.min_point.y),  # Top-right
            self.max_point,  # Bottom-right
            Vector2(self.min_point.x, self.max_point.y)   # Bottom-left
        ]
    
    @property
    def edges(self) -> List[Tuple[Vector2, Vector2]]:
        """Get rectangle edges as pairs of points in clockwise order"""
        corners = self.corners
        return [
            (corners[i], corners[(i + 1) % 4]) 
            for i in range(4)
        ]
    
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
    def size(self) -> Vector2:
        """Get rectangle size as a vector"""
        return Vector2(self.width, self.height)
    
    @property
    def area(self) -> float:
        """Get rectangle area"""
        return self.width * self.height
    
    @property
    def perimeter(self) -> float:
        """Get rectangle perimeter"""
        return 2 * (self.width + self.height)

    @classmethod
    def from_center(cls, center: Vector2, width: float, height: float) -> 'Rectangle':
        """Create rectangle from center point and dimensions"""
        half_width = width * 0.5
        half_height = height * 0.5
        return cls(
            Vector2(center.x - half_width, center.y - half_height),
            Vector2(center.x + half_width, center.y + half_height)
        )
    
    @classmethod
    def from_points(cls, points: List[Vector2]) -> 'Rectangle':
        """Create minimum rectangle that contains all given points"""
        if not points:
            raise ValueError("Cannot create rectangle from empty point list")
        
        min_x = min(p.x for p in points)
        min_y = min(p.y for p in points)
        max_x = max(p.x for p in points)
        max_y = max(p.y for p in points)
        
        return cls(Vector2(min_x, min_y), Vector2(max_x, max_y))

    def contains_point(self, point: Vector2) -> bool:
        """Check if point is inside rectangle"""
        return (self.min_point.x <= point.x <= self.max_point.x and
                self.min_point.y <= point.y <= self.max_point.y)

    def contains_rect(self, other: 'Rectangle') -> bool:
        """Check if this rectangle completely contains another rectangle"""
        return (self.min_point.x <= other.min_point.x and
                self.min_point.y <= other.min_point.y and
                self.max_point.x >= other.max_point.x and
                self.max_point.y >= other.max_point.y)

    def expand(self, margin: float) -> 'Rectangle':
        """Return new rectangle expanded by margin in all directions"""
        return Rectangle(
            self.min_point - Vector2(margin, margin),
            self.max_point + Vector2(margin, margin)
        )
    
    def scale(self, scale: float) -> 'Rectangle':
        """Return new rectangle scaled from center by given factor"""
        center = self.center
        half_size = self.size * (scale * 0.5)
        return Rectangle(
            center - half_size,
            center + half_size
        )

@dataclass
class Triangle:
    a: Vector2
    b: Vector2
    c: Vector2

    def area(self) -> float:
        return abs((self.b - self.a).cross(self.c - self.a)) * 0.5

    def contains_point(self, point: Vector2) -> bool:
        # Using barycentric coordinates
        v0 = self.c - self.a
        v1 = self.b - self.a
        v2 = point - self.a

        dot00 = v0.dot(v0)
        dot01 = v0.dot(v1)
        dot02 = v0.dot(v2)
        dot11 = v1.dot(v1)
        dot12 = v1.dot(v2)

        inv_denom = 1.0 / (dot00 * dot11 - dot01 * dot01)
        u = (dot11 * dot02 - dot01 * dot12) * inv_denom
        v = (dot00 * dot12 - dot01 * dot02) * inv_denom

        return u >= 0 and v >= 0 and u + v <= 1

@dataclass
class Polygon:
    points: List[Vector2]

    def contains_point(self, point: Vector2) -> bool:
        """Ray casting algorithm for point in polygon test"""
        inside = False
        j = len(self.points) - 1

        for i in range(len(self.points)):
            if ((self.points[i].y > point.y) != (self.points[j].y > point.y) and
                point.x < (self.points[j].x - self.points[i].x) * 
                (point.y - self.points[i].y) / 
                (self.points[j].y - self.points[i].y) + self.points[i].x):
                inside = not inside
            j = i

        return inside
