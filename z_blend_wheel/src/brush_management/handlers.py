"""Blender handlers and bootstrap for the brush management system."""

from __future__ import annotations

import traceback

import bpy

from ...core.debug import print_debug
from ...core.globals import GLOBALS


def _load_post_handler(*args) -> None:
    """Check libraries for changes on file load, trigger sync if needed."""
    if GLOBALS.IN_BACKGROUND:
        return
    try:
        from .sync import needs_sync, sync_and_reload
        from .runtime import is_loaded, load_from_disk

        if not is_loaded():
            load_from_disk()

        changed = needs_sync()
        if changed:
            names = ", ".join(name for name, _ in changed)
            print_debug(f"[Sculpt+] Libraries changed: {names} — syncing...")
            ok, err = sync_and_reload(force=False)
            if not ok:
                print_debug(f"[Sculpt+] Sync on load_post failed: {err}")
    except Exception:
        print_debug(f"[Sculpt+] load_post handler error: {traceback.format_exc()}")


def schedule_bootstrap() -> None:
    """Deferred one-shot: load libraries.json (build if missing) after addon enable."""
    if GLOBALS.IN_BACKGROUND:
        return

    def _timer():
        try:
            c = bpy.context
            if c is None:
                return 0.1
            if c.preferences.addons.get(GLOBALS.ADDON.PACKAGE_NAME) is None:
                return 0.1

            from .runtime import is_loaded, load_from_disk
            from .cache import libraries_json_path

            if not libraries_json_path().is_file():
                from .sync import sync_and_reload
                ok, err = sync_and_reload(force=True)
                if not ok:
                    print_debug(f"[Sculpt+] Initial sync failed: {err}")
                    return None
            elif not is_loaded():
                load_from_disk()

            return None
        except Exception:
            print_debug(f"[Sculpt+] bootstrap timer error: {traceback.format_exc()}")
            return None

    bpy.app.timers.register(_timer, first_interval=0.15)


def register_handlers() -> None:
    if GLOBALS.IN_BACKGROUND:
        return
    if _load_post_handler not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_load_post_handler)


def unregister_handlers() -> None:
    if _load_post_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_load_post_handler)
