"""Configuración de persistencia de historial de conversación (Fase 7)."""
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv
import os

load_dotenv()


@dataclass(frozen=True)
class HistoryConfig:
    db_path: Path = field(default_factory=lambda: Path(os.getenv("HISTORY_DB_PATH", "data/history.db")))
    # N mensajes previos (usuario + asistente) que se incluyen como contexto en cada respuesta
    window_n: int = int(os.getenv("HISTORY_WINDOW_N", "6"))


config = HistoryConfig()
