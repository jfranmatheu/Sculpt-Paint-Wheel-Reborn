import importlib
import os
import sys
from pathlib import Path
from bmesh.types import BMFace, BMesh
from mathutils import Vector
from ...globals import PATHS

Geometry = None
Polygon = None
MultiPolygon = None
unary_union = None
_shapely_ready = False
_dll_dirs = []

'''def _ensure_shapely_paths():
    py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
    candidates = [
        PATHS.ROOT / "python" / "lib" / py_ver / "site-packages",
        PATHS.ROOT / "python" / "lib" / "site-packages",
    ]
    for p in candidates:
        if p.exists() and str(p) not in sys.path:
            sys.path.append(str(p))'''

def _load_shapely():
    global Geometry, Polygon, MultiPolygon, unary_union, _shapely_ready
    if _shapely_ready:
        return True
    try:
        from shapely import Geometry as _Geometry
        from shapely.geometry import Polygon as _Polygon, MultiPolygon as _MultiPolygon
        from shapely.ops import unary_union as _unary_union
        Geometry = _Geometry
        Polygon = _Polygon
        MultiPolygon = _MultiPolygon
        unary_union = _unary_union
        _shapely_ready = True
        return True
    except Exception:
        pass
    #_ensure_shapely_paths()
    libs = []
    for p in list(dict.fromkeys(sys.path)):
        try:
            base = Path(p)
        except Exception:
            continue
        libs_dir = base / "shapely.libs"
        if libs_dir.exists():
            libs.append(libs_dir)
    if os.name == "nt":
        for libs_dir in libs:
            if str(libs_dir) not in _dll_dirs:
                os.add_dll_directory(str(libs_dir))
                _dll_dirs.append(str(libs_dir))
    try:
        mod = importlib.import_module("shapely")
        Geometry = getattr(mod, "Geometry", None)
        geom = importlib.import_module("shapely.geometry")
        ops = importlib.import_module("shapely.ops")
        Polygon = getattr(geom, "Polygon", None)
        MultiPolygon = getattr(geom, "MultiPolygon", None)
        unary_union = getattr(ops, "unary_union", None)
        _shapely_ready = True
        return True
    except Exception:
        return False

def _require_shapely():
    if not _load_shapely():
        raise ImportError("shapely is not available")


# Convertir Vectors -> shapely Polygon
def vectors_to_polygon(vectors):
    _require_shapely()
    return Polygon([(v.x, v.y) for v in vectors])

# Convertir resultado -> listas de Vectors
def polygon_to_vectors(poly):
    return [Vector((x, y, 0.0)) for x, y in poly.exterior.coords[:-1]]


def boolean_2d_vectors(poly_a: list[Vector], poly_b: list[Vector], operation="union"):
    """
    Realiza operaciones booleanas 2D entre dos polígonos definidos
    por listas de mathutils.Vector (solo X,Y).

    operation: "union", "intersection", "difference", "symmetric_difference"
    return: lista(s) de listas de Vector
    """
    _require_shapely()
    shapely_a = vectors_to_polygon(poly_a)
    shapely_b = vectors_to_polygon(poly_b)

    if not shapely_a.is_valid or not shapely_b.is_valid:
        raise ValueError("Uno de los polígonos no es válido")

    # Operación booleana
    if operation == "union":
        result = shapely_a.union(shapely_b)
    elif operation == "intersection":
        result = shapely_a.intersection(shapely_b)
    elif operation == "difference":
        result = shapely_a.difference(shapely_b)
    elif operation == "symmetric_difference":
        result = shapely_a.symmetric_difference(shapely_b)
    else:
        raise ValueError(f"Operación no soportada: {operation}")

    # Puede devolver Polygon o MultiPolygon
    if isinstance(result, Polygon):
        return [polygon_to_vectors(result)]

    elif isinstance(result, MultiPolygon):
        return [polygon_to_vectors(p) for p in result.geoms]

    else:
        return []


