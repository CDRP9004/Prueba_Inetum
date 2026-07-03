"""Punto de entrada del scraper: uso -> python -m scraper.run_scraper"""
from __future__ import annotations

import json
import time
from collections import Counter

from tqdm import tqdm

from scraper.config import config
from scraper.fetcher import build_session, fetch_page
from scraper.sitemap_crawler import select_target_pages


def main() -> None:
    print(f"Sitio objetivo: {config.base_url}")
    print(f"Secciones priorizadas: {config.sections}")
    print(f"Límite de páginas: {config.max_pages}\n")

    print("Obteniendo y filtrando URLs del sitemap...")
    pages = select_target_pages(config)
    print(f"{len(pages)} páginas seleccionadas para scraping.\n")

    config.raw_dir.mkdir(parents=True, exist_ok=True)
    session = build_session(config)

    manifest: list[dict] = []
    status_counts: Counter[str] = Counter()

    for page in tqdm(pages, desc="Descargando páginas"):
        result = fetch_page(session, config, page.url, page.section)
        manifest.append(result.__dict__)
        status_counts["ok" if result.error is None else "error"] += 1
        time.sleep(config.delay_seconds)

    manifest_path = config.raw_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nCompletado: {status_counts['ok']} páginas OK, {status_counts['error']} con error.")
    print(f"Manifiesto guardado en: {manifest_path}")


if __name__ == "__main__":
    main()
