"""Dependencias compartidas de FastAPI.

Patrón Singleton (vía `lru_cache`): el embedder y el pipeline RAG cargan un modelo pesado
en memoria, así que se construyen una sola vez por proceso y se reutilizan en cada request
en vez de recrearse por petición.
"""
from functools import lru_cache

from history.repository import ConversationRepository
from indexing.config import config as indexing_config
from indexing.embeddings import build_embedder
from rag.config import config as rag_config
from rag.pipeline import RAGPipeline, build_default_pipeline


@lru_cache(maxsize=1)
def get_pipeline() -> RAGPipeline:
    embedder = build_embedder(indexing_config.embedding_model)
    return build_default_pipeline(rag_config, embedder)


@lru_cache(maxsize=1)
def get_repository() -> ConversationRepository:
    return ConversationRepository()
