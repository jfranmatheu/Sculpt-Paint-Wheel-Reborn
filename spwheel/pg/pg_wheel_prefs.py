from bpy.props import BoolProperty, CollectionProperty, FloatProperty, IntProperty, PointerProperty
from bpy.types import Context, UILayout

from ..core.bl_types import PropertyGroup
from .pg_brush_set import BrushSet
from .pg_colpk import ColorPicker
from .pg_wheel_theme import WheelTheme
from .pg_tarta_set import WheelTartaSet


class WheelPrefs(PropertyGroup):

    # Wheel Style.
    # -----------------------------------------------------------------------

    scale: FloatProperty(
        name="Scale",
        description="Scale of the wheel",
        default=1.0,
        min=0.1,
        max=10.0,
        step=0.1,
        precision=2,
    )

    theme: PointerProperty(type=WheelTheme)

    # Wheel Behavior.
    # -----------------------------------------------------------------------

    keep_open: BoolProperty(
        name="Keep Open",
        description="First key release does not close the wheel; click to select then press key again to close",
        default=False,
    )

    select_on_release: BoolProperty(
        name="Select on Release",
        description="Select the hovered brush when the trigger key is released instead of clicking",
        default=False,
    )

    # Wheel Widgets Settings.
    # -----------------------------------------------------------------------

    color_picker: PointerProperty(type=ColorPicker)


    # Tarta Sets.
    # -----------------------------------------------------------------------

    tarta_sets: CollectionProperty(type=WheelTartaSet)
    active_tarta_set_index: IntProperty(
        name="Active Custom Buttons Set Index",
        description="Index of the active custom buttons set",
        default=-1,
    )

    @property
    def active_tarta_set(self) -> WheelTartaSet:
        if not self.tarta_sets:
            return None
        if self.active_tarta_set_index < 0:
            return None
        if self.active_tarta_set_index >= len(self.tarta_sets):
            return None
        return self.tarta_sets[self.active_tarta_set_index]

    def add_tarta_set(self) -> WheelTartaSet:
        new_tarta_set = self.tarta_sets.add()
        self.active_tarta_set_index = len(self.tarta_sets) - 1
        # Avoid duplicate names.
        name = f"Button Set {len(self.tarta_sets)}"
        picked_names = {t.name for t in self.tarta_sets}
        if name in picked_names:
            for i in range(1, 100):
                name = f"Button Set {i}"
                if name not in picked_names:
                    break
        new_tarta_set.name = name
        return new_tarta_set

    def remove_active_tarta_set(self) -> None:
        self.tarta_sets.remove(self.active_tarta_set_index)
        self.active_tarta_set_index = -1 if not self.tarta_sets else self.active_tarta_set_index - 1

    def move_active_tarta_set(self, direction: int) -> None:
        if direction == 1:
            target_index = (self.active_tarta_set_index - 1 + len(self.tarta_sets)) % len(self.tarta_sets)
        elif direction == -1:
            target_index = (self.active_tarta_set_index + 1) % len(self.tarta_sets)
        else:
            raise ValueError(f"Invalid direction: {direction}")
        self.tarta_sets.move(self.active_tarta_set_index, target_index)
        self.active_tarta_set_index = target_index


    # Wheel Data: Brush Sets.
    # -----------------------------------------------------------------------

    brush_sets: CollectionProperty(type=BrushSet)
    active_brush_set_index: IntProperty(
        name="Active Brush Set Index",
        description="Index of the active brush set",
        default=-1,
    )

    @property
    def active_brush_set(self) -> BrushSet:
        if not self.brush_sets:
            return None
        if self.active_brush_set_index < 0:
            return None
        if self.active_brush_set_index >= len(self.brush_sets):
            return None
        return self.brush_sets[self.active_brush_set_index]
    
    def add_brush_set(self) -> BrushSet:
        new_brush_set = self.brush_sets.add()
        self.active_brush_set_index = len(self.brush_sets) - 1
        # Avoid duplicate names.
        name = f"Brush Set {len(self.brush_sets)}"
        picked_names = {t.name for t in self.brush_sets}
        if name in picked_names:
            for i in range(1, 100):
                name = f"Brush Set {i}"
                if name not in picked_names:
                    break
        new_brush_set.name = name
        return new_brush_set

    def remove_active_brush_set(self) -> None:
        self.brush_sets.remove(self.active_brush_set_index)
        self.active_brush_set_index = -1 if not self.brush_sets else self.active_brush_set_index - 1

    def move_active_brush_set(self, direction: int) -> None:
        if direction == 1:
            target_index = (self.active_brush_set_index - 1 + len(self.brush_sets)) % len(self.brush_sets)
        elif direction == -1:
            target_index = (self.active_brush_set_index + 1) % len(self.brush_sets)
        else:
            raise ValueError(f"Invalid direction: {direction}")
        self.brush_sets.move(self.active_brush_set_index, target_index)
        self.active_brush_set_index = target_index


    # -----------------------------------------------------------------------
    # UI.
    # -----------------------------------------------------------------------

    def draw_preferences_ui(self, context: Context, layout: UILayout):
        _, content = self.draw_section(layout, "Settings", icon='SETTINGS')
        content.prop(self, 'scale')
        content.prop(self, 'keep_open')
        content.prop(self, 'select_on_release')

        _, content = self.draw_section(layout, "Theme", icon='COLOR')
        self.theme.draw_ui(context, content)
        
        _, content = self.draw_section(layout, "Color Picker", icon='COLORSET_02_VEC')
        self.color_picker.draw_ui(context, content)
