"""Configuración de observabilidad con Langfuse (Fase 11)."""
from dataclasses import dataclass

from dotenv import load_dotenv
import os

load_dotenv()


@dataclass(frozen=True)
class ObservabilityConfig:
    public_key: str = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    secret_key: str = os.getenv("LANGFUSE_SECRET_KEY", "")
    host: str = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

    @property
    def keys_configured(self) -> bool:
        return bool(self.public_key and self.secret_key)


config = ObservabilityConfig()
