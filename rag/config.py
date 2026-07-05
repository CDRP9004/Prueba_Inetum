"""Configuración del pipeline RAG (Fase 5): retrieval y generación."""
from dataclasses import dataclass

from dotenv import load_dotenv
import os

load_dotenv()


@dataclass(frozen=True)
class RagConfig:
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    llm_model: str = os.getenv("LLM_MODEL", "llama3.2:3b")
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    top_k: int = int(os.getenv("RAG_TOP_K", "5"))
    llm_timeout_seconds: int = int(os.getenv("LLM_TIMEOUT_SECONDS", "120"))


config = RagConfig()
