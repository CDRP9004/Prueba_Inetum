"""CLI de prueba manual del pipeline RAG: uso -> python -m rag.cli "pregunta"

Sirve para validar retrieval + generación antes de exponerlos vía FastAPI (Fase 6).
"""
from __future__ import annotations

import sys

from indexing.config import config as indexing_config
from indexing.embeddings import build_embedder
from rag.config import config as rag_config
from rag.pipeline import build_default_pipeline


def main() -> None:
    if len(sys.argv) < 2:
        print('Uso: python -m rag.cli "tu pregunta"')
        return

    question = " ".join(sys.argv[1:])
    embedder = build_embedder(indexing_config.embedding_model)
    pipeline = build_default_pipeline(rag_config, embedder)

    result = pipeline.run(question)

    print("=== Respuesta ===")
    print(result.answer)
    print("\n=== Fuentes ===")
    for chunk in result.chunks:
        print(f"- {chunk.title} ({chunk.url}) [score={chunk.score:.3f}]")


if __name__ == "__main__":
    main()
