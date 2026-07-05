"""Cliente de Langfuse con degradación elegante.

Si no hay API keys configuradas (`LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY`) o son
inválidas, el resto de la aplicación sigue funcionando exactamente igual, solo que sin
enviar trazas — la observabilidad es un complemento, nunca debe poder tumbar el chat.
"""
from __future__ import annotations

import logging
from functools import lru_cache

from langfuse import Langfuse

from observability.config import config

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_langfuse_client() -> Langfuse | None:
    if not config.keys_configured:
        logger.info(
            "Langfuse no configurado (faltan LANGFUSE_PUBLIC_KEY/LANGFUSE_SECRET_KEY): "
            "la app funciona igual, simplemente sin trazas de observabilidad."
        )
        return None

    try:
        client = Langfuse(public_key=config.public_key, secret_key=config.secret_key, host=config.host)
        if not client.auth_check():
            logger.warning("Credenciales de Langfuse inválidas; observabilidad deshabilitada.")
            return None
        return client
    except Exception:
        logger.exception("No se pudo inicializar Langfuse; observabilidad deshabilitada.")
        return None
