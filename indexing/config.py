"""Configuración de chunking, embeddings e indexación vectorial (Fase 4)."""
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv
import os

load_dotenv()


@dataclass(frozen=True)
class IndexingConfig:
    processed_dir: Path = field(default_factory=lambda: Path(os.getenv("CLEANING_PROCESSED_DIR", "data/processed")))
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "1000"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "150"))
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-small")
    chroma_persist_dir: Path = field(default_factory=lambda: Path(os.getenv("CHROMA_PERSIST_DIR", "data/chroma")))
    chroma_collection: str = os.getenv("CHROMA_COLLECTION", "bbva_docs")


config = IndexingConfig()
