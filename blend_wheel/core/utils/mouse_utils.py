

from decimal import Context
from math import dist
from typing import Literal, Optional
from bpy.types import Event
from mathutils import Vector
import numpy as np

from ..utils.geometry.rpd import rdp
from ..utils.geometry.savgol import savgol_filter_2d
from ..utils.geometry.intersect import path_self_intersects


class ModalMouse:
    moved: bool = True
    init: Optional[Vector] = None
    last: Vector = Vector((0, 0))
    current: Vector = Vector((0, 0))
    delta_x: int = 0
    delta_y: int = 0
    delta_threshold: float = 1.0
    delta_ix: int = 0
    delta_iy: int = 0
    do_record_path: bool = False
    path: list[Vector] = []
    auto_record_path: bool = False
    auto_path: list[Vector] = []

    def __init__(self, context: Context, event: Event, delta_threshold: float = 1.0, record_init: bool = True, auto_record_path: bool = False) -> None:
        self.set_delta_threshold(delta_threshold)
        if record_init:
            self.record_init(event)
        self.auto_record_path = auto_record_path
        self.update(context, event)

    @property
    def delta_vec(self) -> Vector:
        return Vector((self.delta_x, self.delta_y))

    @property
    def delta_len(self) -> float:
        return self.delta_vec.length

    @property
    def delta_ivec(self) -> Vector:
        return Vector((self.delta_ix, self.delta_iy))

    @property
    def delta_ilen(self) -> float:
        return self.delta_ivec.length

    def has_moved_by(self, px: int, use_init: bool = False) -> bool:
        """Check if the mouse has moved by at least `px` pixels in any direction."""
        return self.moved and (self.delta_len >= px or (use_init and self.delta_ilen >= px))

    def is_away_from_init(self, px: int) -> bool:
        """Check if the mouse is away from the initial position by at least `px` pixels in any direction."""
        return self.has_moved_by(px, use_init=True)

    def set_delta_threshold(self, px: int) -> None:
        """Set the delta threshold in pixels."""
        self.delta_threshold = px

    def record_init(self, event: Event) -> None:
        """Record the initial mouse position."""
        self.init = Vector((event.mouse_region_x, event.mouse_region_y))

    def update(self, context: Context, event: Event) -> None:
        """Update the mouse delta values."""
        self.last = self.current
        self.current = Vector((event.mouse_region_x, event.mouse_region_y))
        self.delta_x = int(self.current.x - self.last.x)
        self.delta_y = int(self.current.y - self.last.y)
        self.moved = dist(self.last, self.current) >= self.delta_threshold
        if not self.moved:
            return
        if self.init is not None:
            self.delta_ix = int(self.current.x - self.init.x)
            self.delta_iy = int(self.current.y - self.init.y)
        if self.auto_record_path:
            if event.value in {'PRESS', 'CLICK_DRAG'}:
                self.start_path_recording()
        if self.do_record_path:
            self.path.append(self.current)
        if self.auto_record_path:
            if event.value == 'RELEASE':
                self.end_path_recording()

    def start_path_recording(self) -> None:
        """Start recording the mouse path. This action will disable auto path recording!"""
        self.auto_record_path = False
        self.do_record_path = True
        self.path = []

    def end_path_recording(self) -> list[Vector]:
        """End recording the mouse path."""
        self.do_record_path = False
        return self.path

    def get_even_path(self, segment_size: float = 0.0, method: Literal['BEZIER', 'CATMULL_ROM'] = 'BEZIER') -> list[Vector]:
        """Get the even path."""
        if segment_size == 0.0 or len(self.path) < 2:
            return self.path
        path = self.path
        if method == 'BEZIER':
            samples: list[Vector] = [path[0]]
            for i in range(len(path) - 1):
                p0 = path[i - 1] if i - 1 >= 0 else path[i]
                p1 = path[i]
                p2 = path[i + 1]
                p3 = path[i + 2] if i + 2 < len(path) else path[i + 1]
                seg_len = (p2 - p1).length
                steps = max(8, int(seg_len / max(1e-6, segment_size)) * 3)
                for s in range(1, steps + 1):
                    t = s / steps
                    q = (p1 * 2.0) + (-p0 + p2) * t + (p0 * 2.0 - p1 * 5.0 + p2 * 4.0 - p3) * (t * t) + (-p0 + p1 * 3.0 - p2 * 3.0 + p3) * (t * t * t)
                    q *= 0.5
                    if (q - samples[-1]).length > 1e-6:
                        samples.append(q)
            dists: list[float] = [0.0]
            total = 0.0
            for i in range(1, len(samples)):
                dl = (samples[i] - samples[i - 1]).length
                if dl > 1e-12:
                    total += dl
                    dists.append(total)
                else:
                    dists.append(total)
            even_path: list[Vector] = [samples[0]]
            target = segment_size
            idx = 1
            while target < total and idx < len(dists):
                while idx < len(dists) and dists[idx] < target:
                    idx += 1
                if idx >= len(dists):
                    break
                low = idx - 1
                high = idx
                denom = max(1e-12, dists[high] - dists[low])
                r = (target - dists[low]) / denom
                pt = samples[low] + (samples[high] - samples[low]) * r
                even_path.append(pt)
                target += segment_size
            if (samples[-1] - even_path[-1]).length > 1e-6:
                even_path.append(samples[-1])
            return even_path
        elif method == 'CATMULL_ROM':
            samples: list[Vector] = [path[0]]
            for i in range(len(path) - 1):
                p0 = path[i - 1] if i - 1 >= 0 else path[i]
                p1 = path[i]
                p2 = path[i + 1]
                p3 = path[i + 2] if i + 2 < len(path) else path[i + 1]
                seg_len = (p2 - p1).length
                steps = max(8, int(seg_len / max(1e-6, segment_size)) * 3)
                for s in range(1, steps + 1):
                    t = s / steps
                    q = (p1 * 2.0) + (-p0 + p2) * t + (p0 * 2.0 - p1 * 5.0 + p2 * 4.0 - p3) * (t * t) + (-p0 + p1 * 3.0 - p2 * 3.0 + p3) * (t * t * t)
                    q *= 0.5
                    if (q - samples[-1]).length > 1e-6:
                        samples.append(q)
            return samples
        else:
            raise ValueError(f"Unknown even_method: {method}")

    def get_simplified_path(self, epsilon: float = 0.03) -> list[Vector]:
        """Simplify the path using Ramer-Douglas-Peucker algorithm."""
        if len(self.path) < 2:
            return self.path
        pts = savgol_filter_2d(np.array(self.path), window=11, poly=3)
        pts = rdp(pts, epsilon=epsilon * np.linalg.norm(pts.ptp(axis=0)))
        return [Vector(p) for p in pts]

    def get_closure_snapped_path(self, radius_px: float, min_presence_px: float = 0.0, *, path: list[Vector] | None = None) -> tuple[list[Vector], bool]:
        """Close a path if the stroke end is close enough to the stroke start."""
        src = self.path if path is None else path
        if radius_px <= 0.0 or len(src) < 3:
            return src, False
        total_length = 0.0
        for i in range(1, len(src)):
            total_length += (src[i] - src[i - 1]).length
        if total_length < min_presence_px:
            return src, False
        first = src[0]
        last = src[-1]
        if (last - first).length > radius_px:
            return src, False
        closed_path = list(src)
        if (closed_path[-1] - closed_path[0]).length <= 1e-6:
            return closed_path, True
        if len(closed_path) > 3:
            closed_path[-1] = closed_path[0].copy()
        else:
            closed_path.append(closed_path[0].copy())
        return closed_path, True

    @classmethod
    def analyze_path_shape(
        cls,
        path: list,
        rdp_epsilon: float = 0.03,
        skip_simplify: bool = False,
        prioritize_closed: bool = False,
    ) -> Literal[
        'NONE', 'I', 'L', 'V', 'U', 'W', 'C',
        'Z', 'ZZ', 'X',
        'TRIANGLE', 'SQUARE', 'O'
    ]:

        if len(path) < 2:
            return 'NONE'

        # -------------------------------------------------
        # 1. Preprocess
        # -------------------------------------------------
        if not skip_simplify:
            pts = savgol_filter_2d(np.asarray(path), window=11, poly=3)
            scale = np.linalg.norm(pts.ptp(axis=0))
            pts = rdp(pts, epsilon=rdp_epsilon * scale)
        else:
            pts = np.asarray(path)

        if len(pts) < 2:
            return 'NONE'

        # -------------------------------------------------
        # 2. Segments
        # -------------------------------------------------
        segments: np.ndarray = pts[1:] - pts[:-1]
        nseg = len(segments)

        if nseg == 0:
            return 'NONE'

        bbox = pts.ptp(axis=0)
        diag = np.linalg.norm(bbox)
        closed = np.linalg.norm(pts[0] - pts[-1]) < 0.25 * diag

        if nseg > 8 and not (prioritize_closed and closed):
            return 'NONE'

        # -------------------------------------------------
        # 3. X detection
        # -------------------------------------------------
        if nseg in {3, 4} and (intersect_point := path_self_intersects(pts, return_intersection_point=True)) is not None:
            first_point = Vector(pts[0])
            last_point = Vector(pts[-1])
            if dist(first_point, last_point) < 10:
                # Probably a triangle or square!
                print('End points are too close to each other! Probably a triangle or square!')
                pass
            else:
                median_segment_length: float = np.median(np.linalg.norm(segments, axis=1))
                first_to_intersect: Vector = intersect_point - first_point
                last_to_intersect: Vector = intersect_point - last_point
                minimal_distance_to_intersect: float = min(median_segment_length * 0.2, 10)
                if first_to_intersect.length > minimal_distance_to_intersect and last_to_intersect.length > minimal_distance_to_intersect:
                    return 'X'
                else:
                    # Probably a triangle or square!
                    print('Intersection point is too close to end points! Probably a triangle or square!')
                    pass

        # -------------------------------------------------
        # 4. Signed turning angles
        # -------------------------------------------------
        norms = np.linalg.norm(segments, axis=1, keepdims=True)
        seg_n = segments / np.clip(norms, 1e-6, None)

        turns = []
        for i in range(len(seg_n) - 1):
            v1 = seg_n[i]
            v2 = seg_n[i + 1]
            cross = v1[0] * v2[1] - v1[1] * v2[0]
            dot = np.dot(v1, v2)
            turns.append(np.arctan2(cross, dot))
        turns = np.array(turns)

        BIG = 0.6          # ~35°
        VERY_BIG = 1.3     # ~75°
        SMALL = 0.25       # ~14°

        if prioritize_closed and closed:
            if nseg == 3:
                return 'TRIANGLE'
            if nseg in {4, 5}:
                significant_turns = turns[np.abs(turns) > 0.2]
                if len(significant_turns) >= 3:
                    turn_signs = np.sign(significant_turns)
                    if np.all(turn_signs == turn_signs[0]):
                        return 'SQUARE'
            if nseg >= 9 and len(turns) > 0:
                significant_turns = turns[np.abs(turns) > 0.05]
                if len(significant_turns) > 0:
                    sign_changes = np.sum(np.sign(significant_turns[:-1]) != np.sign(significant_turns[1:]))
                    max_allowed_sign_changes = max(1, int(len(significant_turns) * 0.15))
                    if sign_changes <= max_allowed_sign_changes and np.sum(np.abs(turns)) > 1.5 * np.pi:
                        return 'O'

        big = np.abs(turns) > BIG
        t_big = turns[big]

        # -------------------------------------------------
        # 5. Helpers
        # -------------------------------------------------
        total_turn = np.sum(np.abs(turns))

        # -------------------------------------------------
        # 6. Classification
        # -------------------------------------------------

        # I
        if nseg == 1 or np.all(np.abs(turns) < SMALL):
            return 'I'

        # L
        if nseg == 2 and abs(abs(turns[0]) - np.pi/2) < 0.4:
            return 'L'

        # V
        if nseg == 2 and abs(turns[0]) > VERY_BIG:
            return 'V'

        # U (3 segments, open, same sign, wide)
        if nseg == 3 and not closed:
            if len(t_big) == 2:
                if np.sign(t_big[0]) == np.sign(t_big[1]):
                    if np.all(np.abs(t_big) < 2.4):  # not triangle
                        return 'U'

        # Z
        if nseg == 3:
            if len(t_big) == 2 and np.sign(t_big[0]) == -np.sign(t_big[1]):
                return 'Z'

        # W
        if nseg == 4:
            if len(t_big) == 3:
                signs = np.sign(t_big)
                if np.all(signs[:-1] != signs[1:]):
                    return 'W'

        # ZZ
        if nseg >= 5:
            if len(t_big) >= 4:
                signs = np.sign(t_big)
                if np.sum(signs[:-1] != signs[1:]) >= 2:
                    return 'ZZ'

        # TRIANGLE (closed-ish, 2 big ~120°)
        if nseg == 3 and closed:
            if len(t_big) == 2:
                if abs(abs(t_big[0]) - 2*np.pi/3) < 0.4:
                    return 'TRIANGLE'

        # SQUARE (closed-ish, ~90° turns)
        if nseg in {4, 5} and closed:
            if len(t_big) >= 3:
                if np.all(np.abs(np.abs(t_big) - np.pi/2) < 0.4):
                    return 'SQUARE'

        # ROMBOID (closed, 4 corners, convex, non-right angles)
        if nseg in {4, 5} and closed:
            if len(t_big) == 4:
                # same turning direction (convex polygon)
                if np.all(np.sign(t_big) == np.sign(t_big[0])):
                    # not a square (angles not near 90°)
                    if not np.all(np.abs(np.abs(t_big) - np.pi/2) < 0.4):
                        return 'ROMBOID'

        # O (closed, smooth, full rotation)
        if closed and nseg >= 4:
            if np.all(np.sign(turns) == np.sign(turns[0])):
                if total_turn > 1.6 * np.pi:
                    return 'O'

        # C ──────────────────────────────────────────────
        # Commented by now as 'C' is geometrically 'weak' and can conflict with other shapes.
        # if nseg >= 3 and not closed:
        #     if np.all(np.sign(turns) == np.sign(turns[0])) \
        #        and np.sum(np.abs(turns)) > np.pi:
        #         return 'C'

        return 'NONE'
