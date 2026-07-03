"""Punto de entrada de la limpieza: uso -> python -m cleaning.run_cleaner

Lee data/raw/manifest.json (generado por scraper/run_scraper.py), limpia cada página
descargada exitosamente y guarda el resultado como JSON en data/processed/.
"""
from __future__ import annotations

import json
from pathlib import Path

from cleaning.config import config
from cleaning.html_cleaner import clean_html


def _processed_path(local_html_path: str) -> Path:
    slug = Path(local_html_path).stem
    return config.processed_dir / f"{slug}.json"


def main() -> None:
    manifest_path = config.raw_dir / "manifest.json"
    if not manifest_path.exists():
        print(f"No se encontró {manifest_path}. Corré primero: python -m scraper.run_scraper")
        return

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    config.processed_dir.mkdir(parents=True, exist_ok=True)

    cleaned, skipped_short, skipped_error = 0, 0, 0

    for entry in manifest:
        if entry.get("error") or not entry.get("local_path"):
            skipped_error += 1
            continue

        html = Path(entry["local_path"]).read_bytes()
        page = clean_html(html)

        if len(page.text) < config.min_text_length:
            skipped_short += 1
            continue

        out_path = _processed_path(entry["local_path"])
        out_path.write_text(
            json.dumps(
                {
                    "url": entry["url"],
                    "section": entry["section"],
                    "title": page.title,
                    "fetched_at": entry["fetched_at"],
                    "text": page.text,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        cleaned += 1

    print(f"Limpiadas: {cleaned}")
    print(f"Omitidas por texto muy corto (< {config.min_text_length} chars): {skipped_short}")
    print(f"Omitidas por error de descarga: {skipped_error}")


if __name__ == "__main__":
    main()
