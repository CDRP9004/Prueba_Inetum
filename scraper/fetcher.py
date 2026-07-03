"""Descarga páginas individuales con reintentos y las persiste como HTML crudo."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from scraper.config import ScraperConfig

_UNSAFE_CHARS = re.compile(r"[^a-zA-Z0-9._-]+")


def slugify_url(url: str) -> str:
    """Convierte una URL en un nombre de archivo seguro para data/raw/."""
    parsed = urlparse(url)
    path = parsed.path.strip("/") or "index"
    slug = _UNSAFE_CHARS.sub("__", path)
    if not slug.endswith(".html"):
        slug += ".html"
    return slug


def build_session(config: ScraperConfig) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"User-Agent": config.user_agent})
    return session


@dataclass
class FetchResult:
    url: str
    section: str
    local_path: str | None
    http_status: int | None
    content_length: int
    fetched_at: str
    error: str | None


def fetch_page(session: requests.Session, config: ScraperConfig, url: str, section: str) -> FetchResult:
    fetched_at = datetime.now(timezone.utc).isoformat()
    try:
        resp = session.get(url, timeout=config.timeout_seconds)
    except requests.RequestException as exc:
        return FetchResult(url, section, None, None, 0, fetched_at, error=str(exc))

    if resp.status_code != 200:
        return FetchResult(url, section, None, resp.status_code, len(resp.content), fetched_at,
                            error=f"HTTP {resp.status_code}")

    local_path = config.raw_dir / slugify_url(url)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_bytes(resp.content)

    return FetchResult(
        url=url,
        section=section,
        local_path=str(local_path),
        http_status=resp.status_code,
        content_length=len(resp.content),
        fetched_at=fetched_at,
        error=None,
    )
