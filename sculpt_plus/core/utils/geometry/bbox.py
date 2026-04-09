

from mathutils import Vector


class BBox:

    @classmethod
    def from_pos_size(cls, pos: tuple[float, ...], size: tuple[float, ...]) -> 'BBox':
        pos = Vector(pos)
        return cls(pos, pos + Vector(size))

    def __init__(self, min: Vector, max: Vector):
        self.min = min if isinstance(min, Vector) else Vector(min)
        self.max = max if isinstance(max, Vector) else Vector(max)

    def contains(self, p: Vector) -> bool:
        if len(p) != len(self.min):
            raise ValueError(f"Invalid vector length: {len(p)}")
        for min_comp, p_comp, max_comp in zip(self.min, p, self.max):
            if p_comp <= min_comp or p_comp >= max_comp:
                return False
        return True

    def expanded_uniform(self, amount: float) -> 'BBox':
        return BBox(
            self.min - Vector((amount, amount, amount)),
            self.max + Vector((amount, amount, amount)),
        )
