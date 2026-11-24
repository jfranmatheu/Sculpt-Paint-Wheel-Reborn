from bpy.types import Context
from ..pg.pg_wheel_prefs import WheelPrefs
from .wheel import Wheel
from ..widgets.brush_set_ring import BrushSetRing, RING_OUTER_FACTOR, ring_count_for, wheel_layout
from ..widgets.tarta_ring import TartaRing
from ..widgets.wheel_core import WheelCore
from ..pg.pg_wheel_storage import SculptPaintWheelStorage, WheelStorage
from ..widgets.color_picker import ColorPickerWidget
from ..utils.ups import has_brush_color_capabilities


class SculptPaintWheel(Wheel):
    brush_set_ring: BrushSetRing
    tarta_ring: TartaRing
    color_picker: ColorPickerWidget
    default_radius = 210 # radius without color picker: 160
    reduced_radius = 195

    def setup(self, context: Context) -> None:
        tarta_ring = TartaRing()
        tarta_ring.set_parent(self)
        self.tarta_ring = tarta_ring

        WheelCore(tarta_ring).set_parent(self)
        
        color_picker = ColorPickerWidget()
        color_picker.set_parent(self)
        self.color_picker = color_picker

        brush_set_ring = BrushSetRing()
        brush_set_ring.set_parent(self)
        self.brush_set_ring = brush_set_ring

    def on_brush_set_change(self, context: Context) -> None:
        self._activate(context)

    def on_brush_change(self, context: Context) -> None:
        """A brush was picked while the wheel stays open (Keep Open, or the trigger key still held): show / hide the
        color picker when the new brush needs it and the old one didn't (or the other way round)."""
        if self.wants_color_picker(context) != self.color_picker.enabled:
            self._activate(context)

    @staticmethod
    def wants_color_picker(context: Context) -> bool:
        # Shown when the brush set asks for it, or when the active brush paints color (Paint brush in Sculpt
        # Mode, texture / vertex paint brushes): default sets never set ``use_color_picker``.
        active_brush_set = WheelStorage.get_by_mode(context).active_brush_set
        return (active_brush_set is not None and active_brush_set.use_color_picker) or has_brush_color_capabilities(context)

    def activate(self, context: Context, prefs: WheelPrefs, storage: SculptPaintWheelStorage) -> None:
        use_colorpk = self.wants_color_picker(context)
        ring_prefs = prefs.brush_set_ring
        base_radius = self.default_radius if use_colorpk else self.reduced_radius
        brush_set = storage.active_brush_set
        rows = ring_count_for(ring_prefs, base_radius, len(brush_set.items) if brush_set else 0)
        self.radius, content_scale = wheel_layout(ring_prefs, base_radius, rows)  # (Two rings: a bigger wheel.)
        self.brush_set_ring.row_count = rows

        self.brush_set_ring.set_transform_thickness(RING_OUTER_FACTOR, -ring_prefs.ring_thickness(rows))
        if use_colorpk:
            self.color_picker.enabled = True
            # (From the base radius: with two rings the pie grows with the content, not with the whole wheel.)
            pie = base_radius * content_scale
            self.tarta_ring.set_transform(0, 0, pie * .1, pie * .4)
            self.color_picker.set_transform(0, 0, self.tarta_ring.radius_outer+4, self.brush_set_ring.radius_inner-4)
        else:
            self.color_picker.enabled = False
            self.tarta_ring.set_transform(0, 0, 0.1, self.brush_set_ring.radius_inner - self.radius * 0.03)
