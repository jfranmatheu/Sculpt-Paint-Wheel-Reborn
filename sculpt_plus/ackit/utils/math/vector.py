import math
from typing import Union, Tuple
from enum import Enum


class VectorDirection(Enum):
    UP = (0, 1)
    DOWN = (0, -1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)
    ZERO = (0, 0)


class Vector2:
    """2D Vector with float components"""
    x: float = 0.0
    y: float = 0.0

    @classmethod
    def from_tuple(cls, tup: Tuple[float, float]) -> 'Vector2':
        return cls(tup[0], tup[1])
    
    @classmethod
    def from_direction(cls, direction: VectorDirection) -> 'Vector2':
        return cls(*direction.value)

    @classmethod
    def zero(cls) -> 'Vector2':
        return cls(0.0, 0.0)
    
    @classmethod
    def one(cls) -> 'Vector2':
        return cls(1.0, 1.0)

    def __init__(self, x: float = 0, y: float = 0):
        self.x = x
        self.y = y

    def reset(self) -> None:
        self.x = 0.0
        self.y = 0.0

    def __set__(self, instance, values: Tuple[float, float] | Tuple[int, int]):
        if not isinstance(values, (Tuple[float, float], Tuple[int, int])):
            raise TypeError('Only objects of type Tuple[float, float] and Tuple[int, int] can be assigned')
        self.x, self.y = values  # This can be self.val = MyCustomClass(val) as well.

    def copy(self) -> 'Vector2':
        return Vector2(self.x, self.y)

    def to_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)
    
    def to_int_tuple(self) -> Tuple[int, int]:
        return (int(self.x), int(self.y))
    
    def to_vector2i(self) -> 'Vector2i':
        return Vector2i(int(self.x), int(self.y))

    # Basic vector operations
    def dot(self, other: 'Vector2') -> float:
        """Compute dot product"""
        return self.x * other.x + self.y * other.y

    def cross(self, other: 'Vector2') -> float:
        """Compute cross product (z component only for 2D vectors)"""
        return self.x * other.y - self.y * other.x

    def length(self) -> float:
        """Get vector magnitude"""
        return math.sqrt(self.length_squared())

    def length_squared(self) -> float:
        """Get squared vector magnitude (faster than length)"""
        return self.x * self.x + self.y * self.y

    def normalize(self) -> 'Vector2':
        """Normalize vector in place"""
        length = self.length()
        if length != 0:
            self.x /= length
            self.y /= length
        return self

    def normalized(self) -> 'Vector2':
        """Return normalized copy of vector"""
        return self.copy().normalize()

    def distance_to(self, other: 'Vector2') -> float:
        """Calculate distance to another vector"""
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

    def distance_squared_to(self, other: 'Vector2') -> float:
        """Calculate squared distance to another vector (faster than distance)"""
        return (self.x - other.x)**2 + (self.y - other.y)**2

    def angle_to(self, other: 'Vector2') -> float:
        """Calculate angle to another vector in radians"""
        return math.atan2(self.cross(other), self.dot(other))

    def rotate(self, angle: float) -> 'Vector2':
        """Rotate vector by angle (in radians) in place"""
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        x = self.x * cos_a - self.y * sin_a
        y = self.x * sin_a + self.y * cos_a
        self.x = x
        self.y = y
        return self

    def rotated(self, angle: float) -> 'Vector2':
        """Return rotated copy of vector"""
        return self.copy().rotate(angle)

    def lerp(self, other: 'Vector2', t: float) -> 'Vector2':
        """Linear interpolation between vectors"""
        self.x = self.x + (other.x - self.x) * t
        self.y = self.y + (other.y - self.y) * t
        return self

    def reflect(self, normal: 'Vector2') -> 'Vector2':
        """Reflect vector around normal"""
        normal = normal.normalized()
        dot = self.dot(normal)
        self.x -= 2 * dot * normal.x
        self.y -= 2 * dot * normal.y
        return self

    def is_zero(self, tolerance: float = 1e-6) -> bool:
        """Check if vector is zero within tolerance"""
        return abs(self.x) < tolerance and abs(self.y) < tolerance

    @staticmethod
    def _convert_to_vector2(value: 'Vector2') -> 'Vector2':
        """Convert various input types to Vector2"""
        if isinstance(value, Vector2):
            return value
        elif isinstance(value, tuple):
            return Vector2(*value)
        raise TypeError(f"Cannot convert {type(value)} to Vector2")

    # Operator overloads
    def __add__(self, other: 'Vector2') -> 'Vector2':
        other = self._convert_to_vector2(other)
        return Vector2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: 'Vector2') -> 'Vector2':
        other = self._convert_to_vector2(other)
        return Vector2(self.x - other.x, self.y - other.y)

    def __mul__(self, other: 'Vector2') -> 'Vector2':
        return Vector2(self.x * other.x, self.y * other.y)

    def __truediv__(self, other: 'Vector2') -> 'Vector2':
        return Vector2(self.x / other.x, self.y / other.y)

    def __iadd__(self, other: 'Vector2') -> 'Vector2':
        other = self._convert_to_vector2(other)
        self.x += other.x
        self.y += other.y
        return self

    def __isub__(self, other: 'Vector2') -> 'Vector2':
        other = self._convert_to_vector2(other)
        self.x -= other.x
        self.y -= other.y
        return self

    def __imul__(self, other: 'Vector2') -> 'Vector2':
        return Vector2(self.x * other.x, self.y * other.y)

    def __itruediv__(self, other: 'Vector2') -> 'Vector2':
        return Vector2(self.x / other.x, self.y / other.y)

    def __neg__(self) -> 'Vector2':
        return Vector2(-self.x, -self.y)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, (Vector2, tuple)):
            return NotImplemented
        other = self._convert_to_vector2(other)
        return self.x == other.x and self.y == other.y

    def __str__(self) -> str:
        return f"Vector2(x={self.x:.3f}, y={self.y:.3f})"

    def __repr__(self) -> str:
        return f"Vector2({self.x}, {self.y})"


