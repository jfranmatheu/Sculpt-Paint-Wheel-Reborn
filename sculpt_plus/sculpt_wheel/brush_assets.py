"""Brush asset utilities -- enumeration, activation, and preview texture caching."""

from __future__ import annotations

from typing import TYPE_CHECKING

import bpy
import gpu
from gpu.types import GPUTexture
from .custom_buttons import get_custom_button_texture

if TYPE_CHECKING:
    from .data import WheelBrushSlot

from .data import SculptWheelData


# ---------------------------------------------------------------------------
# Preview texture cache  (session_uid -> GPUTexture)
# ---------------------------------------------------------------------------

_preview_cache: dict[int, GPUTexture] = {}


def clear_preview_cache() -> None:
    _preview_cache.clear()


# ---------------------------------------------------------------------------
# Brush enumeration
# ---------------------------------------------------------------------------

def get_sculpt_brushes() -> list[bpy.types.Brush]:
    """Return all loaded Brush data-blocks usable in Sculpt mode."""
    return [b for b in bpy.data.brushes if b.use_paint_sculpt]


def slot_matches_brush(slot: 'WheelBrushSlot', brush: bpy.types.Brush, asset_ref) -> bool:
    """Return True if *slot* was created from *brush* (and optional *asset_ref*)."""
    if slot.display_name != brush.name:
        return False
    if asset_ref is not None:
        return (
            slot.asset_library_type == asset_ref.asset_library_type
            and slot.asset_library_identifier == asset_ref.asset_library_identifier
            and slot.relative_asset_identifier == asset_ref.relative_asset_identifier
        )
    return (
        slot.asset_library_type == 'LOCAL'
        and slot.relative_asset_identifier == brush.name
    )


def find_brush_for_slot(slot: 'WheelBrushSlot') -> bpy.types.Brush | None:
    """Look up a loaded Brush matching a wheel slot by name then by asset ref."""
    for brush in bpy.data.brushes:
        if brush.name == slot.display_name:
            return brush
    if slot.relative_asset_identifier:
        for brush in bpy.data.brushes:
            if brush.name == slot.relative_asset_identifier:
                return brush
    return None


# ---------------------------------------------------------------------------
# Brush activation
# ---------------------------------------------------------------------------

def _slot_stored_path_is_asset_path(slot: 'WheelBrushSlot') -> bool:
    """True if *slot*'s stored triple looks like a real asset path, not a bare brush name."""
    rid = slot.relative_asset_identifier
    if not rid:
        return False
    # if slot.asset_library_type != 'LOCAL':
    #     return True
    return ('/' in rid) or ('\\' in rid) or ('.blend' in rid.lower())


def _asset_triple_from_brush(brush: bpy.types.Brush) -> tuple[str, str, str] | None:
    wr = getattr(brush, "asset_weak_reference", None)
    if wr is None or not getattr(wr, "relative_asset_identifier", ""):
        return None
    return (wr.asset_library_type, wr.asset_library_identifier, wr.relative_asset_identifier)


def _essentials_mesh_sculpt_paths(brush_name: str) -> list[str]:
    """Common relative paths for built-in mesh sculpt brushes (Blender 5.x Essentials)."""
    blend = "essentials_brushes-mesh_sculpt.blend"
    return [
        f"brushes\\{blend}\\Brush\\{brush_name}",
        f"brushes/{blend}/Brush/{brush_name}",
    ]


def _try_asset_activate(library_type: str, library_id: str, relative_id: str) -> bool:
    try:
        ret = bpy.ops.brush.asset_activate(
            asset_library_type=library_type,
            asset_library_identifier=library_id,
            relative_asset_identifier=relative_id,
        )
        return ret == {'FINISHED'}
    except Exception:
        return False


