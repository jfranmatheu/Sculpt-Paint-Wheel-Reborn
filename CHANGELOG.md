# Changelog

All notable changes to Sculpt-Paint Wheel. Downloads are on the [releases page](https://github.com/jfran3d/Sculpt-Paint-Wheel-Reborn/releases).

## [2.0.0] - 2026-11-25

### New
- **New ring menu** for custom buttons, styled after FlexSpace's ring menu. The hovered button's name shows in the wheel centre.
- **Toggle buttons** that show their on / off state, and a pressed look for operator buttons whose state is on.
- **Script buttons**: run your own Python script, edited and saved from the add-on.
- **New icon set** for the default buttons, super-sampled so icons stay sharp at any size.
- **Tints** for custom buttons: off, per button type, or a color per button. The tint goes on the fill, the outline, the icon or a color strip along the inner edge (the default).
- **Radius and strength from the centre**: in every wheel, drag the centre up / down for the brush radius and left / right for the strength. `Shift` is finer, `Ctrl` faster, `Esc` or right click cancels. Turn it off with **Drag Center: Radius / Strength** in Settings. It replaces the weight wheel's centre pad.
- **Page pill** under the brush ring (`< 1 / 3 >`): click its arrows to change page. It replaces the page dots and the page drag.
- **Allow Double Ring** (Settings > Brush Ring): a brush set that doesn't fit on one ring gets a second, staggered ring, up to 34 brushes per page. The whole wheel grows to fit it, pie and color picker included.
- **Theme presets**: 10 built-in themes (Dark, Light, Midnight, Ember, Forest, Rose, Graphite, High Contrast, Paper, Frost), live editing, and Save / Save As / Reset / Delete for your own themes.
- New theme settings: Accent Color for hover outlines, Icon Color, pie icon size, brush slot outline width, and a soft shadow behind the wheel (opacity and size).
- Preferences in **Settings / Theme / Keymap** tabs with collapsible sections. The Keymap tab changes the wheel hotkey of each mode in place, and Settings > Brush Ring shows how many slots a page holds.
- **Masking** default set for Sculpt: invert / clear, smooth / sharpen, grow / shrink, hide masked / show all, invert visible and face set from mask. It's the first and active set on a fresh install; existing setups get it once, without changing their active set.
- Fuller default sets in the other modes, with operators and toggles (mirror X, selection masking, auto normalize, multi-frame editing, onion skin, cavity mask, texture slots...). Existing default sets get new default buttons once, without re-adding buttons you removed.
- Weight wheel: the centre shows the weight only while you drag the weight ring or a marker. The Grease Pencil weight wheel shows only its brush tools.

### Changed
- The wheel looks closer to FlexSpace's ring menu: neutral dark segments, a solid blend for pressed buttons, and smoother rings at any scale.
- **Slot Size** defaults to 56.
- The active brush's slot is highlighted as soon as the wheel opens.
- Faster drawing: the wheel reuses its draw data between redraws (about 20-30% less time per frame).

### Fixes
- Colors look as set: theme colors and colored icons are no longer drawn darker, the hue ring shows the colors it picks, and the color picker's handles and swatches match the brush color.
- The color picker appears (or hides) when you pick a paint (or sculpt) brush with the wheel open.
- Saturation and value arcs no longer get jagged edges on some GPUs.
- The wheel no longer stays open when its key is released during a drag.
- The brush cursor is no longer turned back on after using the wheel if you had it off.
- Pressing a pie button and releasing over another one no longer runs the other one.
- A quick second click on the wheel is no longer ignored, and pressing the key again quickly closes a wheel kept open.
- Clicks between the weight toolbar buttons no longer set the weight.
- Dragging up in small steps now grows the brush radius (it could only shrink).
- The text in the wheel centre no longer overflows its disc.
- Renaming a set no longer makes its dropdown show (and, after a restart, activate) another set.
- Set and brush list operators no longer error outside sculpt / paint modes (e.g. from F3 search), and Remove / Move no longer report "Cancelled" after working, so they can be undone.
- Default buttons with the same operator but different settings (e.g. Clear Mask and Invert Mask) are no longer treated as the same button.
- Brush previews: two libraries with a brush at the same path no longer share a thumbnail, a regenerated preview shows right away, and brushes without a preview no longer read the disk on every redraw.
- Bundled button icons keep working after moving to a new Blender version or restoring your backup on another machine.

## [1.2.0] - 2026-11-24

### New
- Custom buttons: use any image file as a button's icon.
- Custom button ring: one segment per button (no empty slots), up to 10 buttons per set.

### Fixes
- The add-on failed to enable when installed in an extensions repository other than the default one (`ModuleNotFoundError: No module named 'bl_ext.user_default.spwheel'`, [#3](https://github.com/jfranmatheu/Sculpt-Paint-Wheel-Reborn/issues/3)).
- Blender 5.3: the wheel's color picker, the centre drag (size / strength) and the weight dial now change the values Blender really uses. Blender 5.3 moved the "unified" toggles to the brush, so picks and drags could change a value Blender ignores (a picked color didn't paint, a bigger brush stayed the same size).
- Brush sets and custom buttons edited from the wheel or the sidebar are now kept after restarting Blender.
- The backup of your sets is saved when you quit Blender again, even after opening a file during the session.
- Opening Blender by double-clicking a `.blend` file no longer skips restoring your saved data and creating the default sets.
- An error while the wheel is open no longer leaves it stuck on screen with the brush cursor hidden; you get an error message instead.
- Changing brush set with `Shift`+scroll and clicking without moving the mouse no longer picks a brush from the previous set.
- Operator buttons accept tuples, lists and commas in their arguments, e.g. `value=(0, 0, 1)`.
- With Select on Release, releasing over the color picker, the weight ring or the brush set title no longer leaves the wheel open in a drag.
- The color picker now shows in Grease Pencil Vertex Paint (Draw and Replace brushes), and whenever the active brush paints color.
- With several 3D viewports or Quad View, the wheel is only drawn in the viewport where you opened it.
- Dragging the weight ring with a selection mask on adds one undo step instead of dozens.
- Icons for newer Essentials brushes (Scene Project, Cut, Add Weight, Set Weight) are no longer missing.
- Debug logging is off; it printed to the console on every redraw.

## [1.1.1] - 2026-11-23

### Fixes
- The **Scale** setting now scales where you can hover and click, not only how the wheel is drawn. Before, at any scale other than 1.0, brushes, buttons and the color picker reacted at the wrong spot ([#1](https://github.com/jfran3d/Sculpt-Paint-Wheel-Reborn/issues/1)).

## [1.1.0] - 2026-11-15

### New
- Support for **Blender 5.3** (still compatible with 5.1 / 5.2).
- New wheels for **Vertex Paint**, **Sculpt Curves** and every **Grease Pencil** paint mode (Draw, Sculpt, Weight, Vertex), each with default brushes, default buttons and preset lists.
- Grease Pencil and Sculpt Curves wheels now open with `Space`.
- Updated Sculpt presets to the Blender 5.3 operators (Mask Extract / Slice, Mask from Cavity, Hide Masked, Show All, Invert Visible).
- **Falloff** buttons open the new **Shape** panel in mesh paint modes on Blender 5.3.

### Fixes
- Fixed sidebar panels that failed to register on Blender 5.2+.
- Fixed a draw callback leak when the wheel failed to open.

[2.0.0]: https://github.com/jfran3d/Sculpt-Paint-Wheel-Reborn/releases/tag/v2.0.0
[1.2.0]: https://github.com/jfran3d/Sculpt-Paint-Wheel-Reborn/releases/tag/v1.2.0
[1.1.1]: https://github.com/jfran3d/Sculpt-Paint-Wheel-Reborn/releases/tag/v1.1.1
[1.1.0]: https://github.com/jfran3d/Sculpt-Paint-Wheel-Reborn/releases/tag/v1.1.0
