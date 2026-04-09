

from typing import Literal


GPU_TYPES = Literal['FLOAT', 'VEC2', 'VEC3', 'VEC4', 'MAT3', 'MAT4', 'UINT', 'UVEC2', 'UVEC3', 'UVEC4', 'INT', 'IVEC2', 'IVEC3', 'IVEC4', 'BOOL']
PRIMITIVE_TYPES = Literal['ALL', 'TRIS', 'LINES', 'POINTS']


class UniformType:
    INT = "INT"
    FLOAT = "FLOAT"
    VEC2 = "VEC2"
    VEC3 = "VEC3"
    VEC4 = "VEC4"
    MAT3 = "MAT3"
    MAT4 = "MAT4"
    UINT = "UINT"
    UVEC2 = "UVEC2"
    UVEC3 = "UVEC3"
    UVEC4 = "UVEC4"
    IVEC2 = "IVEC2"
    IVEC3 = "IVEC3"
    IVEC4 = "IVEC4"
    BOOL = "BOOL"
    SAMPLER = "SAMPLER"


def _uniformtype_to_pytype(uniform_type: str) -> str:
    table = {
        UniformType.FLOAT: "float",
        UniformType.INT: "int",
        UniformType.UINT: "int",
        UniformType.BOOL: "bool",
        UniformType.VEC2: "tuple[float, float]",
        UniformType.VEC3: "tuple[float, float, float]",
        UniformType.VEC4: "tuple[float, float, float, float]",
        UniformType.MAT3: "Any",
        UniformType.MAT4: "Any",
        UniformType.SAMPLER: "GPUTexture",
    }
    return table.get(uniform_type, "Any")
