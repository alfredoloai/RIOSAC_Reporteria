from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from core.layers.capa_b.cleaner import clean_part1
from core.layers.capa_b.manifest import ProcessedManifest

RAW_DIR = Path("data/raw")
CLEAN_DIR = Path("data/clean")
MANIFEST_PATH = Path("data/manifests/capa_b_processed.json")


def raw_to_clean_path(raw_path: Path) -> Path:
    relative = raw_path.relative_to(RAW_DIR)
    return CLEAN_DIR / relative


def list_raw_csvs() -> list[Path]:
    if not RAW_DIR.exists():
        return []
    return sorted(p for p in RAW_DIR.rglob("*.csv") if p.is_file())


def main() -> None:
    parser = argparse.ArgumentParser(description="Limpia capa B a partir de raw pendientes.")
    parser.add_argument("--force", action="store_true", help="Reprocesa aunque exista manifest válido.")
    args = parser.parse_args()

    manifest = ProcessedManifest(MANIFEST_PATH)
    raw_files = list_raw_csvs()

    if not raw_files:
        print("No hay CSV en data/raw.")
        return

    processed = 0
    skipped_existing = 0
    skipped_manifest = 0
    missing_clean = 0
    failed = 0

    for raw_path in raw_files:
        clean_path = raw_to_clean_path(raw_path)
        raw_mtime = raw_path.stat().st_mtime
        clean_exists = clean_path.exists()
        manifest_hit = manifest.is_processed(raw_path, raw_mtime)

        if not clean_exists:
            missing_clean += 1

        if not args.force and clean_exists:
            if manifest_hit:
                skipped_manifest += 1
            else:
                manifest.mark_processed(raw_path, raw_mtime, clean_path)
                skipped_existing += 1
            continue

        try:
            df_raw = pd.read_csv(raw_path, dtype=str, keep_default_na=False)
            df_clean = clean_part1(df_raw)
        except Exception as exc:
            failed += 1
            print(f"[ERROR] {raw_path}: {exc}")
            continue

        clean_path.parent.mkdir(parents=True, exist_ok=True)
        df_clean.to_csv(clean_path, index=False, encoding="utf-8-sig")
        manifest.mark_processed(raw_path, raw_mtime, clean_path)
        processed += 1

    print(f"Procesados: {processed}")
    print(f"Saltados (clean existente): {skipped_existing}")
    print(f"Saltados (manifest): {skipped_manifest}")
    print(f"Raw sin clean al inicio: {missing_clean}")
    print(f"Fallidos: {failed}")


if __name__ == "__main__":
    main()
