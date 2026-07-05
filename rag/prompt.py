"""Construcción del prompt: instrucciones del sistema + contexto recuperado + historial."""
from __future__ import annotations

from rag.retriever import RetrievedChunk

SYSTEM_PROMPT = """Eres un asistente que responde preguntas sobre los productos y \
servicios de BBVA usando ÚNICAMENTE la información de contexto proporcionada.
Si la respuesta no está en el contexto, dilo explícitamente en vez de inventar datos.
Responde en español, de forma clara y concisa. Cuando sea relevante, menciona de qué \
producto o sección proviene la información."""


def build_context_block(chunks: list[RetrievedChunk]) -> str:
    parts = []
    for i, chunk in enumerate(chunks, start=1):
        parts.append(f"[Fuente {i}: {chunk.title} ({chunk.url})]\n{chunk.text}")
    return "\n\n".join(parts)


def build_user_prompt(
    question: str,
    chunks: list[RetrievedChunk],
    history: list[tuple[str, str]] | None = None,
) -> str:
    """`history` es una lista de tuplas (rol, contenido) de mensajes previos de la sesión,
    ya recortada al tamaño de ventana N configurado (ver history/ en la Fase 7)."""
    sections = []

    if history:
        history_text = "\n".join(f"{role}: {content}" for role, content in history)
        sections.append(f"Historial de la conversación:\n{history_text}")

    sections.append(f"Contexto:\n{build_context_block(chunks)}")
    sections.append(f"Pregunta: {question}")

    return "\n\n".join(sections)
