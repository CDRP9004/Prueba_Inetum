"""Orquestación del pipeline RAG.

Patrón Chain of Responsibility: `RAGPipeline` ejecuta una lista ordenada de `PipelineStep`
sobre un `RAGContext` compartido, cada uno mutándolo (retrieval -> rerank opcional ->
generación). La Fase 10 inserta `RerankStep` entre retrieval y generación sin tocar
`RAGPipeline` ni los steps existentes: solo se agrega un step más a la lista.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from rag.config import RagConfig
from rag.llm import OllamaClient
from rag.prompt import SYSTEM_PROMPT, build_user_prompt
from rag.retriever import DenseRetriever, RetrievedChunk, Retriever


@dataclass
class RAGContext:
    question: str
    history: list[tuple[str, str]]
    chunks: list[RetrievedChunk] = field(default_factory=list)
    answer: str = ""


class PipelineStep(Protocol):
    def run(self, context: RAGContext) -> None: ...


class RetrievalStep:
    def __init__(self, retriever: Retriever, top_k: int):
        self._retriever = retriever
        self._top_k = top_k

    def run(self, context: RAGContext) -> None:
        context.chunks = self._retriever.retrieve(context.question, self._top_k)


class GenerationStep:
    def __init__(self, llm_client: OllamaClient):
        self._llm_client = llm_client

    def run(self, context: RAGContext) -> None:
        user_prompt = build_user_prompt(context.question, context.chunks, context.history)
        context.answer = self._llm_client.generate(SYSTEM_PROMPT, user_prompt)


class RAGPipeline:
    def __init__(self, steps: list[PipelineStep]):
        self._steps = steps

    def run(self, question: str, history: list[tuple[str, str]] | None = None) -> RAGContext:
        context = RAGContext(question=question, history=history or [])
        for step in self._steps:
            step.run(context)
        return context


def _build_retriever(config: RagConfig, embedder) -> Retriever:
    if not config.use_hybrid_search:
        return DenseRetriever(embedder)

    from rag.hybrid_retriever import HybridRetriever, build_bm25_index

    return HybridRetriever(
        embedder,
        build_bm25_index(),
        rrf_k=config.rrf_k,
        mmr_lambda=config.mmr_lambda,
        candidate_multiplier=config.retrieval_candidate_multiplier,
    )


def build_default_pipeline(config: RagConfig, embedder) -> RAGPipeline:
    retriever = _build_retriever(config, embedder)
    llm_client = OllamaClient(config)
    steps: list[PipelineStep] = []

    if config.use_reranker:
        from rag.reranker import RerankStep, build_cross_encoder

        retrieval_k = max(config.top_k * config.rerank_candidate_multiplier, config.top_k)
        steps.append(RetrievalStep(retriever, retrieval_k))
        steps.append(RerankStep(build_cross_encoder(config.reranker_model), top_k=config.top_k))
    else:
        steps.append(RetrievalStep(retriever, config.top_k))

    steps.append(GenerationStep(llm_client))
    return RAGPipeline(steps)
