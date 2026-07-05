"""Modelo de embeddings usado para indexar y para consultar.

Patrón Factory Method (`build_embedder`): el resto del código depende solo de la interfaz
`Embedder`, no de `sentence-transformers` en concreto. Cambiar de modelo/proveedor (por
ejemplo a un embedding vía API) es un cambio local a este archivo, sin tocar el resto del
pipeline de indexación ni de retrieval.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Protocol

from sentence_transformers import SentenceTransformer


class Embedder(Protocol):
    def embed_passages(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...


class E5Embedder:
    """Wrapper sobre modelos de la familia E5, que requieren prefijos "query: "/"passage: "
    en el texto de entrada para obtener el rendimiento de retrieval esperado."""

    def __init__(self, model_name: str):
        self._model = SentenceTransformer(model_name)

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        prefixed = [f"passage: {t}" for t in texts]
        return self._model.encode(prefixed, normalize_embeddings=True).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self._model.encode(f"query: {text}", normalize_embeddings=True).tolist()


@lru_cache(maxsize=1)
def build_embedder(model_name: str) -> Embedder:
    """Factory Method: crea (y cachea como singleton de facto) el embedder configurado."""
    return E5Embedder(model_name)