class Vector2i:
    """2D Vector with integer components"""
    x: int = 0
    y: int = 0

    @classmethod
    def from_tuple(cls, tup: Tuple[float, float]) -> 'Vector2i':
        return cls(int(tup[0]), int(tup[1]))
    
    @classmethod
    def from_direction(cls, direction: VectorDirection) -> 'Vector2i':
        return cls(*direction.value)

    @classmethod
    def zero(cls) -> 'Vector2i':
        return cls(0, 0)
    
    @classmethod
    def one(cls) -> 'Vector2i':
        return cls(1, 1)

    def __init__(self, x: int = 0, y: int = 0):
        self.x = x
        self.y = y

    def reset(self) -> None:
        self.x = 0
        self.y = 0

    def __set__(self, instance, values: Tuple[int, int] | 'Vector2i'):
        if isinstance(values, Vector2i):
            values = values.x, values.y
        elif not isinstance(values, (Tuple[int, int])):
            raise TypeError('Only objects of type Tuple[int, int] can be assigned')
        self.x, self.y = values  # This can be self.val = MyCustomClass(val) as well.

    def is_zero(self) -> bool:
        """Check if vector is zero"""
        return self.x == 0 and self.y == 0

    def copy(self) -> 'Vector2i':
        return Vector2i(self.x, self.y)

    def to_tuple(self) -> Tuple[int, int]:
        return self.x, self.y
    
    def to_vector2(self) -> Vector2:
        return Vector2(float(self.x), float(self.y))

    def length(self) -> float:
        """Get vector magnitude"""
        return math.sqrt(self.length_squared())

    def length_squared(self) -> int:
        """Get squared vector magnitude"""
        return self.x * self.x + self.y * self.y

    def distance_to(self, other: 'Vector2') -> float:
        """Calculate distance to another vector"""
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

    def manhattan_distance(self, other: 'Vector2') -> int:
        """Calculate Manhattan distance to another vector"""
        return abs(self.x - other.x) + abs(self.y - other.y)

    @staticmethod
    def _convert_to_vector2i(value: 'Vector2') -> 'Vector2i':
        """Convert various input types to Vector2i"""
        if isinstance(value, Vector2):
            return Vector2i(int(value.x), int(value.y))
        elif isinstance(value, tuple):
            return Vector2i(*value)
        raise TypeError(f"Cannot convert {type(value)} to Vector2i")

    # Operator overloads similar to Vector2 but maintaining integer types
    def __add__(self, other: 'Vector2') -> 'Vector2i':
        other = self._convert_to_vector2i(other)
        return Vector2i(self.x + other.x, self.y + other.y)

    def __sub__(self, other: 'Vector2') -> 'Vector2i':
        other = self._convert_to_vector2i(other)
        return Vector2i(self.x - other.x, self.y - other.y)

    def __mul__(self, other: 'Vector2') -> 'Vector2i':
        return Vector2i(self.x * other.x, self.y * other.y)

    def __floordiv__(self, other: 'Vector2') -> 'Vector2i':
        return Vector2i(self.x // other.x, self.y // other.y)

    def __iadd__(self, other: 'Vector2') -> 'Vector2i':
        other = self._convert_to_vector2i(other)
        self.x += other.x
        self.y += other.y
        return self

    def __isub__(self, other: 'Vector2') -> 'Vector2i':
        other = self._convert_to_vector2i(other)
        self.x -= other.x
        self.y -= other.y
        return self

    def __imul__(self, other: 'Vector2') -> 'Vector2i':
        return Vector2i(self.x * other.x, self.y * other.y)

    def __ifloordiv__(self, other: 'Vector2') -> 'Vector2i':
        return Vector2i(self.x // other.x, self.y // other.y)

    def __neg__(self) -> 'Vector2i':
        return Vector2i(-self.x, -self.y)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, (Vector2, Vector2i, tuple)):
            return NotImplemented
        other = self._convert_to_vector2i(other)
        return self.x == other.x and self.y == other.y

    def __str__(self) -> str:
        return f"Vector2i(x={self.x}, y={self.y})"

    def __repr__(self) -> str:
        return f"Vector2i({self.x}, {self.y})"


class Vector3:
    """3D Vector with float components"""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    @classmethod
    def from_tuple(cls, tup: Tuple[float, float, float]) -> 'Vector3':
        return cls(tup[0], tup[1], tup[2])

    @classmethod
    def zero(cls) -> 'Vector3':
        return cls(0.0, 0.0, 0.0)
    
    @classmethod
    def one(cls) -> 'Vector3':
        return cls(1.0, 1.0, 1.0)
    
    @classmethod
    def up(cls) -> 'Vector3':
        return cls(0.0, 1.0, 0.0)
    
    @classmethod
    def down(cls) -> 'Vector3':
        return cls(0.0, -1.0, 0.0)
    
    @classmethod
    def right(cls) -> 'Vector3':
        return cls(1.0, 0.0, 0.0)
    
    @classmethod
    def left(cls) -> 'Vector3':
        return cls(-1.0, 0.0, 0.0)
    
    @classmethod
    def forward(cls) -> 'Vector3':
        return cls(0.0, 0.0, 1.0)
    
    @classmethod
    def back(cls) -> 'Vector3':
        return cls(0.0, 0.0, -1.0)

    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)

    def reset(self) -> None:
        self.x = 0.0
        self.y = 0.0
        self.z = 0.0

    def copy(self) -> 'Vector3':
        return Vector3(self.x, self.y, self.z)

    def to_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)
    
    def to_int_tuple(self) -> Tuple[int, int, int]:
        return (int(self.x), int(self.y), int(self.z))

    # Vector operations
    def dot(self, other: 'Vector3') -> float:
        """Compute dot product"""
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: 'Vector3') -> 'Vector3':
        """Compute cross product"""
        return Vector3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x
        )

    def length(self) -> float:
        """Get vector magnitude"""
        return math.sqrt(self.length_squared())

    def length_squared(self) -> float:
        """Get squared vector magnitude (faster than length)"""
        return self.x * self.x + self.y * self.y + self.z * self.z

    def normalize(self) -> 'Vector3':
        """Normalize vector in place"""
        length = self.length()
        if length != 0:
            self.x /= length
            self.y /= length
            self.z /= length
        return self

    def normalized(self) -> 'Vector3':
        """Return normalized copy of vector"""
        return self.copy().normalize()

    def distance_to(self, other: 'Vector3') -> float:
        """Calculate distance to another vector"""
        return math.sqrt(self.distance_squared_to(other))

    def distance_squared_to(self, other: 'Vector3') -> float:
        """Calculate squared distance to another vector (faster than distance)"""
        return ((self.x - other.x) ** 2 + 
                (self.y - other.y) ** 2 + 
                (self.z - other.z) ** 2)

    def angle_to(self, other: 'Vector3') -> float:
        """Calculate angle to another vector in radians"""
        dot = self.dot(other)
        lengths = self.length() * other.length()
        if lengths == 0:
            return 0.0
        return math.acos(max(-1.0, min(1.0, dot / lengths)))

    def rotate_around_axis(self, axis: 'Vector3', angle: float) -> 'Vector3':
        """Rotate vector around axis by angle (in radians) using Rodrigues' rotation formula"""
        axis = axis.normalized()
        cos_angle = math.cos(angle)
        sin_angle = math.sin(angle)
        dot = self.dot(axis)
        
        self.x = (self.x * cos_angle + 
                 (axis.y * self.z - axis.z * self.y) * sin_angle + 
                 axis.x * dot * (1 - cos_angle))
        
        self.y = (self.y * cos_angle + 
                 (axis.z * self.x - axis.x * self.z) * sin_angle + 
                 axis.y * dot * (1 - cos_angle))
        
        self.z = (self.z * cos_angle + 
                 (axis.x * self.y - axis.y * self.x) * sin_angle + 
                 axis.z * dot * (1 - cos_angle))
        
        return self

    def lerp(self, other: 'Vector3', t: float) -> 'Vector3':
        """Linear interpolation between vectors"""
        self.x = self.x + (other.x - self.x) * t
        self.y = self.y + (other.y - self.y) * t
        self.z = self.z + (other.z - self.z) * t
        return self

    def reflect(self, normal: 'Vector3') -> 'Vector3':
        """Reflect vector around normal"""
        normal = normal.normalized()
        dot = self.dot(normal)
        self.x -= 2 * dot * normal.x
        self.y -= 2 * dot * normal.y
        self.z -= 2 * dot * normal.z
        return self

    def project_onto(self, other: 'Vector3') -> 'Vector3':
        """Project this vector onto another vector"""
        other_normalized = other.normalized()
        dot = self.dot(other_normalized)
        return other_normalized * dot

    def is_zero(self, tolerance: float = 1e-6) -> bool:
        """Check if vector is zero within tolerance"""
        return (abs(self.x) < tolerance and 
                abs(self.y) < tolerance and 
                abs(self.z) < tolerance)

    # Operator overloads
    def __add__(self, other: 'Vector3') -> 'Vector3':
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: 'Vector3') -> 'Vector3':
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, other: Union[float, 'Vector3']) -> 'Vector3':
        if isinstance(other, (int, float)):
            return Vector3(self.x * other, self.y * other, self.z * other)
        return Vector3(self.x * other.x, self.y * other.y, self.z * other.z)

    def __truediv__(self, other: Union[float, 'Vector3']) -> 'Vector3':
        if isinstance(other, (int, float)):
            if other == 0:
                raise ZeroDivisionError("Division by zero")
            return Vector3(self.x / other, self.y / other, self.z / other)
        if other.x == 0 or other.y == 0 or other.z == 0:
            raise ZeroDivisionError("Division by zero")
        return Vector3(self.x / other.x, self.y / other.y, self.z / other.z)

    def __iadd__(self, other: 'Vector3') -> 'Vector3':
        self.x += other.x
        self.y += other.y
        self.z += other.z
        return self

    def __isub__(self, other: 'Vector3') -> 'Vector3':
        self.x -= other.x
        self.y -= other.y
        self.z -= other.z
        return self

    def __imul__(self, other: Union[float, 'Vector3']) -> 'Vector3':
        if isinstance(other, (int, float)):
            self.x *= other
            self.y *= other
            self.z *= other
        else:
            self.x *= other.x
            self.y *= other.y
            self.z *= other.z
        return self

    def __itruediv__(self, other: Union[float, 'Vector3']) -> 'Vector3':
        if isinstance(other, (int, float)):
            if other == 0:
                raise ZeroDivisionError("Division by zero")
            self.x /= other
            self.y /= other
            self.z /= other
        else:
            if other.x == 0 or other.y == 0 or other.z == 0:
                raise ZeroDivisionError("Division by zero")
            self.x /= other.x
            self.y /= other.y
            self.z /= other.z
        return self

    def __neg__(self) -> 'Vector3':
        return Vector3(-self.x, -self.y, -self.z)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Vector3):
            return NotImplemented
        return self.x == other.x and self.y == other.y and self.z == other.z

    def __str__(self) -> str:
        return f"Vector3(x={self.x:.3f}, y={self.y:.3f}, z={self.z:.3f})"

    def __repr__(self) -> str:
        return f"Vector3({self.x}, {self.y}, {self.z})"
