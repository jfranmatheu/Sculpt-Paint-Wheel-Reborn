import json
from pathlib import Path

import bpy
from bpy.props import BoolProperty
from bpy.types import Context
from ...globals import GLOBALS, PATHS

from ..ui.btype_ui_base import BType_UIExtra


class BType_AddonPreferences(BType_UIExtra, bpy.types.AddonPreferences):
    bpy_type = bpy.types.AddonPreferences
    first_time: BoolProperty(
        name="First Time",
        description="Internal flag to detect first register after install and restore saved preferences",
        default=True,
        options={"HIDDEN"},
    )

    @classmethod
    def tag_register(cls, **kwargs):
        cls.bl_idname = GLOBALS.ADDON.PACKAGE_NAME
        if not getattr(cls, "bl_label", ""):
            cls.bl_label = GLOBALS.ADDON.NAME
        for key, value in kwargs.items():
            setattr(cls, key, value)
        return cls

    @classmethod
    def get_prefs(cls, context: Context):
        return context.preferences.addons[GLOBALS.ADDON.PACKAGE_NAME].preferences

    @staticmethod
    def _to_jsonable(value):
        if value is None or isinstance(value, (bool, int, float, str)):
            return value
        if isinstance(value, set):
            return list(value)
        if isinstance(value, (list, tuple)):
            return [BType_AddonPreferences._to_jsonable(v) for v in value]
        if hasattr(value, "to_list"):
            return [BType_AddonPreferences._to_jsonable(v) for v in value.to_list()]
        if hasattr(value, "__iter__") and not isinstance(value, dict):
            try:
                return [BType_AddonPreferences._to_jsonable(v) for v in value]
            except Exception:
                pass
        return str(value)

    @classmethod
    def _serialize_rna(cls, data, visited: set[int] | None = None):
        if data is None:
            return None
        if visited is None:
            visited = set()
        ptr = None
        if hasattr(data, "as_pointer"):
            try:
                ptr = int(data.as_pointer())
            except Exception:
                ptr = None
        if ptr is not None and ptr in visited:
            return None
        if ptr is not None:
            visited.add(ptr)

        out = {}
        for prop in data.bl_rna.properties:
            pid = prop.identifier
            if pid == "rna_type":
                continue
            if pid.startswith("bl_") or pid.startswith("_"):
                continue
            try:
                val = getattr(data, pid)
            except Exception:
                continue

            if prop.type == "POINTER":
                if val is None:
                    out[pid] = None
                    continue
                # Serialize nested PropertyGroup/AddonPreferences-like blocks recursively.
                if hasattr(val, "bl_rna") and hasattr(val, "as_pointer"):
                    out[pid] = cls._serialize_rna(val, visited)
                else:
                    out[pid] = cls._to_jsonable(val)
                continue

            if prop.type == "COLLECTION":
                items = []
                for item in val:
                    if hasattr(item, "bl_rna"):
                        items.append(cls._serialize_rna(item, visited))
                    else:
                        items.append(cls._to_jsonable(item))
                out[pid] = items
                continue

            out[pid] = cls._to_jsonable(val)
        return out

    @classmethod
    def _apply_rna(cls, data, payload) -> None:
        if data is None or not isinstance(payload, dict):
            return

        props = getattr(getattr(data, "bl_rna", None), "properties", None)
        if not props:
            return

        for prop in props:
            pid = prop.identifier
            if pid == "rna_type":
                continue
            if pid.startswith("bl_") or pid.startswith("_"):
                continue
            if pid not in payload:
                continue

            val = payload.get(pid)
            try:
                if prop.type == "POINTER":
                    if val is None:
                        continue
                    target = getattr(data, pid)
                    if hasattr(target, "bl_rna") and isinstance(val, dict):
                        cls._apply_rna(target, val)
                    continue

                if prop.type == "COLLECTION":
                    coll = getattr(data, pid)
                    if not isinstance(val, list):
                        continue
                    try:
                        coll.clear()
                    except Exception:
                        pass
                    for item_payload in val:
                        try:
                            item = coll.add()
                        except Exception:
                            break
                        if isinstance(item_payload, dict) and hasattr(item, "bl_rna"):
                            cls._apply_rna(item, item_payload)
                    continue

                # Plain value property.
                setattr(data, pid, val)
            except Exception:
                # Best-effort restore; skip incompatible/removed properties.
                continue

    @classmethod
    def _clear_rna(cls, data, visited: set[int] | None = None) -> None:
        if data is None:
            return
        if visited is None:
            visited = set()
        ptr = None
        if hasattr(data, "as_pointer"):
            try:
                ptr = int(data.as_pointer())
            except Exception:
                ptr = None
        if ptr is not None and ptr in visited:
            return
        if ptr is not None:
            visited.add(ptr)

        for prop in data.bl_rna.properties:
            pid = prop.identifier
            if pid == "rna_type" or prop.is_readonly:
                continue
            if pid.startswith("bl_") or pid.startswith("_"):
                continue
            try:
                val = getattr(data, pid)
            except Exception:
                continue

            if prop.type == "COLLECTION":
                try:
                    val.clear()
                except Exception:
                    pass
                continue

            if prop.type == "POINTER":
                # If pointer targets a nested PropertyGroup-like struct, clear recursively.
                if val is not None and hasattr(val, "bl_rna") and hasattr(val, "as_pointer"):
                    cls._clear_rna(val, visited)
                # Then try requested pointer clear semantic (data.property = None).
                try:
                    setattr(data, pid, None)
                except Exception:
                    pass
                continue

    def to_dict(self) -> dict:
        data = self._serialize_rna(self)
        return data if isinstance(data, dict) else {}

    def save(self, file_path: str | Path | None = None) -> Path:
        path = Path(file_path) if file_path else (Path(PATHS.USER_DATA) / "preferences.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = self.to_dict()
        payload["_metadata_"] = {
            "version": GLOBALS.ADDON.VERSION,
        }
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
        return path

    def load(self, file_path: str | Path | None = None) -> bool:
        path = Path(file_path) if file_path else (Path(PATHS.USER_DATA) / "preferences.json")
        if not path.exists():
            return False
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return False
        if not isinstance(raw, dict):
            return False
        # Ignore metadata keys and apply known RNA properties recursively.
        raw.pop("_metadata_", None)
        self._apply_rna(self, raw)
        return True

    def clear(self) -> None:
        self._clear_rna(self)
