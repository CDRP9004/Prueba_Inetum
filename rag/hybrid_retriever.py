"""Retrieval híbrido (denso + BM25 con Reciprocal Rank Fusion) y diversificación MMR.

Implementa la misma interfaz `Retriever` que `DenseRetriever` (patrón Strategy definido en
`rag/retriever.py`), así que el pipeline puede usar uno u otro según `USE_HYBRID_SEARCH` sin
cambios en `RAGPipeline`.

- **BM25** aporta recall léxico (nombres exactos de productos, siglas) que el embedding
  puede diluir.
- **RRF** combina los rankings de ambos métodos sin necesitar normalizar sus escalas de
  score (que no son comparables entre sí).
- **MMR** re-ordena los candidatos fusionados priorizando diversidad, para no devolver
  varios chunks casi idénticos de una misma página en el top-k final.
"""
from __future__ import annotations

import re
from functools import lru_cache

import numpy as np
from rank_bm25 import BM25Okapi

from indexing.embeddings import Embedder
from indexing.vector_store import get_collection
from rag.retriever import RetrievedChunk

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class BM25Index:
    """Índice BM25 en memoria construido a partir de todos los chunks de la colección."""

    def __init__(self):
        result = get_collection().get(include=["documents", "metadatas"])
        self._ids = result["ids"]
        self._documents = result["documents"]
        self._metadatas = result["metadatas"]
        self._bm25 = BM25Okapi([_tokenize(doc) for doc in self._documents])

    def search(self, query: str, top_k: int) -> list[str]:
        """IDs de los top_k chunks más relevantes por BM25, ordenados de mejor a peor."""
        scores = self._bm25.get_scores(_tokenize(query))
        ranked_indices = np.argsort(scores)[::-1][:top_k]
        return [self._ids[i] for i in ranked_indices]


@lru_cache(maxsize=1)
def build_bm25_index() -> BM25Index:
    return BM25Index()


def _reciprocal_rank_fusion(rank_lists: list[list[str]], k: int) -> dict[str, float]:
    scores: dict[str, float] = {}
    for ranked_ids in rank_lists:
        for rank, doc_id in enumerate(ranked_ids):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1 / (k + rank + 1)
    return scores


def _cosine_similarity(a, b) -> float:
    a, b = np.asarray(a), np.asarray(b)
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) or 1e-9
    return float(np.dot(a, b) / denom)


def _mmr_select(query_embedding, candidates: list[dict], top_k: int, lambda_mult: float) -> list[dict]:
    selected: list[dict] = []
    remaining = list(candidates)

    while remaining and len(selected) < top_k:
        def mmr_score(candidate: dict) -> float:
            relevance = _cosine_similarity(query_embedding, candidate["embedding"])
            if not selected:
                return relevance
            diversity_penalty = max(_cosine_similarity(candidate["embedding"], s["embedding"]) for s in selected)
            return lambda_mult * relevance - (1 - lambda_mult) * diversity_penalty

        best = max(remaining, key=mmr_score)
        selected.append(best)
        remaining.remove(best)

    return selected


class HybridRetriever:
    def __init__(
        self,
        embedder: Embedder,
        bm25_index: BM25Index,
        rrf_k: int = 60,
        mmr_lambda: float = 0.5,
        candidate_multiplier: int = 4,
    ):
        self._embedder = embedder
        self._bm25_index = bm25_index
        self._rrf_k = rrf_k
        self._mmr_lambda = mmr_lambda
        self._candidate_multiplier = candidate_multiplier

    def retrieve(self, query: str, top_k: int) -> list[RetrievedChunk]:
        n_candidates = top_k * self._candidate_multiplier
        collection = get_collection()
        query_embedding = self._embedder.embed_query(query)

        dense_ids = collection.query(query_embeddings=[query_embedding], n_results=n_candidates)["ids"][0]
        bm25_ids = self._bm25_index.search(query, n_candidates)

        rrf_scores = _reciprocal_rank_fusion([dense_ids, bm25_ids], k=self._rrf_k)
        fused_ids = sorted(rrf_scores, key=rrf_scores.get, reverse=True)[:n_candidates]
        if not fused_ids:
            return []

        fetched = collection.get(ids=fused_ids, include=["documents", "metadatas", "embeddings"])
        candidates = [
            {"id": doc_id, "text": doc, "metadata": meta, "embedding": emb, "rrf_score": rrf_scores[doc_id]}
            for doc_id, doc, meta, emb in zip(
                fetched["ids"], fetched["documents"], fetched["metadatas"], fetched["embeddings"]
            )
        ]

        selected = _mmr_select(query_embedding, candidates, top_k, self._mmr_lambda)

        return [
            RetrievedChunk(
                text=c["text"],
                url=c["metadata"]["url"],
                title=c["metadata"]["title"],
                section=c["metadata"]["section"],
                score=c["rrf_score"],
            )
            for c in selected
        ]
