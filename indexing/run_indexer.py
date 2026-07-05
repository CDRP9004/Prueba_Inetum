"""Punto de entrada de la indexación: uso -> python -m indexing.run_indexer

Lee las páginas limpias de data/processed/ (generadas por cleaning/run_cleaner.py), las
divide en chunks, calcula sus embeddings y las sube a la colección de ChromaDB. Cada
corrida reconstruye la colección desde cero (simple y determinístico para el alcance de
esta prueba; una indexación incremental quedaría como mejora futura).
"""
from __future__ import annotations

import json

from indexing.chunker import chunk_text
from indexing.config import config
from indexing.embeddings import build_embedder
from indexing.vector_store import get_collection


def _iter_processed_docs():
    for path in sorted(config.processed_dir.glob("*.json")):
        yield json.loads(path.read_text(encoding="utf-8")), path.stem


def main() -> None:
    embedder = build_embedder(config.embedding_model)
    collection = get_collection(reset=True)

    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict] = []

    doc_count = 0
    for doc, slug in _iter_processed_docs():
        chunks = chunk_text(doc["text"], config.chunk_size, config.chunk_overlap)
        for i, chunk in enumerate(chunks):
            ids.append(f"{slug}::{i}")
            documents.append(chunk)
            metadatas.append(
                {
                    "url": doc["url"],
                    "title": doc["title"],
                    "section": doc["section"],
                    "chunk_index": i,
                }
            )
        doc_count += 1

    print(f"Documentos procesados: {doc_count}")
    print(f"Chunks a indexar: {len(documents)}")

    batch_size = 64
    for start in range(0, len(documents), batch_size):
        end = start + batch_size
        embeddings = embedder.embed_passages(documents[start:end])
        collection.add(
            ids=ids[start:end],
            embeddings=embeddings,
            documents=documents[start:end],
            metadatas=metadatas[start:end],
        )
        print(f"  Indexados {min(end, len(documents))}/{len(documents)}")

    print(f"Colección '{config.chroma_collection}' lista en {config.chroma_persist_dir}")


if __name__ == "__main__":
    main()
