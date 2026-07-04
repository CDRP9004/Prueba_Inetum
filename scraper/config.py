"""Configuración del scraper, cargada desde variables de entorno (.env)."""
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv
import os

load_dotenv()


def _get_list(key: str, default: str) -> list[str]:
    raw = os.getenv(key, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass(frozen=True)
class ScraperConfig:
    base_url: str = os.getenv("SCRAPER_BASE_URL", "https://www.bbva.mx")
    sitemap_url: str = os.getenv("SCRAPER_SITEMAP_URL", "https://www.bbva.mx/sitemap.xml")
    sections: list[str] = field(default_factory=lambda: _get_list("SCRAPER_SECTIONS", "/personas/,/empresas/"))
    max_pages: int = int(os.getenv("SCRAPER_MAX_PAGES", "150"))
    delay_seconds: float = float(os.getenv("SCRAPER_DELAY_SECONDS", "1.0"))
    timeout_seconds: int = int(os.getenv("SCRAPER_TIMEOUT_SECONDS", "15"))
    user_agent: str = os.getenv(
        "SCRAPER_USER_AGENT",
        "PruebaRAG-BBVA-Bot/1.0 (+contacto: crystyan.davyd@gmail.com; proyecto educativo/prueba tecnica)",
    )
    raw_dir: Path = field(default_factory=lambda: Path(os.getenv("SCRAPER_RAW_DIR", "data/raw")))


config = ScraperConfig()
