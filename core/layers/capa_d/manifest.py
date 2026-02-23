from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any


@dataclass
class ProcessedManifest:
    path: Path
    _data: Dict[str, Any] | None = field(default=None, init=False, repr=False)

    def _load(self) -> Dict[str, Any]:
        if self._data is None:
            if self.path.exists():
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
            else:
                self._data = {"processed_ids": []}
        return self._data

    def _save(self) -> None:
        data = self._load()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def is_processed(self, order_id: str) -> bool:
        data = self._load()
        processed = data.get("processed_ids", [])
        return order_id in processed

    def mark_processed(self, order_id: str) -> None:
        data = self._load()
        processed = data.setdefault("processed_ids", [])
        if order_id not in processed:
            processed.append(order_id)
            self._save()
