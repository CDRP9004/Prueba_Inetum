"""Configuración de la evaluación RAGAS (Fase 13)."""
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
import os

load_dotenv()


@dataclass(frozen=True)
class EvalConfig:
    output_dir: Path = Path(os.getenv("EVAL_OUTPUT_DIR", "eval/output"))
    # Modelo de Ollama usado como juez LLM de RAGAS (por defecto, el mismo que genera
    # las respuestas -- ver limitación documentada en el README sobre usar un juez local).
    judge_model: str = os.getenv("RAGAS_JUDGE_MODEL", os.getenv("LLM_MODEL", "llama3.2:3b"))
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-small")


config = EvalConfig()
