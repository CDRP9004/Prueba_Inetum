"""Instrumentación de pasos del pipeline RAG con Langfuse.

Patrón Decorator (estructural): `TracedStep` envuelve cualquier `PipelineStep` (ver
`rag/pipeline.py`) agregándole la responsabilidad de emitir una observación de Langfuse
(span/retriever/generation) alrededor de su ejecución, sin modificar el step envuelto ni
`RAGPipeline`. Si Langfuse no está configurado, `run()` delega directo al step envuelto:
cero overhead y cero acoplamiento cuando la observabilidad está apagada.
"""
from __future__ import annotations

from typing import Literal

from rag.pipeline import PipelineStep, RAGContext
from observability.langfuse_client import get_langfuse_client

ObservationType = Literal["span", "retriever", "generation"]


class TracedStep:
    def __init__(self, step: PipelineStep, name: str, as_type: ObservationType = "span"):
        self._step = step
        self._name = name
        self._as_type = as_type

    def run(self, context: RAGContext) -> None:
        client = get_langfuse_client()
        if client is None:
            self._step.run(context)
            return

        with client.start_as_current_observation(
            name=self._name, as_type=self._as_type, input={"question": context.question}
        ) as observation:
            self._step.run(context)
            observation.update(output=self._build_output(context))

    def _build_output(self, context: RAGContext) -> dict:
        if self._as_type == "generation":
            return {"answer": context.answer}
        return {
            "chunks": [
                {"title": chunk.title, "url": chunk.url, "score": chunk.score} for chunk in context.chunks
            ]
        }