def plane_basis_from_normal(normal):
    normal = normal.normalized()

    if abs(normal.z) < 0.999:
        tangent = Vector((0, 0, 1))
    else:
        tangent = Vector((0, 1, 0))

    u = normal.cross(tangent).normalized()
    v = normal.cross(u).normalized()

    return u, v


def boolean_2d_vectors_multi(polys: list[list[Vector]], operation="union"):
    """
    Realiza operaciones booleanas 2D entre múltiples polígonos definidos
    por listas de mathutils.Vector (solo X,Y).

    operation: "union", "intersection", "difference", "symmetric_difference"
    return: lista(s) de listas de Vector
    """
    _require_shapely()
    # Convertir polígonos a shapely
    shapely_polys = [vectors_to_polygon(poly) for poly in polys]

    # Operación booleana
    if operation == "union":
        result = shapely_polys[0].union(shapely_polys[1:])
    elif operation == "intersection":
        result = shapely_polys[0].intersection(shapely_polys[1:])
    elif operation == "difference":
        result = shapely_polys[0].difference(shapely_polys[1:])
    elif operation == "symmetric_difference":
        result = shapely_polys[0].symmetric_difference(shapely_polys[1:])
    else:
        raise ValueError(f"Operación no soportada: {operation}")

    # Puede devolver Polygon o MultiPolygon
    if isinstance(result, Polygon):
        return [polygon_to_vectors(result)]

    elif isinstance(result, MultiPolygon):
        return [polygon_to_vectors(p) for p in result.geoms]

    else:
        return []


def bmface_to_shapely_polygon(
    face,
    matrix=None,
    plane='XY',
    plane_origin=None,
    plane_normal=None
):
    _require_shapely()
    """
    plane: 'XY', 'XZ', 'YZ', 'CUSTOM'
    plane_origin: Vector (solo si plane='CUSTOM')
    plane_normal: Vector (solo si plane='CUSTOM')
    """

    coords_2d = []

    # Precalcular base del plano custom
    if plane == 'CUSTOM':
        if plane_origin is None or plane_normal is None:
            raise ValueError("CUSTOM requiere plane_origin y plane_normal")

        plane_origin = Vector(plane_origin)
        u, v = plane_basis_from_normal(Vector(plane_normal))

    for loop in face.loops:
        p = loop.vert.co

        if matrix:
            p = matrix @ p

        if plane == 'XY':
            coords_2d.append((p.x, p.y))

        elif plane == 'XZ':
            coords_2d.append((p.x, p.z))

        elif plane == 'YZ':
            coords_2d.append((p.y, p.z))

        elif plane == 'CUSTOM':
            # Proyección al plano
            vec = p - plane_origin
            coords_2d.append((
                vec.dot(u),
                vec.dot(v)
            ))

        else:
            raise ValueError(f"Plano no soportado: {plane}")

    poly = Polygon(coords_2d)

    # Limpieza defensiva
    if not poly.is_valid:
        poly = poly.buffer(0)

    return poly


def bmverts_boundary_to_shapely_polygon(
    bmverts,
    matrix=None,
    plane='XY',
    plane_origin=None,
    plane_normal=None
):
    _require_shapely()
    """
    bmverts: lista ordenada de BMVert (boundary)
    plane: 'XY', 'XZ', 'YZ', 'CUSTOM'
    """

    if len(bmverts) < 3:
        raise ValueError("Un polígono necesita al menos 3 vértices")

    coords_2d = []

    # Plano custom
    if plane == 'CUSTOM':
        if plane_origin is None or plane_normal is None:
            raise ValueError("CUSTOM requiere plane_origin y plane_normal")

        plane_origin = Vector(plane_origin)
        u, v = plane_basis_from_normal(Vector(plane_normal))

    for vtx in bmverts:
        p = vtx.co

        if matrix:
            p = matrix @ p

        if plane == 'XY':
            coords_2d.append((p.x, p.y))

        elif plane == 'XZ':
            coords_2d.append((p.x, p.z))

        elif plane == 'YZ':
            coords_2d.append((p.y, p.z))

        elif plane == 'CUSTOM':
            vec = p - plane_origin
            coords_2d.append((
                vec.dot(u),
                vec.dot(v)
            ))

        else:
            raise ValueError(f"Plano no soportado: {plane}")

    poly = Polygon(coords_2d)

    # Limpieza defensiva
    if not poly.is_valid:
        poly = poly.buffer(0)

    return poly


