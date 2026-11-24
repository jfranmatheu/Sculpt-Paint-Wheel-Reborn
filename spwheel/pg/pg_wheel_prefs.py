from bpy.props import BoolProperty, CollectionProperty, EnumProperty, FloatProperty, IntProperty, PointerProperty
from bpy.types import Context, UILayout

from ..core.bl_types import PropertyGroup
from .pg_brush_set import BrushSet, BrushSetPreferences
from .pg_colpk import ColorPickerPreferences
from .pg_wheel_theme import WheelTheme
from .wheels.weight_prefs import WeightWheelPrefs
from .pg_wheel_storage import WheelStorage


class WheelPrefs(PropertyGroup):

    # Wheel Storage.
    # -----------------------------------------------------------------------

    storage: PointerProperty(type=WheelStorage)


    # Per Mode Preferences.
    # -----------------------------------------------------------------------

    weight: PointerProperty(type=WeightWheelPrefs)


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
        description="Select the hovered brush or press hovered pie button when the trigger key is released instead of clicking, then closes the wheel",
        default=False,
    )

    center_text_max_lines: IntProperty(
        name="Center Text Lines",
        description="Maximum number of lines of the name shown in the centre of the wheel",
        default=2,
        min=1,
        max=3,
    )

    # Preferences UI.
    # -----------------------------------------------------------------------

    prefs_tab: EnumProperty(
        name="Preferences Tab",
        items=(
            ("SETTINGS", "Settings", "How the wheel behaves", 'PREFERENCES', 0),
            ("THEME", "Theme", "How the wheel looks", 'COLOR', 1),
            ("KEYMAP", "Keymap", "Hotkeys that open the wheel", 'KEYINGSET', 2),
        ),
        default="SETTINGS",
    )

    # Wheel Widgets Settings.
    # -----------------------------------------------------------------------

    color_picker: PointerProperty(type=ColorPickerPreferences)
    brush_set_ring: PointerProperty(type=BrushSetPreferences)


    # -----------------------------------------------------------------------
    # UI.
    # -----------------------------------------------------------------------

    def draw_preferences_ui(self, context: Context, layout: UILayout):
        tabs = layout.row(align=True)
        tabs.scale_y = 1.3
        tabs.prop(self, 'prefs_tab', expand=True)
        layout.separator()

        if self.prefs_tab == "SETTINGS":
            self._draw_settings_tab(context, layout)
        elif self.prefs_tab == "THEME":
            self.theme.draw_ui(context, layout)
        else:
            self._draw_keymap_tab(context, layout)

    def _draw_settings_tab(self, context: Context, layout: UILayout) -> None:
        if body := prefs_panel(layout, "spwheel_settings_wheel", "Wheel", 'MESH_CIRCLE'):
            body.prop(self, 'scale')
            body.prop(self, 'center_text_max_lines')
            col = body.column(heading="Behavior")
            col.prop(self, 'keep_open')
            col.prop(self, 'select_on_release')

        if body := prefs_panel(layout, "spwheel_settings_color_picker", "Color Picker", 'COLORSET_02_VEC'):
            self.color_picker.draw_ui(context, body)

        if body := prefs_panel(layout, "spwheel_settings_weight", "Weight Wheel", 'WPAINT_HLT'):
            col = body.column(heading="Markers")
            col.prop(self.weight, "show_markers", text="Show")
            sub = col.column()
            sub.active = self.weight.show_markers
            sub.prop(self.weight, "use_interactable_markers", text="Interactable")
            sub.prop(self.weight, "marker_count", text="Count")
            body.prop(self.weight, "set_weight_of_selection_directly")

    def _draw_keymap_tab(self, context: Context, layout: UILayout) -> None:
        import rna_keymap_ui
        from ..km import modes
        from ..ops.op_wheel_modal import WheelModal

        kc = context.window_manager.keyconfigs.user
        col = layout.column()
        found = False
        for km_name in sorted(modes):
            km = kc.keymaps.get(km_name)
            if km is None:
                continue
            for kmi in km.keymap_items:
                if kmi.idname != WheelModal.bl_idname:
                    continue
                found = True
                box = col.box()
                box.label(text=km_name, icon='WINDOW')
                box.context_pointer_set("keymap", km)
                rna_keymap_ui.draw_kmi([], kc, km, kmi, box, 0)
        if not found:
            col.label(text="No wheel hotkeys found", icon='INFO')


def prefs_panel(layout: UILayout, idname: str, title: str, icon: str, closed: bool = False) -> UILayout | None:
    """Collapsible section (remembers its open state); returns its body with aligned labels, or None if closed."""
    header, body = layout.panel(idname, default_closed=closed)
    header.label(text=title, icon=icon)
    if body is not None:
        body.use_property_split = True
        body.use_property_decorate = False
    return body
