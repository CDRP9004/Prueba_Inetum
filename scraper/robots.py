"""Parseo simple de robots.txt.

No usamos ``urllib.robotparser`` porque su matching de rutas no soporta bien los
comodines ``*`` que usan bancos como bbva.mx (ej. ``Disallow: *.app.html``). Reglas sin
comodín (ej. ``Disallow: /personas/cards`` en bbva.com.co) se tratan como prefijo, tal
como indica la spec de robots.txt; reglas con ``*`` se evalúan con ``fnmatch``.
"""
from __future__ import annotations

import fnmatch
from pathlib import Path

import requests

from scraper.http_client import get_with_retry

ROBOTS_CACHE_FILENAME = "_robots_cache.txt"


def fetch_disallow_patterns(base_url: str, timeout: int, user_agent: str, cache_dir: Path | None = None) -> list[str]:
    """Descarga robots.txt y devuelve los patrones Disallow del bloque User-agent: *.

    Igual que el sitemap, se cachea localmente para no golpear repetidamente un path
    poco visitado por usuarios reales que el WAF vigila de cerca.
    """
    cache_path = cache_dir / ROBOTS_CACHE_FILENAME if cache_dir else None
    if cache_path and cache_path.exists():
        text = cache_path.read_text(encoding="utf-8")
    else:
        robots_url = base_url.rstrip("/") + "/robots.txt"
        try:
            resp = get_with_retry(robots_url, timeout, user_agent)
        except requests.RequestException:
            return []
        text = resp.text
        if cache_path:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(text, encoding="utf-8")

    patterns: list[str] = []
    applies_to_all = False
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        field, _, value = line.partition(":")
        field = field.strip().lower()
        value = value.strip()

        if field == "user-agent":
            applies_to_all = value == "*"
        elif field == "disallow" and applies_to_all and value:
            patterns.append(value)

    return patterns


def is_path_allowed(path: str, disallow_patterns: list[str]) -> bool:
    for pattern in disallow_patterns:
        if "*" in pattern or "?" in pattern:
            if fnmatch.fnmatch(path, pattern):
                return False
        elif path.startswith(pattern):
            return False
    return True
