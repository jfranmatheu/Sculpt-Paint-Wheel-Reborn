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
    preview: BrushPreviewMeta = field(default_factory=BrushPreviewMeta)

    # Asset activation metadata.
    asset_library_type: str = "LOCAL"
    asset_library_identifier: str = ""
    relative_asset_identifier: str = ""

    # Legacy v1 JSON only (ignored when pages present on blend).
    wheel_page: int = 0
    wheel_index: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
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
        prev = d.get("preview") or {}
        wheel = d.get("wheel") or {}
        return cls(
            name=str(d.get("name", "")),
            type=str(d.get("type", "SCULPT")),
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
            wheel_page=int(wheel.get("page", 0)),
            wheel_index=int(wheel.get("index", 0)),
        )


@dataclass
class PageData:
    """One wheel page: display name + ordered brush ids (keys of ``BlendData.brushes``)."""

    name: str = ""
    brush_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "brushes": list(self.brush_ids)}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "PageData":
        raw = d.get("brushes") or []
        ids: list[str] = []
        if isinstance(raw, list):
            for x in raw:
                if isinstance(x, str):
                    ids.append(x)
                elif x is not None:
                    ids.append(str(x))
        return cls(name=str(d.get("name", "")), brush_ids=ids)


def _pages_from_legacy_wheel(brushes: dict[str, BrushData]) -> list[PageData]:
    """v1: build synthetic pages from per-brush ``wheel`` page/index."""
    if not brushes:
        return []
    rows: list[tuple[int, int, str]] = []
    for bid, b in brushes.items():
        rows.append((b.wheel_page, b.wheel_index, bid))
    rows.sort(key=lambda t: (t[0], t[1], t[2].lower()))
    if not rows:
        return []
    max_p = max(r[0] for r in rows)
    out: list[PageData] = []
    for p in range(max_p + 1):
        ids = [bid for (wp, _wi, bid) in rows if wp == p]
        if ids:
            out.append(PageData(name=f"Page {p + 1}", brush_ids=ids))
    return out


@dataclass
class BlendData:
    file_name: str = ""
    path: str = ""
    mtime: float = 0.0
    size: int = 0
    brush_count: int = 0
    brushes: dict[str, BrushData] = field(default_factory=dict)
    pages: list[PageData] = field(default_factory=list)
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
            "pages": [p.to_dict() for p in self.pages],
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
        pages_raw = d.get("pages")
        pages: list[PageData] = []
        if isinstance(pages_raw, list) and pages_raw:
            for p in pages_raw:
                if isinstance(p, dict):
                    pages.append(PageData.from_dict(p))
        elif brushes:
            pages = _pages_from_legacy_wheel(brushes)

        return cls(
            file_name=str(d.get("file_name", "")),
            path=str(d.get("path", "")),
            mtime=float(d.get("mtime", 0.0)),
            size=int(d.get("size", 0)),
            brush_count=int(d.get("brush_count", 0)),
            brushes=brushes,
            pages=pages,
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
