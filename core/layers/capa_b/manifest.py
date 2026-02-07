from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict


@dataclass
class ProcessedManifest:
    path: Path
    _data: Dict[str, Any] | None = field(default=None, init=False, repr=False)

    def _load(self) -> Dict[str, Any]:
        if self._data is None:
            if self.path.exists():
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
            else:
                self._data = {"processed_raw": {}}
        return self._data

    def _save(self) -> None:
        data = self._load()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _normalize_key(file_path: Path) -> str:
        return str(file_path).replace("\\", "/")

    def is_processed(self, raw_path: Path, raw_mtime: float) -> bool:
        data = self._load()
        key = self._normalize_key(raw_path)
        record = data.get("processed_raw", {}).get(key)
        if not record:
            return False
        try:
            stored_mtime = float(record.get("mtime", -1))
        except (TypeError, ValueError):
            return False
        return stored_mtime == float(raw_mtime)

    def mark_processed(self, raw_path: Path, raw_mtime: float, clean_path: Path) -> None:
        data = self._load()
        data.setdefault("processed_raw", {})
        key = self._normalize_key(raw_path)
        data["processed_raw"][key] = {
            "mtime": float(raw_mtime),
            "clean": self._normalize_key(clean_path),
        }
        self._save()
