"""Métricas agregadas sobre el histórico de conversaciones (Fase 14)."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from history.db import SessionLocal
from history.models import Message
from analytics.keywords import top_keywords


@dataclass
class AnalyticsSummary:
    total_sessions: int
    total_messages: int
    total_user_messages: int
    total_assistant_messages: int
    avg_messages_per_session: float
    avg_latency_ms: float | None
    p95_latency_ms: float | None
    messages_per_day: dict[str, int] = field(default_factory=dict)
    top_keywords: list[tuple[str, int]] = field(default_factory=list)
    first_message_at: str | None = None
    last_message_at: str | None = None


def _percentile(sorted_values: list[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    idx = min(int(len(sorted_values) * pct), len(sorted_values) - 1)
    return sorted_values[idx]


def compute_summary(top_n_keywords: int = 15) -> AnalyticsSummary:
    with SessionLocal() as session:
        messages = session.query(Message).order_by(Message.created_at.asc()).all()

    if not messages:
        return AnalyticsSummary(
            total_sessions=0,
            total_messages=0,
            total_user_messages=0,
            total_assistant_messages=0,
            avg_messages_per_session=0.0,
            avg_latency_ms=None,
            p95_latency_ms=None,
        )

    sessions = {m.session_id for m in messages}
    user_messages = [m for m in messages if m.role == "user"]
    assistant_messages = [m for m in messages if m.role == "assistant"]
    latencies = sorted(m.latency_ms for m in assistant_messages if m.latency_ms is not None)

    per_day: Counter[str] = Counter(m.created_at.date().isoformat() for m in messages)

    return AnalyticsSummary(
        total_sessions=len(sessions),
        total_messages=len(messages),
        total_user_messages=len(user_messages),
        total_assistant_messages=len(assistant_messages),
        avg_messages_per_session=len(messages) / len(sessions),
        avg_latency_ms=(sum(latencies) / len(latencies)) if latencies else None,
        p95_latency_ms=_percentile(latencies, 0.95) if latencies else None,
        messages_per_day=dict(sorted(per_day.items())),
        top_keywords=top_keywords([m.content for m in user_messages], top_n=top_n_keywords),
        first_message_at=messages[0].created_at.isoformat(),
        last_message_at=messages[-1].created_at.isoformat(),
    )
