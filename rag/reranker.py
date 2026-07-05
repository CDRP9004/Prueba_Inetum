"""Reranker: reordena los candidatos recuperados con un cross-encoder antes de generar.

Un cross-encoder evalúa el par (pregunta, chunk) directamente -mucho más preciso que la
similitud de embeddings, que evalúa cada texto por separado- a costa de ser más lento, por
lo que solo se aplica sobre un conjunto acotado de candidatos (no sobre toda la colección).
Se usa `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`: multilingüe (incluye español vía
mMARCO) y lo bastante liviano para correr en CPU.

`RerankStep` implementa la interfaz `PipelineStep` (ver `rag/pipeline.py`), por lo que se
inserta en la cadena entre retrieval y generación sin modificar `RAGPipeline`.
"""
from __future__ import annotations

from dataclasses import replace
from functools import lru_cache

from sentence_transformers import CrossEncoder

from rag.pipeline import RAGContext
from rag.retriever import RetrievedChunk


@lru_cache(maxsize=1)
def build_cross_encoder(model_name: str) -> CrossEncoder:
    return CrossEncoder(model_name)


class RerankStep:
    def __init__(self, cross_encoder: CrossEncoder, top_k: int):
        self._cross_encoder = cross_encoder
        self._top_k = top_k

    def run(self, context: RAGContext) -> None:
        if not context.chunks:
            return

        pairs = [(context.question, chunk.text) for chunk in context.chunks]
        scores = self._cross_encoder.predict(pairs)

        reranked = [
            replace(chunk, score=float(score)) for chunk, score in sorted(
                zip(context.chunks, scores), key=lambda pair: pair[1], reverse=True
            )
        ]
        context.chunks = reranked[: self._top_k]
