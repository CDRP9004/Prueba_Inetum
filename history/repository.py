"""Acceso a datos del historial de conversación.

Patrón Repository: el resto de la aplicación (endpoints de la API, pipeline RAG) habla con
`ConversationRepository`, no con SQLAlchemy directamente. Cambiar el motor de persistencia
(por ejemplo, de SQLite a Postgres) es un cambio local a este módulo.
"""
from __future__ import annotations

from typing import Optional

from history.db import SessionLocal
from history.models import Message


class ConversationRepository:
    def add_message(
        self, session_id: str, role: str, content: str, latency_ms: Optional[int] = None
    ) -> None:
        with SessionLocal() as session:
            session.add(Message(session_id=session_id, role=role, content=content, latency_ms=latency_ms))
            session.commit()

    def get_recent_messages(self, session_id: str, limit: int) -> list[tuple[str, str]]:
        """Devuelve hasta `limit` mensajes previos de la sesión, en orden cronológico."""
        if limit <= 0:
            return []

        with SessionLocal() as session:
            rows = (
                session.query(Message)
                .filter(Message.session_id == session_id)
                .order_by(Message.created_at.desc())
                .limit(limit)
                .all()
            )

        rows.reverse()
        return [(row.role, row.content) for row in rows]

    def get_all_messages(self, session_id: str) -> list[Message]:
        with SessionLocal() as session:
            return (
                session.query(Message)
                .filter(Message.session_id == session_id)
                .order_by(Message.created_at.asc())
                .all()
            )
