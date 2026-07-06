"""Endpoint conversacional: POST /chat."""
from __future__ import annotations

import logging
import time

import httpx
import requests
from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_pipeline, get_repository
from app.schemas import ChatRequest, ChatResponse, SourceItem
from history.config import config as history_config
from history.repository import ConversationRepository
from observability.tracing import traced_chat_request
from rag.pipeline import RAGPipeline

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    pipeline: RAGPipeline = Depends(get_pipeline),
    repository: ConversationRepository = Depends(get_repository),
) -> ChatResponse:
    if not request.message.strip():
        raise HTTPException(status_code=422, detail="El mensaje no puede estar vacío.")

    history = repository.get_recent_messages(request.session_id, history_config.window_n)

    started_at = time.perf_counter()

    with traced_chat_request(request.session_id, request.message) as root_observation:
        try:
            result = pipeline.run(request.message, history=history)
        except requests.exceptions.RequestException:
            logger.exception("No se pudo contactar al servidor de Ollama")
            raise HTTPException(
                status_code=503,
                detail="El modelo de lenguaje no está disponible en este momento. "
                "Verificá que Ollama esté corriendo.",
            )
        except httpx.ConnectError:
            logger.exception("No se pudo contactar a ChromaDB")
            raise HTTPException(
                status_code=503,
                detail="La base de datos vectorial no está disponible en este momento. "
                "Verificá que ChromaDB esté corriendo.",
            )
        except Exception:
            logger.exception("Error inesperado en el pipeline RAG")
            raise HTTPException(status_code=500, detail="Ocurrió un error procesando la pregunta.")

        if root_observation is not None:
            root_observation.update(output={"answer": result.answer})

    latency_ms = int((time.perf_counter() - started_at) * 1000)

    repository.add_message(request.session_id, "user", request.message)
    repository.add_message(request.session_id, "assistant", result.answer, latency_ms=latency_ms)

    return ChatResponse(
        answer=result.answer,
        sources=[
            SourceItem(title=chunk.title, url=chunk.url, score=chunk.score) for chunk in result.chunks
        ],
    )
