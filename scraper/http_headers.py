"""Cabeceras HTTP usadas por el scraper.

Algunos WAFs (ej. Akamai en bbva.com.co) rechazan con 403 las requests que solo llevan
``User-Agent`` porque no calzan con el patrón de un navegador real. Enviamos el resto de
cabeceras estándar que cualquier navegador manda en una navegación normal (Accept,
Accept-Language, Sec-Fetch-*) para evitar ese falso positivo. El ``User-Agent`` se
mantiene descriptivo y con datos de contacto: no se busca ocultar que es un scraper,
solo dejar de parecer una request "no-browser" incompleta. El sitio permite explícitamente
el crawling vía robots.txt (``Allow: /``).
"""
from __future__ import annotations


def build_headers(user_agent: str) -> dict[str, str]:
    return {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Upgrade-Insecure-Requests": "1",
    }
