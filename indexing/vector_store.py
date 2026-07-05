"""Cliente de la base de datos vectorial (ChromaDB).

Soporta dos modos, elegidos por `CHROMA_MODE`:

- `persistent` (por defecto, desarrollo local): `PersistentClient` embebido, sin servidor
  aparte, con los datos en `data/chroma/`.
- `http` (Fase 12, docker-compose): `HttpClient` contra el contenedor propio de Chroma.

El resto del código (retrievers, indexador) solo llama a `get_collection()` y no sabe en
qué modo está corriendo.
"""
from __future__ import annotations

from functools import lru_cache

import chromadb
from chromadb.api.models.Collection import Collection

from indexing.config import config


@lru_cache(maxsize=1)
def _client() -> chromadb.ClientAPI:
    if config.chroma_mode == "http":
        return chromadb.HttpClient(host=config.chroma_host, port=config.chroma_port)

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
