"""Deterministic ID generation for libraries, blends, brushes, and previews."""

from __future__ import annotations

import hashlib
from pathlib import Path


def library_id(library_path: str | Path) -> str:
    """Stable hash for an asset library directory path."""
    key = str(Path(library_path).resolve())
    return hashlib.sha1(key.encode("utf-8")).hexdigest()


def blend_id(blend_path: str | Path, mtime: float, size: int) -> str:
    """Hash that changes when file is modified (mtime or size change)."""
    key = f"{Path(blend_path).resolve()}|{mtime}|{size}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()


def brush_id(blend_path: str | Path, brush_name: str) -> str:
    """Stable hash for a brush within a blend file (name-dependent, not time-dependent)."""
    key = f"{Path(blend_path).resolve()}|{brush_name}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()


def preview_hash(library_name: str, blend_stem: str, brush_name: str) -> str:
    """Filename hash for a preview .bin file."""
    key = f"{library_name}|{blend_stem}|{brush_name}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()


def preview_relative_path(hash_id: str) -> str:
    """Subdirectory path: ``previews/ab/cd/abcdef...bin``."""
    return f"previews/{hash_id[:2]}/{hash_id[2:4]}/{hash_id}.bin"
