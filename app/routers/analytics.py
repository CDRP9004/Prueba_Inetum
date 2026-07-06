"""Endpoint de analítica del histórico de conversaciones: GET /analytics/summary."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from analytics.metrics import compute_summary

logger = logging.getLogger(__name__)
router = APIRouter()


class AnalyticsSummaryResponse(BaseModel):
    total_sessions: int
    total_messages: int
    total_user_messages: int
    total_assistant_messages: int
    avg_messages_per_session: float
    avg_latency_ms: float | None
    p95_latency_ms: float | None
    messages_per_day: dict[str, int]
    top_keywords: list[list]  # [[palabra, conteo], ...] (JSON no soporta tuplas)
    first_message_at: str | None
    last_message_at: str | None


@router.get("/analytics/summary", response_model=AnalyticsSummaryResponse)
def analytics_summary() -> AnalyticsSummaryResponse:
    try:
        summary = compute_summary()
    except Exception:
        logger.exception("Error calculando el resumen de analítica")
        raise HTTPException(status_code=500, detail="No se pudo calcular la analítica del histórico.")

    return AnalyticsSummaryResponse(
        total_sessions=summary.total_sessions,
        total_messages=summary.total_messages,
        total_user_messages=summary.total_user_messages,
        total_assistant_messages=summary.total_assistant_messages,
        avg_messages_per_session=summary.avg_messages_per_session,
        avg_latency_ms=summary.avg_latency_ms,
        p95_latency_ms=summary.p95_latency_ms,
        messages_per_day=summary.messages_per_day,
        top_keywords=[[word, count] for word, count in summary.top_keywords],
        first_message_at=summary.first_message_at,
        last_message_at=summary.last_message_at,
    )
