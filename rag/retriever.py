"""Retrieval de chunks relevantes para una pregunta.

Patrón Strategy: `Retriever` es la interfaz que usa el pipeline; `DenseRetriever` es la
primera implementación (búsqueda vectorial pura). La Fase 9 añade `HybridRetriever`
(dense + BM25 con Reciprocal Rank Fusion) implementando la misma interfaz, de forma que
`RAGPipeline` pueda intercambiarlas por configuración sin cambiar su propio código.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from indexing.embeddings import Embedder
from indexing.vector_store import get_collection


@dataclass(frozen=True)
class RetrievedChunk:
    text: str
    url: str
    title: str
    section: str
    score: float


class Retriever(Protocol):
    def retrieve(self, query: str, top_k: int) -> list[RetrievedChunk]: ...


class DenseRetriever:
    def __init__(self, embedder: Embedder):
        self._embedder = embedder

    def retrieve(self, query: str, top_k: int) -> list[RetrievedChunk]:
        collection = get_collection()
        query_embedding = self._embedder.embed_query(query)
        result = collection.query(query_embeddings=[query_embedding], n_results=top_k)

        chunks: list[RetrievedChunk] = []
        documents = result["documents"][0]
        metadatas = result["metadatas"][0]
        distances = result["distances"][0]

        for text, meta, distance in zip(documents, metadatas, distances):
            chunks.append(
                RetrievedChunk(
                    text=text,
                    url=meta["url"],
                    title=meta["title"],
                    section=meta["section"],
                    score=1 - distance,  # distancia coseno -> similitud (mayor es mejor)
                )
            )
        return chunks
