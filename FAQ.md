# Frequently Asked Questions

Quick answers about Sculpt-Paint Wheel. For the full guide, see the [README documentation](README.md#documentation).

- [General](#general)
- [Installation and compatibility](#installation-and-compatibility)
- [Using the wheel](#using-the-wheel)
- [Customization and your data](#customization-and-your-data)
- [Buying and supporting](#buying-and-supporting)
- [Troubleshooting](#troubleshooting)

---

## General

### What is Sculpt-Paint Wheel?

A Blender add-on that shows your brushes and tools on a radial wheel right under your cursor. Hold `Space` in a sculpt or paint mode, pick a brush or button, and keep working, without reaching for toolbars or the asset shelf.

### Which modes does it support?

Sculpt, Vertex Paint, Weight Paint, Texture Paint, Sculpt Curves (hair), and the four Grease Pencil modes: Draw, Sculpt, Weight Paint and Vertex Paint. Each mode has its own wheel. See [Supported modes](README.md#supported-modes) for what's on each one.

### Is it really free?

Yes. Sculpt-Paint Wheel is **free and open source** under the GPL-2.0-or-later license, the same family of license as Blender. You can always download it from the [GitHub releases page](https://github.com/jfran3d/Sculpt-Paint-Wheel-Reborn/releases/latest).

---

## Installation and compatibility

### Which Blender versions are supported?

**Blender 5.1 and newer.** Version 1.1.0 is tested on Blender 5.3 and 5.2.

### Does it work with Blender 4.x?

Not this version. It's built as a Blender 5.x extension and relies on the brush assets and Grease Pencil system that Blender 5 uses. Older Blender versions are covered by the [original Sculpt-Paint Wheel](https://github.com/jfranmatheu/Sculpt-Paint-Wheel).

### How do I install it?

1. Download `spwheel-<version>.zip` from the [releases page](https://github.com/jfran3d/Sculpt-Paint-Wheel-Reborn/releases/latest). Don't unzip it.
2. In Blender, go to **Edit › Preferences › Get Extensions**, open the **v** menu at the top right and choose **Install from Disk...**. You can also drag and drop the zip into Blender.
3. Make sure **Sculpt-Paint Wheel** is enabled under **Edit › Preferences › Add-ons**.

### How do I update?

Install the newer zip the same way. Your brush sets, custom buttons and preferences are kept.

### Does it work on Windows, macOS and Linux?

It's built only on Blender's own Python and drawing APIs, with no platform-specific code, so it's available on every platform Blender supports. Testing so far has been done on Windows. If something looks wrong on macOS or Linux, please [report it](https://github.com/jfran3d/Sculpt-Paint-Wheel-Reborn/issues).

### Does it need internet access?

No. The add-on only reads and writes its own settings file on your computer.

---

## Using the wheel

### How do I open the wheel?

Hover the 3D Viewport in a supported mode and **hold `Space`**. Pick a brush or button with a left click, then release `Space`. `Esc` or a right click closes the wheel without picking anything.

### Space used to play the animation. What happened?

In sculpt and paint modes, the add-on binds `Space` to the wheel, which takes priority over Blender's play shortcut there. Playback still works with `Space` in other modes and from the Timeline. If you'd rather use a different key, see the next question.

### Can I change the hotkey?

Yes. Go to **Edit › Preferences › Keymap**, search for `Sculpt-Paint Wheel Modal`, and change the key for the modes you want.

### Can I pick a brush just by releasing the key?

Yes. Turn on **Select on Release** in the add-on preferences: press `Space`, move toward a brush, release, done. **Keep Open** does the opposite: the wheel stays open after you release the key until you press it again.

### Some of my brushes don't fit on the wheel.

When a set has more brushes than fit on the ring, the wheel gets pages. Scroll the mouse wheel to switch between them, and check the `1 / 2` indicator at the bottom.

### Why doesn't Weight Paint show brushes?

The Weight Paint wheels (mesh and Grease Pencil) show a **weight dial** instead of a brush list: pick any weight from 0.0 to 1.0 in one gesture. Brushes and weight tools are available from the buttons in the center.

---

## Customization and your data

### How do I change which brushes and buttons appear?

Open the sidebar with `N` in the 3D Viewport and go to the **Wheel** tab while you are in the mode you want to change. **Brush Sets** controls the outer ring and **Custom Button Sets** controls the center. See [Customizing brushes and buttons](README.md#customizing-brushes-and-buttons).

### What can a custom button do?

It can run an operator, for example inverting the mask, or open a panel or menu as a popup, for example Stroke or Falloff settings. Each mode offers ready-made presets, and you can enter any panel, menu or operator ID by hand.

### Can I go back to the default setup?

Yes. The default set is only created when a mode has no sets at all. Remove your sets for that mode in the **Wheel** tab, and the **Default Set** is recreated the next time Blender starts.

### Where are my settings saved?

In `preferences.json`, inside an `spwheel` folder in Blender's user configuration directory. It's written automatically when Blender closes, and whenever you press **Save/Backup Addon Preferences** in the add-on preferences. It's restored after you update or reinstall the extension.

---

## Buying and supporting

### If it's free, why is it for sale?

Buying it on [Superhive](https://superhivemarket.com/products/sculpt-paint-wheel) or [Payhip](https://payhip.com/b/zXfm2) is how you support its development. Sculpt-Paint Wheel is maintained by one independent developer, and every new Blender version needs porting, testing and fixing. Purchases fund that work, so the add-on keeps improving and stays free for everyone, including students and artists who can't afford to buy it.

### Do buyers get a different version?

No. Everyone gets the same add-on, with the same features. Buying it is a way of saying thanks and keeping the project alive.

### Where should I buy it?

Wherever you prefer: [Superhive](https://superhivemarket.com/products/sculpt-paint-wheel) or [Payhip](https://payhip.com/b/zXfm2). Both support the same developer.

### Can I help without buying it?

Absolutely:
- ⭐ [Star the repository](https://github.com/jfran3d/Sculpt-Paint-Wheel-Reborn) so other artists can find it.
- 🐞 [Report bugs or suggest features](https://github.com/jfran3d/Sculpt-Paint-Wheel-Reborn/issues).
- 📣 Share it with other Blender artists.
- 💻 Contribute code through a pull request.

---

## Troubleshooting

### Nothing happens when I press Space.

- Make sure the mouse is over the **3D Viewport** and you are in a **supported mode**: the wheel doesn't open in Object or Edit mode.
- There must be an active object.
- Check **Edit › Preferences › Keymap** for another add-on using `Space` in the same mode.
- Make sure the extension is enabled under **Edit › Preferences › Add-ons**.

### A button doesn't do anything.

Some operators only work in the right context. For example, multires buttons need a Multires modifier, and keyframe buttons need an existing keyframe. When an operator can't run, Blender doesn't apply it and may print the reason in the system console.

### The Falloff button opens a "Shape" panel.

That's expected on Blender 5.3. Blender moved brush falloff into the new **Shape** panel for mesh sculpt and paint modes, and the add-on opens it automatically.

### I found a bug.

Please [open an issue](https://github.com/jfran3d/Sculpt-Paint-Wheel-Reborn/issues). Include your Blender version, the mode you were in, the steps to reproduce it, and any error from **Window › Toggle System Console** (Windows) or the terminal (macOS/Linux).
