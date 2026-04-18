"""BMesh fill utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from mathutils import Matrix, Vector

if TYPE_CHECKING:
    from bmesh.types import BMEdge, BMFace, BMVert, BMesh


# ──────────────────────────────────────────────────────────────────────────────
#  Public API
# ──────────────────────────────────────────────────────────────────────────────

def grid_fill_between_equivalent_edge_loops(
    bm: 'BMesh',
    edges_a: List['BMEdge'],
    edges_b: List['BMEdge'],
    cuts: int = 0,
    path_guide: Optional[List[Vector]] = None,
    path_start_t: float = 0.0,
    use_previz: bool = False,
    matrix_world: Optional[Matrix] = None,
) -> dict:
    """Create a quad grid between two edge loops with the **same** edge count.

    Parameters
    ----------
    bm : BMesh
        The BMesh to create geometry in (only mutated when *use_previz* is
        ``False``).
    edges_a, edges_b : list[BMEdge]
        Two boundary edge chains with **equal** edge counts.
    cuts : int
        Number of intermediate edge loops to insert between the two loops.
    path_guide : list[Vector] | None
        Optional 3-D world-space polyline used as a guide curve.
    path_start_t : float
        Normalised start parameter along the path guide (0–1).
    use_previz : bool
        When ``True`` no geometry is created.  Instead a dict suitable for
        GPU drawing is returned (world-space *coords*, triangulated
        *face_indices*, line-pair *edge_indices*).
    matrix_world : Matrix | None
        Object → world matrix.  **Required** when *use_previz* is ``True``
        so that all returned coordinates are in world space.

    Returns
    -------
    dict
        * ``{'faces': list[BMFace]}`` when *use_previz* is ``False``.
        * ``{'coords': .., 'face_indices': .., 'edge_indices': ..,
          'real_face_indices': ..}`` when *use_previz* is ``True``.
    """
    if len(edges_a) != len(edges_b):
        raise ValueError(
            f"Edge loops must have the same edge count, "
            f"got {len(edges_a)} vs {len(edges_b)}"
        )

    verts_a, is_closed_a = _get_ordered_verts(edges_a)
    verts_b, is_closed_b = _get_ordered_verts(edges_b)
    if not verts_a or not verts_b:
        raise ValueError("Could not order vertices from edge loops")

    is_closed = is_closed_a and is_closed_b
    verts_b = _align_loops(verts_a, verts_b, is_closed)

    count = len(verts_a)

    # ── Path guide ────────────────────────────────────────────────────────
    path_fn = None
    straight_start = straight_end = None

    if path_guide and len(path_guide) >= 2:
        cum = [0.0]
        total = 0.0
        for i in range(1, len(path_guide)):
            total += (path_guide[i] - path_guide[i - 1]).length
            cum.append(total)

        if total > 0:
            t_range = 1.0 - path_start_t

            def _sample_path(
                t_local,
                _cum=cum,
                _total=total,
                _pg=path_guide,
                _pst=path_start_t,
                _tr=t_range,
            ):
                t_global = max(0.0, min(1.0, _pst + t_local * _tr))
                target = t_global * _total
                seg = 0
                for k in range(1, len(_cum)):
                    if _cum[k] >= target:
                        seg = k - 1
                        break
                s0, s1 = _cum[seg], _cum[seg + 1]
                sl = s1 - s0
                if sl > 0:
                    st = max(0.0, min(1.0, (target - s0) / sl))
                    return _pg[seg].lerp(_pg[seg + 1], st)
                return _pg[seg].copy()

            path_fn = _sample_path
            straight_start = (
                sum((v.co for v in verts_a), Vector()) / len(verts_a)
            )
            straight_end = (
                sum((v.co for v in verts_b), Vector()) / len(verts_b)
            )

    # ── Dispatch ──────────────────────────────────────────────────────────
    if use_previz:
        mw = matrix_world if matrix_world is not None else Matrix.Identity(4)
        return _build_previz_grid(
            verts_a, verts_b, is_closed, count, cuts,
            path_fn, straight_start, straight_end, mw,
        )
    return _build_bmesh_grid(
        bm, verts_a, verts_b, is_closed, count, cuts,
        path_fn, straight_start, straight_end,
    )


# ──────────────────────────────────────────────────────────────────────────────
#  Geometry construction
# ──────────────────────────────────────────────────────────────────────────────

def _build_bmesh_grid(
    bm, verts_a, verts_b, is_closed, count, cuts,
    path_fn, straight_start, straight_end,
) -> dict:
    """Create actual BMesh faces (quads) between the two loops."""
    rows = [verts_a]

    for i in range(cuts):
        t = (i + 1) / (cuts + 1)
        row = []
        for j in range(count):
            co = verts_a[j].co.lerp(verts_b[j].co, t)
            if path_fn:
                co = co + (path_fn(t) - straight_start.lerp(straight_end, t))
            row.append(bm.verts.new(co))
        rows.append(row)

    rows.append(verts_b)

    new_faces: list['BMFace'] = []
    for r in range(len(rows) - 1):
        curr, nxt = rows[r], rows[r + 1]
        limit = count if is_closed else count - 1
        for j in range(limit):
            j2 = (j + 1) % count if is_closed else j + 1
            try:
                new_faces.append(
                    bm.faces.new((curr[j], curr[j2], nxt[j2], nxt[j]))
                )
            except ValueError:
                pass

    return {'faces': new_faces}


def _build_previz_grid(
    verts_a, verts_b, is_closed, count, cuts,
    path_fn, straight_start, straight_end, mw,
) -> dict:
    """Build preview data (world-space coords + triangulated indices)."""
    coords: list[Vector] = []
    row_indices: list[list[int]] = []
    idx = 0

    # Row A
    ri: list[int] = []
    for v in verts_a:
        coords.append(mw @ v.co)
        ri.append(idx)
        idx += 1
    row_indices.append(ri)

    # Intermediate rows
    for i in range(cuts):
        t = (i + 1) / (cuts + 1)
        ri = []
        for j in range(count):
            co = verts_a[j].co.lerp(verts_b[j].co, t)
            if path_fn:
                co = co + (path_fn(t) - straight_start.lerp(straight_end, t))
            coords.append(mw @ co)
            ri.append(idx)
            idx += 1
        row_indices.append(ri)

    # Row B
    ri = []
    for v in verts_b:
        coords.append(mw @ v.co)
        ri.append(idx)
        idx += 1
    row_indices.append(ri)

    # Faces (triangulated quads) + edges
    face_indices: list[list[int]] = []
    edge_indices: list[tuple[int, int]] = []

    for r in range(len(row_indices) - 1):
        curr, nxt = row_indices[r], row_indices[r + 1]
        limit = count if is_closed else count - 1
        for j in range(limit):
            j2 = (j + 1) % count if is_closed else j + 1
            i0, i1 = curr[j], curr[j2]
            i2, i3 = nxt[j2], nxt[j]
            face_indices.append([i0, i1, i2])
            face_indices.append([i0, i2, i3])
            edge_indices.append((i0, i1))
            edge_indices.append((i1, i2))
            edge_indices.append((i2, i3))
            edge_indices.append((i3, i0))

    return {
        'coords': coords,
        'face_indices': face_indices,
        'edge_indices': edge_indices,
        'real_face_indices': [],
    }


# ──────────────────────────────────────────────────────────────────────────────
#  Vert ordering & loop alignment
# ──────────────────────────────────────────────────────────────────────────────

def _get_ordered_verts(edges) -> tuple[list, bool]:
    """Walk *edges* and return ``(ordered_verts, is_closed)``."""
    if not edges:
        return [], False

    adj: dict = {}
    for e in edges:
        v1, v2 = e.verts
        adj.setdefault(v1, []).append(v2)
        adj.setdefault(v2, []).append(v1)

    start = edges[0].verts[0]
    is_closed = True
    leaves = [v for v, n in adj.items() if len(n) == 1]
    if leaves:
        is_closed = False
        start = leaves[0]

    path = [start]
    visited = {start}
    curr = start
    while True:
        nxt = None
        for n in adj.get(curr, []):
            if n not in visited:
                nxt = n
                break
        if nxt:
            visited.add(nxt)
            path.append(nxt)
            curr = nxt
        else:
            break

    return path, is_closed


def _align_loops(loop_a, loop_b, is_closed) -> list:
    """Re-order *loop_b* so that its vertices correspond spatially to *loop_a*."""
    if is_closed:
        best_shift = 0
        min_dist = float('inf')
        v0 = loop_a[0].co
        for i, v in enumerate(loop_b):
            d = (v.co - v0).length
            if d < min_dist:
                min_dist = d
                best_shift = i
        new_b = loop_b[best_shift:] + loop_b[:best_shift]
        if len(loop_a) > 1:
            va = loop_a[1].co - loop_a[0].co
            vb = new_b[1].co - new_b[0].co
            if va.dot(vb) < 0:
                pivot = new_b[0]
                rest = new_b[1:]
                rest.reverse()
                new_b = [pivot] + rest
    else:
        d_straight = (
            (loop_a[0].co - loop_b[0].co).length
            + (loop_a[-1].co - loop_b[-1].co).length
        )
        d_reversed = (
            (loop_a[0].co - loop_b[-1].co).length
            + (loop_a[-1].co - loop_b[0].co).length
        )
        new_b = (
            list(reversed(loop_b)) if d_reversed < d_straight
            else list(loop_b)
        )
    return new_b

