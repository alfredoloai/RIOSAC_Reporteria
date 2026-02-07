from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path


_slug_re = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
	t = text.strip().lower()
	t = t.replace("ñ", "n")
	t = _slug_re.sub("_", t)
	t = t.strip("_")
	return t or "sin_nombre"


@dataclass(frozen=True)
class RawSaveTarget:
	day_dir: Path
	file_path: Path


def build_raw_target(raw_root: Path, d: date, group_name: str) -> RawSaveTarget:
	yyyy_mm = d.strftime("%Y-%m")
	yyyy_mm_dd = d.strftime("%Y-%m-%d")
	day_dir = raw_root / yyyy_mm / yyyy_mm_dd
	day_dir.mkdir(parents=True, exist_ok=True)

	safe_group = slugify(group_name)
	filename = f"capa_a_raw_{yyyy_mm_dd}_{safe_group}.csv"

	return RawSaveTarget(day_dir=day_dir, file_path=day_dir / filename)