def activate_brush_asset(context: bpy.types.Context, slot: 'WheelBrushSlot') -> bool:
    """Activate the brush described by *slot* using ``bpy.ops.brush.asset_activate``.

    Blender 5.x makes ``Paint.brush`` read-only; assignment is not allowed.
    Bare brush names are not valid ``relative_asset_identifier`` values — we
    resolve paths from the live ``Brush`` data-block or Essentials fallbacks.
    """
    brush = find_brush_for_slot(slot)

    if _slot_stored_path_is_asset_path(slot):
        if _try_asset_activate(
            slot.asset_library_type,
            slot.asset_library_identifier,
            slot.relative_asset_identifier,
        ):
            return True

    if brush is not None:
        triple = _asset_triple_from_brush(brush)
        if triple is not None:
            lt, lid, rid = triple
            if _try_asset_activate(lt, lid, rid):
                return True

        for rid in _essentials_mesh_sculpt_paths(brush.name):
            if _try_asset_activate('ESSENTIALS', '', rid):
                return True

    return False


def get_brush_asset_ref(context: bpy.types.Context):
    """Return the ``AssetWeakReference`` for the active sculpt brush, or None."""
    paint = getattr(context.tool_settings, 'sculpt', None)
    if paint is None:
        return None
    return getattr(paint, 'brush_asset_reference', None)


# ---------------------------------------------------------------------------
# Active brush helper
# ---------------------------------------------------------------------------

def get_active_sculpt_brush(context: bpy.types.Context) -> bpy.types.Brush | None:
    ts = context.tool_settings
    if ts and ts.sculpt:
        return ts.sculpt.brush
    return None


# ---------------------------------------------------------------------------
# Brush asset utils
# ---------------------------------------------------------------------------

# def get_brush_asset(slot: 'WheelBrushSlot') -> bpy.types.AssetWeakReference | None:
    


# ---------------------------------------------------------------------------
# Preview -> GPUTexture
# ---------------------------------------------------------------------------

def get_brush_preview_texture(brush: bpy.types.Brush) -> GPUTexture | None:
    """Return a cached GPUTexture built from *brush*'s preview image.

    The texture is created once per session_uid and reused on subsequent
    calls within the same draw cycle.
    """
    uid = brush.session_uid
    cached = _preview_cache.get(uid)
    if cached is not None:
        return cached

    preview = brush.preview
    if preview is None:
        try:
            preview = brush.preview_ensure()
        except Exception:
            return None
    if preview is None:
        return None

    w, h = preview.image_size
    if w == 0 or h == 0:
        return None

    try:
        pixels = preview.image_pixels_float[:]
        buf = gpu.types.Buffer('FLOAT', len(pixels), pixels)
        tex = GPUTexture((w, h), format='RGBA32F', data=buf)
    except Exception:
        return None

    _preview_cache[uid] = tex
    return tex


def get_brush_asset_preview_texture(context: bpy.types.Context, slot: 'WheelBrushSlot') -> GPUTexture | None:
    if slot.custom_icon_path:
        return get_custom_button_texture(slot.custom_icon_path)
    if slot.asset_library_type == 'ESSENTIALS':
        lib_name = "essentials_brushes-mesh_sculpt.blend"
        lib = bpy.data.libraries.get(lib_name, None)
        if lib:
            lib_path = lib.filepath
        with bpy.data.libraries.load(lib_path, assets_only=True) as (data_from, data_to):
            data_to.brushes = [slot.display_name]
        brush = data_to.brushes[0]
        return get_brush_preview_texture(brush)
    else:
        # backup_brush = get_active_sculpt_brush(context)
        activate_brush_asset(context, slot)
        '''# restore brush
        if backup_brush:
            asset_data: bpy.types.AssetWeakReference = backup_brush.library_weak_reference
            bpy.ops.brush.asset_activate(
                asset_library_type=asset_data.asset_library_type,
                asset_library_identifier=asset_data.asset_library_identifier,
                relative_asset_identifier=asset_data.relative_asset_identifier,
            )'''
    return None
