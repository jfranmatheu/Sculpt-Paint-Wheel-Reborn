# Changelog

All notable changes to Sculpt-Paint Wheel. Downloads are on the [releases page](https://github.com/jfran3d/Sculpt-Paint-Wheel-Reborn/releases).

## [2.0.0] - 2026-11-24

### New
- **New ring menu** for custom buttons: one clean segment per button (no empty slots), up to 10 buttons per set.
- **Toggle buttons** that show their on / off state, and a pressed look for operator buttons whose state is on.
- **Script buttons**: run your own Python script, edited and saved from the add-on.
- **New icon set**, super-sampled so icons stay sharp at any size. Any image file can also be a button's icon.
- **Tints** for custom buttons: off, per button type, or a color per button, shown on the fill, the outline, the icon or a color strip (the default).
- **Smart centre**: drag the wheel centre up / down for brush radius and left / right for strength, in every wheel (`Shift` finer, `Ctrl` faster, `Esc` / right click to cancel). Hovering a button shows its name in the centre.
- **Page pill** under the ring: click its arrows to change page. `Shift` + mouse wheel, or dragging the set name, switches brush sets.
- **Allow Double Ring**: a brush set that doesn't fit on one ring gets a second, staggered ring (up to 34 brushes per page); the wheel, the pie and the color picker grow to fit it.
- **Theme presets**: 10 built-in themes (Dark, Light, Midnight, Ember, Forest, Rose, Graphite, High Contrast, Paper, Frost), live editing, and Save / Save As / Reset / Delete for your own themes.
- Preferences in **Settings / Theme / Keymap** tabs; the Brush Ring settings show how many slots a page holds.
- **Masking** default set for Sculpt, and fuller default sets with operators and toggles in the other modes. Existing default sets get the new default buttons once, without re-adding buttons you removed.
- The weight wheel shows the value in its centre while dragging; the Grease Pencil weight wheel shows brush tools only.
- The color picker now shows in Grease Pencil Vertex Paint (Draw and Replace brushes), and whenever the active brush paints color.

### Changed
- The wheel looks closer to FlexSpace's ring menu, with smoother rings and a shared accent color.
- **Slot Size** defaults to 56.
- Faster drawing: the wheel reuses its draw batches, and brush previews are cached and shared.

### Fixes
- Brush sets and custom buttons edited from the wheel or the sidebar are now kept after restarting Blender.
- The backup of your sets is saved when you quit Blender again, even after opening a file during the session.
- Opening Blender by double-clicking a `.blend` file no longer skips restoring your saved data and creating the default sets.
- An error while the wheel is open no longer leaves it stuck on screen with the brush cursor hidden; you get an error message instead.
- The wheel no longer stays open when the key is released during a drag, and the brush cursor is no longer turned back on after using the wheel.
- Changing brush set with `Shift`+scroll and clicking without moving the mouse no longer picks a brush from the previous set.
- Releasing over another pie button no longer runs that button, and a quick second click on the wheel is no longer ignored.
- Clicks between the weight toolbar buttons no longer set the weight.
- Operator buttons accept tuples, lists and commas in their arguments, e.g. `value=(0, 0, 1)`.
- With Select on Release, releasing over the color picker, the weight ring or the brush set title no longer leaves the wheel open in a drag.
- The color picker shows after picking a paint brush in an open wheel, its hue ring shows the colors it picks, and its handles and swatches match the brush color.
- Theme colors and icons are no longer drawn darker than they are.
- The text in the wheel centre no longer overflows its disc.
- Renaming a set no longer makes its dropdown show (and later activate) another set; set and brush list operators no longer error outside sculpt / paint modes or report "Cancelled" after working.
- Bundled button icons keep working when the add-on install moves.
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
[1.1.1]: https://github.com/jfran3d/Sculpt-Paint-Wheel-Reborn/releases/tag/v1.1.1
[1.1.0]: https://github.com/jfran3d/Sculpt-Paint-Wheel-Reborn/releases/tag/v1.1.0
