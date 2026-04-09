from math import acos, degrees, sqrt
import numpy as np


def dotproduct(v1: tuple[float, float], v2: tuple[float, float]) -> float:
    """ Get the dot product of the two vectors. """
    return sum((a*b) for a, b in zip(v1, v2))

def length(v: tuple[float, float]) -> float:
    """ Get the length of the vector. """
    return sqrt(dotproduct(v, v))

def angle_v2v2(v1: tuple[float, float], v2: tuple[float, float], as_degrees: bool = True) -> float:
    """ Get the angle between the two vectors. """
    a = acos(dotproduct(v1, v2) / (length(v1) * length(v2)))
    return degrees(a) if as_degrees else a

def angle_v3v3(v1: np.ndarray, v2: np.ndarray, as_degrees: bool = False) -> float:
    """ Returns the angle in radians between given 3D vectors"""
    a = np.arccos(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))
    return degrees(a) if as_degrees else a

def unit_vector(vector: np.ndarray) -> np.ndarray:
    """ Returns the unit vector of the vector"""
    return vector / np.linalg.norm(vector)

def angle_signed(vector1: np.ndarray, vector2: np.ndarray, as_degrees: bool = False) -> float:
    """ Returns the angle in radians between given vectors"""
    v1_u = unit_vector(vector1)
    v2_u = unit_vector(vector2)
    minor = np.linalg.det(
        np.stack((v1_u[-2:], v2_u[-2:]))
    )
    if minor == 0:
        return 0
        raise NotImplementedError('Too odd vectors =(')
    ang_rad = np.sign(minor) * np.arccos(np.clip(np.dot(v1_u, v2_u), -1.0, 1.0))
    return degrees(ang_rad) if as_degrees else ang_rad

def normalize(v):
    return v / np.linalg.norm(v)
