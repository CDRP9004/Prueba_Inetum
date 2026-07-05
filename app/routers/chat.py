"""Endpoint conversacional: POST /chat."""
from __future__ import annotations

import logging

import requests
from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_pipeline
from app.schemas import ChatRequest, ChatResponse, SourceItem
from rag.pipeline import RAGPipeline

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, pipeline: RAGPipeline = Depends(get_pipeline)) -> ChatResponse:
    if not request.message.strip():
        raise HTTPException(status_code=422, detail="El mensaje no puede estar vacío.")

    try:
        result = pipeline.run(request.message)
    except requests.exceptions.RequestException:
        logger.exception("No se pudo contactar al servidor de Ollama")
        raise HTTPException(
            status_code=503,
            detail="El modelo de lenguaje no está disponible en este momento. "
            "Verificá que Ollama esté corriendo.",
        )
    except Exception:
        logger.exception("Error inesperado en el pipeline RAG")
        raise HTTPException(status_code=500, detail="Ocurrió un error procesando la pregunta.")

    return ChatResponse(
        answer=result.answer,
        sources=[
            SourceItem(title=chunk.title, url=chunk.url, score=chunk.score) for chunk in result.chunks
        ],
    )
