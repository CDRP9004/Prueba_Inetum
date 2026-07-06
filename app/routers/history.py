"""Endpoint de lectura del historial de conversación: GET /history/{session_id}."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.dependencies import get_repository
from history.repository import ConversationRepository

logger = logging.getLogger(__name__)
router = APIRouter()


class HistoryMessage(BaseModel):
    role: str
    content: str
    created_at: str


@router.get("/history/{session_id}", response_model=list[HistoryMessage])
def get_history(
    session_id: str, repository: ConversationRepository = Depends(get_repository)
) -> list[HistoryMessage]:
    try:
        messages = repository.get_all_messages(session_id)
    except Exception:
        logger.exception("Error leyendo el historial de la sesión %s", session_id)
        raise HTTPException(status_code=500, detail="No se pudo leer el historial de la sesión.")

    return [
        HistoryMessage(role=m.role, content=m.content, created_at=m.created_at.isoformat())
        for m in messages
    ]
