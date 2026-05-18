import re
import os
import bpy
from bpy.props import FloatVectorProperty, IntProperty, StringProperty
from bpy.types import Brush, AssetWeakReference, Context
from gpu.types import GPUTexture

from ..core.bl_types import PropertyGroup
from ..data.brush_previews import (
    write_preview,
    read_preview,
    read_essential_preview,
    generate_preview_hash,
    get_brush_gputex,
    get_essential_brush_gputex,
)
from ..utils.ups import get_tool_settings, get_active_brush_mode



_MAP_MODE_TO_ESSENTIALS_ASSET_ID = {
    "SCULPT": "mesh_sculpt",
    "WEIGHT": "mesh_weight",
    "PAINT_TEXTURE": "mesh_texture",
    "VERTEX_PAINT": "mesh_vertex",
    "WEIGHT_GREASE_PENCIL": "gp_weight",
    "VERTEX_GREASE_PENCIL": "gp_vertex",
    "PAINT_GREASE_PENCIL": "gp_draw",
    "SCULPT_GREASE_PENCIL": "gp_sculpt",
    "CURVE_SCULPT": "curve_sculpt",
}

def get_essentials_asset_id(mode: str) -> str | None:
    return _MAP_MODE_TO_ESSENTIALS_ASSET_ID.get(mode,  None)


def get_essentials_blend_id_from_relative_path(relative_asset_identifier: str) -> str | None:
    m = re.search(r"essentials_brushes-([^.]+)\.blend", relative_asset_identifier)
    return m.group(1) if m else None


