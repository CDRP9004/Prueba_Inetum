"""Traza de nivel request para el endpoint de chat.

`traced_chat_request` abre una traza de Langfuse por request (agrupada por `session_id`,
usando `propagate_attributes` para que todas las observaciones hijas -retrieval, rerank,
generación- queden asociadas a la misma sesión) y expone la observación raíz para setear
el output final. Si Langfuse no está configurado, es un no-op transparente (`yield None`).
"""
from __future__ import annotations

import logging
from contextlib import contextmanager

from langfuse import propagate_attributes

from observability.langfuse_client import get_langfuse_client

logger = logging.getLogger(__name__)


@contextmanager
def traced_chat_request(session_id: str, message: str):
    """Nota: solo envuelve el *armado* de la traza en manejo de errores. Las excepciones
    que ocurran dentro del bloque `with` del llamador (ej. un error real del pipeline RAG)
    deben propagarse normalmente y no ser tratadas como una falla de observabilidad."""
    client = get_langfuse_client()
    if client is None:
        yield None
        return

    with propagate_attributes(session_id=session_id, trace_name="chat"):
        with client.start_as_current_observation(name="chat-request", input={"message": message}) as root:
            yield root
