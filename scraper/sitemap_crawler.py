"""Obtiene y filtra las URLs a scrapear a partir del sitemap oficial del sitio."""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from scraper.config import ScraperConfig
from scraper.http_client import get_with_retry
from scraper.robots import fetch_disallow_patterns, is_path_allowed


@dataclass(frozen=True)
class TargetPage:
    url: str
    section: str


def _fetch_xml(url: str, timeout: int, user_agent: str) -> BeautifulSoup:
    resp = get_with_retry(url, timeout, user_agent)
    return BeautifulSoup(resp.content, "xml")


def _locs_of(container_tags) -> list[str]:
    """Extrae el texto de <loc> dentro de cada tag (<url> o <sitemap>) de la lista."""
    locs = []
    for tag in container_tags:
        loc = tag.find("loc")
        if loc:
            locs.append(loc.get_text(strip=True))
    return locs


SITEMAP_CACHE_FILENAME = "_sitemap_cache.xml"


def fetch_sitemap_urls(config: ScraperConfig) -> list[str]:
    """Descarga el sitemap; si es un índice de sitemaps, sigue cada sub-sitemap.

    El sitemap cambia con poca frecuencia y bbva.com.co lo protege con un WAF que
    penaliza requests repetidas al mismo path poco visitado por usuarios reales. Por
    eso se cachea localmente: solo se vuelve a pedir por red si no existe la copia.
    """
    cache_path = config.raw_dir / SITEMAP_CACHE_FILENAME
    if cache_path.exists():
        soup = BeautifulSoup(cache_path.read_bytes(), "xml")
    else:
        resp = get_with_retry(config.sitemap_url, config.timeout_seconds, config.user_agent)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(resp.content)
        soup = BeautifulSoup(resp.content, "xml")

    url_tags = soup.find_all("url")
    if url_tags:
        return _locs_of(url_tags)

    sitemap_tags = soup.find_all("sitemap")
    all_urls: list[str] = []
    for sub_sitemap_url in _locs_of(sitemap_tags):
        sub_soup = _fetch_xml(sub_sitemap_url, config.timeout_seconds, config.user_agent)
        all_urls.extend(_locs_of(sub_soup.find_all("url")))
    return all_urls


def select_target_pages(config: ScraperConfig) -> list[TargetPage]:
    """Filtra y prioriza las URLs del sitemap según config.sections y robots.txt."""
    all_urls = fetch_sitemap_urls(config)
    disallow_patterns = fetch_disallow_patterns(
        config.base_url, config.timeout_seconds, config.user_agent, cache_dir=config.raw_dir
    )
    allowed_netloc = urlparse(config.base_url).netloc

    by_section: dict[str, list[str]] = {section: [] for section in config.sections}
    seen: set[str] = set()

    for url in all_urls:
        parsed = urlparse(url)
        if parsed.netloc != allowed_netloc:
            continue
        if not is_path_allowed(parsed.path, disallow_patterns):
            continue
        if url in seen:
            continue

        for section in config.sections:
            if parsed.path.startswith(section):
                by_section[section].append(url)
                seen.add(url)
                break

    ordered: list[TargetPage] = []
    for section in config.sections:
        ordered.extend(TargetPage(url=url, section=section) for url in by_section[section])

    return ordered[: config.max_pages]
