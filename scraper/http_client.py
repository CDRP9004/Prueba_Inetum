"""Cliente HTTP con reintentos para llamadas puntuales (sitemap, robots.txt).

bbva.com.co responde 403 de forma intermitente (bloqueo probabilístico del WAF) incluso
con cabeceras de navegador completas y correctas. Un único 403 no es una señal confiable
de que la URL esté realmente bloqueada, así que reintentamos con backoff antes de asumir
que el recurso no está disponible.
"""
from __future__ import annotations

import time

import requests

from scraper.http_headers import build_headers


def get_with_retry(
    url: str,
    timeout: int,
    user_agent: str,
    attempts: int = 6,
    backoff_seconds: float = 5.0,
) -> requests.Response:
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            resp = requests.get(url, timeout=timeout, headers=build_headers(user_agent))
            if resp.status_code == 200:
                return resp
            last_exc = requests.exceptions.HTTPError(f"HTTP {resp.status_code} for {url}")
        except requests.RequestException as exc:
            last_exc = exc

        if attempt < attempts:
            time.sleep(backoff_seconds * attempt)

    assert last_exc is not None
    raise last_exc
