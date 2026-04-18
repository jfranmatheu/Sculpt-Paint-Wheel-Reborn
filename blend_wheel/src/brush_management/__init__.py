"""Brush management system — library sync, caching, previews, runtime."""

from .models import (
    BrushData,
    BrushPreviewMeta,
    BlendData,
    LibraryData,
    LibrariesIndex,
    PageData,
    MAX_BRUSHES_PER_PAGE,
)
from .ids import library_id, blend_id, brush_id, preview_hash, preview_relative_path
from .cache import (
    cache_dir,
    libraries_json_path,
    previews_dir,
    ensure_cache_dirs,
    load_libraries_index,
    save_libraries_index,
    clean_library_previews,
)
from .previews import (
    write_preview_bin,
    read_preview_bin,
    get_brush_preview_texture,
    clear_texture_cache,
)
from .runtime import (
    is_loaded,
    get_index,
    load_from_disk,
    save_to_disk,
    set_index,
    reset,
    list_library_blend_keys,
    blend_file_display_title,
    get_brushes_for_blend,
    get_all_brushes_for_blend,
    page_count_for_blend,
    get_page_name,
    get_user_prefs_for_blend,
    set_user_pref,
    activate_brush,
    get_active_sculpt_brush,
    active_brush_index_in_list,
)
from .sync import needs_sync, run_sync_background, sync_and_reload
from .handlers import schedule_bootstrap, register_handlers, unregister_handlers


def register() -> None:
    from ..core.globals import GLOBALS
    if GLOBALS.IN_BACKGROUND:
        return
    register_handlers()
    schedule_bootstrap()


def unregister() -> None:
    unregister_handlers()
    reset()
