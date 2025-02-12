from typing import Tuple, Union

Number = Union[float, int]

def clamp(value: Number, min_value: Number = 0.0, max_value: Number = 1.0) -> Number:
    return min(max(value, min_value), max_value)

def map_value(val: float, src: Tuple[float, float], dst: Tuple[float, float] = (0.0, 1.0)) -> float:
    """Scale the given value from the scale of src to the scale of dst."""
    return ((val - src[0]) / (src[1]-src[0])) * (dst[1]-dst[0]) + dst[0]