from math import exp, sqrt
from enum import Enum


class FalloffType(Enum):
    GAUSSIAN = 'GAUSSIAN'
    SMOOTH = 'SMOOTH'
    LINEAR = 'LINEAR'
    SHARP = 'SHARP'
    ROOT = 'ROOT'
    INVERSE_SMOOTH = 'INVERSE_SMOOTH'

    def __call__(self, t: float) -> float:
        return self.evaluate(t)

    def evaluate(self, t: float) -> float:
        """
        t in [0..1] → distance ratio
        returns weight in [0..1]
        """

        t = max(0.0, min(1.0, t))

        match self:
            case FalloffType.GAUSSIAN:
                return exp(-(t * t) * 4.0)

            case FalloffType.SMOOTH:
                return 1.0 - (3.0 - 2.0 * t) * t * t  # smoothstep inverted

            case FalloffType.LINEAR:
                return 1.0 - t

            case FalloffType.SHARP:
                return (1.0 - t) ** 3

            case FalloffType.ROOT:
                return 1.0 - sqrt(t)

            case FalloffType.INVERSE_SMOOTH:
                return (3.0 - 2.0 * t) * t * t

        return 1.0
