"""Cliente de la base de datos vectorial (ChromaDB), en modo persistente local.

Se usa `PersistentClient` (embebido, sin servidor aparte) para desarrollo; en la Fase 12
(dockerización) se podrá pasar a `HttpClient` apuntando a un contenedor de Chroma sin tocar
el resto del código, ya que todo el acceso pasa por `get_collection()`.
"""
from __future__ import annotations

from functools import lru_cache

import chromadb
from chromadb.api.models.Collection import Collection

from indexing.config import config


@lru_cache(maxsize=1)
def _client() -> chromadb.ClientAPI:
    config.chroma_persist_dir.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(config.chroma_persist_dir))


def get_collection(reset: bool = False) -> Collection:
    client = _client()
    if reset:
        try:
            client.delete_collection(config.chroma_collection)
        except Exception:
            pass  # la colección todavía no existe en la primera corrida
    return client.get_or_create_collection(
        name=config.chroma_collection,
        metadata={"hnsw:space": "cosine"},
    )
