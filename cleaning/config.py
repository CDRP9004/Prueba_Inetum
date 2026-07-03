"""Configuración de la fase de limpieza, cargada desde variables de entorno (.env)."""
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv
import os

load_dotenv()


@dataclass(frozen=True)
class CleaningConfig:
    raw_dir: Path = field(default_factory=lambda: Path(os.getenv("SCRAPER_RAW_DIR", "data/raw")))
    processed_dir: Path = field(default_factory=lambda: Path(os.getenv("CLEANING_PROCESSED_DIR", "data/processed")))
    min_text_length: int = int(os.getenv("CLEANING_MIN_TEXT_LENGTH", "200"))


config = CleaningConfig()
