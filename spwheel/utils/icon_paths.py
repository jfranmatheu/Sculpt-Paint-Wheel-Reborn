"""Portable paths for the bundled custom-button icons.

Button icons are stored as file paths in the preferences (and preferences.json). A bundled icon stored as the full
path into the add-on's install folder breaks when the install moves (a new Blender version with copied settings,
another extensions repository, preferences restored on another machine), and keeps showing the old copy after an
update. Bundled icons are stored as ``builtin:<file name>`` instead, resolved against the current install. Other
paths (the user's own images) are kept as they are.
"""

from __future__ import annotations

from pathlib import Path

from ..core.globals import PATHS

BUILTIN_PREFIX = "builtin:"
BUILTIN_DIR: Path = PATHS.ASSETS / "images" / "custom_buttons"


def to_portable(path: str) -> str:
    """``builtin:<name>`` for a path into the bundled icons folder of any install (when the current install has that
    icon); any other path unchanged."""
    if not path or path.startswith(BUILTIN_PREFIX):
        return path
    p = Path(path.replace("\\", "/"))
    parents = [part.lower() for part in p.parts[-4:-1]]
    if parents == ["assets", "images", "custom_buttons"] and (BUILTIN_DIR / p.name).is_file():
        return BUILTIN_PREFIX + p.name
    return path


def resolve(path: str) -> str:
    """The file path to load for a stored icon path."""
    if path.startswith(BUILTIN_PREFIX):
        return str(BUILTIN_DIR / path[len(BUILTIN_PREFIX):])
    return path


def builtin_name(path: str) -> str | None:
    """File stem of a bundled icon (portable or full path), else None."""
    portable = to_portable(path)
    if portable.startswith(BUILTIN_PREFIX):
        return Path(portable[len(BUILTIN_PREFIX):]).stem
    return None