class BrushMetadata(PropertyGroup):
    name: StringProperty(
        name="Name",
        description="Name of the brush metadata",
        default="Brush Metadata",
    )

    mode: StringProperty(
        name="Mode",
        description="Brush mode of the brush metadata",
        default="",
    )

    wheel_order: IntProperty(
        name="Wheel Order",
        description="Order of the brush metadata in the wheel",
        default=-1,
    )

    hash_id: StringProperty(
        name="Hash ID",
        description="Hash ID of the brush metadata",
        default="",
    )
    
    preview_size: FloatVectorProperty(
        name="Preview Size",
        description="Size of the preview image",
        default=(0, 0),
        size=2
    )

    asset_library_type: StringProperty(
        name="Asset Library Type",
        description="Type of the asset library",
        default="Brush",
    )

    asset_library_identifier: StringProperty(
        name="Asset Library Identifier",
        description="Identifier of the asset library",
        default="",
    )

    relative_asset_identifier: StringProperty(
        name="Relative Asset Identifier",
        description="Relative identifier of the asset",
        default="",
    )

    def get_essentials_blend_id(self) -> str | None:
        """Blend library id (e.g. mesh_sculpt) for ESSENTIALS brushes."""
        if self.asset_library_type != "ESSENTIALS":
            return None
        mid = get_essentials_asset_id(self.mode)
        if mid:
            return mid
        return get_essentials_blend_id_from_relative_path(self.relative_asset_identifier)

    @property
    def brush(self) -> Brush:
        return bpy.data.brushes.get(self.name)

    def _resolve_asset_library_root(self) -> str | None:
        if self.asset_library_type == "ESSENTIALS":
            datafiles = bpy.utils.system_resource("DATAFILES")
            if not datafiles:
                return None
            return os.path.join(datafiles, "assets")

        lib_id = self.asset_library_identifier
        if not lib_id:
            return None
        prefs = bpy.context.preferences
        asset_libraries = getattr(prefs.filepaths, "asset_libraries", None)
        if not asset_libraries:
            return None
        for lib in asset_libraries:
            if lib.name == lib_id:
                return lib.path
        return None

    def get_asset_blend_file_abs_path(self) -> str | None:
        rel = (self.relative_asset_identifier or "").replace("\\", "/")
        blend_marker = ".blend/"
        marker_idx = rel.lower().find(blend_marker)
        if marker_idx == -1:
            return None
        blend_rel = rel[: marker_idx + len(".blend")]
        root = self._resolve_asset_library_root()
        if root is None:
            return None
        blend_abs = os.path.normpath(os.path.join(root, blend_rel.replace("/", os.sep)))
        if os.path.isfile(blend_abs):
            return blend_abs
        return None

    def get_any_brush(self) -> Brush | None:
        if brush := self.brush:
            return brush
        blend_abs = self.get_asset_blend_file_abs_path()
        if not blend_abs:
            return None
        brushes = bpy.data.brushes
        try:
            brush = brushes.get((self.name, blend_abs))
            if brush is not None:
                return brush
        except Exception:
            pass
        try:
            return brushes[(self.name, blend_abs)]
        except Exception:
            return None

    @property
    def icon_id(self) -> int:
        brush = self.get_any_brush()
        if brush is None:
            return 0
        preview = brush.preview or brush.preview_ensure()
        if preview is None:
            return 0
        return int(getattr(preview, "icon_id", 0) or 0)

    @property
    def is_brush_loaded(self) -> bool:
        return self.brush is not None

    @property
    def preview_pixels(self) -> list | None:
        """
        Get the preview pixels from disk.
        """
        if self.asset_library_type == "ESSENTIALS":
            essentials_mode_id = self.get_essentials_blend_id()
            if essentials_mode_id is None:
                return None
            if data := read_essential_preview(essentials_mode_id, self.name):
                return data[2]
            return None

        if self.hash_id == "" or self.preview_size == (0, 0):
            return None
        if data := read_preview(self.hash_id):
            return data[2]
        return None

    @property
    def gputex(self) -> GPUTexture | None:
        """
        Get the GPU texture from the preview data.
        """
        if self.asset_library_type == "ESSENTIALS":
            essentials_mode_id = self.get_essentials_blend_id()
            if self.name == "" or essentials_mode_id is None:
                return None
            return get_essential_brush_gputex(essentials_mode_id, self.name)

        if self.hash_id == "" or self.preview_size == (0, 0):
            return None
        return get_brush_gputex(self.hash_id)

    def activate(self) -> None:
        if self.name == "":
            return
        bpy.ops.brush.asset_activate(
            asset_library_type=self.asset_library_type,
            asset_library_identifier=self.asset_library_identifier,
            relative_asset_identifier=self.relative_asset_identifier,
        )
        if self.hash_id == "":
            self.ensure_preview()

    def setup_from_active(self, context: Context) -> bool:
        """
        Set up the brush metadata from the active brush.

        Returns:
            bool: True if the setup was successful, False otherwise (preview not found or tool settings not found).
        """
        ts = get_tool_settings(context)
        if not ts:
            return False

        weak_ref: AssetWeakReference = ts.brush_asset_reference
        self.asset_library_type = weak_ref.asset_library_type
        self.asset_library_identifier = weak_ref.asset_library_identifier
        self.relative_asset_identifier = weak_ref.relative_asset_identifier

        brush: Brush = ts.brush
        self.name = brush.name
        self.mode = get_active_brush_mode(context)

        return self.ensure_preview(brush)

    def setup_from_essential(self, mode: str, brush_name: str) -> bool:
        relative_asset_identifier = get_essentials_asset_id(mode)
        if relative_asset_identifier is None:
            return False
        self.asset_library_type = "ESSENTIALS"
        self.asset_library_identifier = ""
        self.relative_asset_identifier = f"brushes/essentials_brushes-{relative_asset_identifier}.blend/Brush/{brush_name}"
        self.name = brush_name
        self.mode = mode
        return True

    def ensure_preview(self, brush: Brush | None = None) -> bool:
        if brush is None:
            brush = self.brush
        if brush is None:
            return False
        preview = brush.preview
        if not preview:
            preview = brush.preview_ensure()
        if not preview:
            return False
        x, y = preview.image_size
        if x == 0 or y == 0:
            return False
        pixels = preview.image_pixels_float
        if len(pixels) == 0:
            return False
        self.hash_id = generate_preview_hash(self.asset_library_type, self.relative_asset_identifier, self.name, is_essential=self.asset_library_type == "ESSENTIALS")
        self.preview_size = (x, y)
        write_preview(self.hash_id, x, y, pixels)
        return True



'''
weak_ref = C.tool_settings.sculpt.brush_asset_reference
weak_ref.asset_library_identifier
weak_ref.asset_library_type
weak_ref.relative_asset_identifier

p = C.window_manager.operator_properties_last(bpy.ops.brush.asset_activate.idname())
p.asset_library_identifier
p.asset_library_type
p.relative_asset_identifier
'''
