"""Endpoint de lectura del historial de conversación: GET /history/{session_id}."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.dependencies import get_repository
from history.repository import ConversationRepository

router = APIRouter()


class HistoryMessage(BaseModel):
    role: str
    content: str
    created_at: str


@router.get("/history/{session_id}", response_model=list[HistoryMessage])
def get_history(
    session_id: str, repository: ConversationRepository = Depends(get_repository)
) -> list[HistoryMessage]:
    messages = repository.get_all_messages(session_id)
    return [
        HistoryMessage(role=m.role, content=m.content, created_at=m.created_at.isoformat())
        for m in messages
    ]
