"""Divide texto limpio en chunks solapados, respetando límites de párrafo cuando es posible.

Se usa una estrategia simple por caracteres (no por tokens): es suficiente para el alcance
de esta prueba y evita depender de un tokenizer específico del modelo de embeddings/LLM.
"""
from __future__ import annotations


def _split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in text.split("\n") if p.strip()]


def _hard_split(paragraph: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Divide un párrafo más largo que chunk_size en trozos de tamaño fijo con solape."""
    step = max(chunk_size - chunk_overlap, 1)
    return [paragraph[i : i + chunk_size] for i in range(0, len(paragraph), step)]


def chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Agrupa párrafos en chunks de hasta `chunk_size` caracteres, con `chunk_overlap`
    caracteres de solape entre chunks consecutivos para no cortar contexto a la mitad."""
    chunks: list[str] = []
    buffer = ""

    for paragraph in _split_paragraphs(text):
        if len(paragraph) > chunk_size:
            if buffer:
                chunks.append(buffer)
                buffer = ""
            chunks.extend(_hard_split(paragraph, chunk_size, chunk_overlap))
            continue

        candidate = f"{buffer}\n{paragraph}" if buffer else paragraph
        if len(candidate) <= chunk_size:
            buffer = candidate
        else:
            chunks.append(buffer)
            overlap_tail = buffer[-chunk_overlap:] if chunk_overlap else ""
            buffer = f"{overlap_tail}\n{paragraph}" if overlap_tail else paragraph

    if buffer:
        chunks.append(buffer)

    return chunks
