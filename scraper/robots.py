"""Parseo simple de robots.txt.

No usamos ``urllib.robotparser`` porque su matching de rutas no soporta bien los
comodines ``*`` que declara bbva.mx (ej. ``Disallow: *.app.html``, ``Disallow: */icons/*``).
En su lugar traducimos cada regla a un patrón ``fnmatch`` sobre el path de la URL.
"""
from __future__ import annotations

import fnmatch

import requests


def fetch_disallow_patterns(base_url: str, timeout: int, user_agent: str) -> list[str]:
    """Descarga robots.txt y devuelve los patrones Disallow del bloque User-agent: *."""
    robots_url = base_url.rstrip("/") + "/robots.txt"
    try:
        resp = requests.get(robots_url, timeout=timeout, headers={"User-Agent": user_agent})
        resp.raise_for_status()
    except requests.RequestException:
        return []

    patterns: list[str] = []
    applies_to_all = False
    for raw_line in resp.text.splitlines():
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
    return not any(fnmatch.fnmatch(path, pattern) for pattern in disallow_patterns)