def bmesh_faces_to_shapely(bm: BMesh, matrix=None):
    _require_shapely()
    polys = []

    for face in bm.faces:
        poly = bmface_to_shapely_polygon(face, matrix)
        if not poly.is_empty:
            polys.append(poly)

    return polys


def union_bmesh_faces(bm, matrix=None):
    _require_shapely()
    polys = bmesh_faces_to_shapely(bm, matrix)
    return unary_union(polys)


def shapely_to_vectors(geom: Geometry) -> list[list[Vector]]:
    """
    Devuelve listas de Vectors listas para crear caras nuevas
    """
    _require_shapely()
    def poly_to_vectors(poly):
        return [Vector((x, y, 0.0)) for x, y in poly.exterior.coords[:-1]]

    if isinstance(geom, Polygon):
        return [poly_to_vectors(geom)]

    elif isinstance(geom, MultiPolygon):
        return [poly_to_vectors(p) for p in geom.geoms]

    return []


def union_bmvert_boundaries_2d(
    boundaries,
    matrix=None,
    plane='XY',
    plane_origin=None,
    plane_normal=None,
    unproject=False
):
    _require_shapely()
    """
    boundaries: List[List[BMVert]]
    plane: 'XY', 'XZ', 'YZ', 'CUSTOM'
    unproject: si True, devuelve puntos 3D en el plano original
    """

    if len(boundaries) < 2:
        raise ValueError("Se requieren al menos 2 boundaries")

    shapely_polys = []

    # Base del plano
    if plane == 'CUSTOM':
        if plane_origin is None or plane_normal is None:
            raise ValueError("CUSTOM requiere plane_origin y plane_normal")

        plane_origin = Vector(plane_origin)
        u, v = plane_basis_from_normal(Vector(plane_normal))

    for bmverts in boundaries:
        if len(bmverts) < 3:
            continue

        coords_2d = []

        for vtx in bmverts:
            p = vtx.co
            if matrix:
                p = matrix @ p

            if plane == 'XY':
                coords_2d.append((p.x, p.y))
            elif plane == 'XZ':
                coords_2d.append((p.x, p.z))
            elif plane == 'YZ':
                coords_2d.append((p.y, p.z))
            elif plane == 'CUSTOM':
                vec = p - plane_origin
                coords_2d.append((vec.dot(u), vec.dot(v)))

        poly = Polygon(coords_2d)
        if not poly.is_valid:
            poly = poly.buffer(0)

        if not poly.is_empty:
            shapely_polys.append(poly)

    result = unary_union(shapely_polys)

    # 🔁 UNPROJECT opcional
    if not unproject:
        return result

    def unproject_polygon(poly):
        pts = []

        for x, y in poly.exterior.coords[:-1]:
            if plane == 'XY':
                pts.append(Vector((x, y, 0.0)))
            elif plane == 'XZ':
                pts.append(Vector((x, 0.0, y)))
            elif plane == 'YZ':
                pts.append(Vector((0.0, x, y)))
            elif plane == 'CUSTOM':
                pts.append(plane_origin + u * x + v * y)

        return pts

    if isinstance(result, Polygon):
        return [unproject_polygon(result)]

    elif isinstance(result, MultiPolygon):
        return [unproject_polygon(p) for p in result.geoms]

    return []
