"""Plain data classes for the brush library system (JSON-serializable)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


MAX_BRUSHES_PER_PAGE = 20


@dataclass
class BrushPreviewMeta:
    path: str = ""
    width: int = 0
    height: int = 0
    format: str = "RGBA8"
    compression: str = "zlib"


@dataclass
class BrushData:
    name: str = ""
    type: str = "SCULPT"
    wheel_page: int = 0
    wheel_index: int = 0
    preview: BrushPreviewMeta = field(default_factory=BrushPreviewMeta)

    # Asset activation metadata.
    asset_library_type: str = "LOCAL"
    asset_library_identifier: str = ""
    relative_asset_identifier: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "wheel": {"page": self.wheel_page, "index": self.wheel_index},
            "preview": {
                "path": self.preview.path,
                "width": self.preview.width,
                "height": self.preview.height,
                "format": self.preview.format,
                "compression": self.preview.compression,
            },
            "asset_library_type": self.asset_library_type,
            "asset_library_identifier": self.asset_library_identifier,
            "relative_asset_identifier": self.relative_asset_identifier,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "BrushData":
        wheel = d.get("wheel") or {}
        prev = d.get("preview") or {}
        return cls(
            name=str(d.get("name", "")),
            type=str(d.get("type", "SCULPT")),
            wheel_page=int(wheel.get("page", 0)),
            wheel_index=int(wheel.get("index", 0)),
            preview=BrushPreviewMeta(
                path=str(prev.get("path", "")),
                width=int(prev.get("width", 0)),
                height=int(prev.get("height", 0)),
                format=str(prev.get("format", "RGBA8")),
                compression=str(prev.get("compression", "zlib")),
            ),
            asset_library_type=str(d.get("asset_library_type", "LOCAL")),
            asset_library_identifier=str(d.get("asset_library_identifier", "")),
            relative_asset_identifier=str(d.get("relative_asset_identifier", "")),
        )


@dataclass
class BlendData:
    file_name: str = ""
    path: str = ""
    mtime: float = 0.0
    size: int = 0
    brush_count: int = 0
    brushes: dict[str, BrushData] = field(default_factory=dict)
    user_prefs: dict[str, Any] = field(default_factory=lambda: {
        "active_page": 0,
        "custom_order": [],
        "favorites": [],
    })

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_name": self.file_name,
            "path": self.path,
            "mtime": self.mtime,
            "size": self.size,
            "brush_count": self.brush_count,
            "brushes": {bid: b.to_dict() for bid, b in self.brushes.items()},
            "user_prefs": dict(self.user_prefs),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "BlendData":
        brushes_raw = d.get("brushes") or {}
        brushes = {
            bid: BrushData.from_dict(bdata)
            for bid, bdata in brushes_raw.items()
            if isinstance(bdata, dict)
        }
        return cls(
            file_name=str(d.get("file_name", "")),
            path=str(d.get("path", "")),
            mtime=float(d.get("mtime", 0.0)),
            size=int(d.get("size", 0)),
            brush_count=int(d.get("brush_count", 0)),
            brushes=brushes,
            user_prefs=dict(d.get("user_prefs") or {
                "active_page": 0,
                "custom_order": [],
                "favorites": [],
            }),
        )


@dataclass
class LibraryData:
    name: str = ""
    path: str = ""
    last_scan: float = 0.0
    builtin: bool = False
    blends: dict[str, BlendData] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path,
            "last_scan": self.last_scan,
            "builtin": self.builtin,
            "blends": {bid: b.to_dict() for bid, b in self.blends.items()},
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "LibraryData":
        blends_raw = d.get("blends") or {}
        blends = {
            bid: BlendData.from_dict(bdata)
            for bid, bdata in blends_raw.items()
            if isinstance(bdata, dict)
        }
        return cls(
            name=str(d.get("name", "")),
            path=str(d.get("path", "")),
            last_scan=float(d.get("last_scan", 0.0)),
            builtin=bool(d.get("builtin", False)),
            blends=blends,
        )


@dataclass
class LibrariesIndex:
    version: int = 1
    generated_at: float = 0.0
    libraries: dict[str, LibraryData] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "generated_at": self.generated_at,
            "libraries": {lid: lib.to_dict() for lid, lib in self.libraries.items()},
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "LibrariesIndex":
        libs_raw = d.get("libraries") or {}
        libraries = {
            lid: LibraryData.from_dict(ldata)
            for lid, ldata in libs_raw.items()
            if isinstance(ldata, dict)
        }
        return cls(
            version=int(d.get("version", 1)),
            generated_at=float(d.get("generated_at", 0.0)),
            libraries=libraries,
        )
