"""Extrae título y texto principal de una página HTML de bbva.com.co, descartando
navegación, scripts y el aviso de cookies.

El sitio usa Adobe AEM/Helix; no siempre delimita el contenido principal con <main>, así
que además de quitar las etiquetas estructurales típicas (header/footer/nav/script/etc.)
filtramos por un denylist de frases de boilerplate observadas en el propio sitio durante
el desarrollo (banner de cookies, textos de accesibilidad del menú). Es un heurístico:
puede requerir ajuste una vez se disponga del corpus completo real.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup

_STRUCTURAL_TAGS = ["script", "style", "noscript", "svg", "iframe", "header", "footer", "nav", "form", "button"]

_BOILERPLATE_SUBSTRINGS = [
    "utilizamos cookies",
    "aviso de privacidad",
    "ir al contenido principal",
    "pulsa enter",
    "hacer búsqueda",
    "menú cerrar",
    "acceso acceso acceso",
]

_WHITESPACE_RE = re.compile(r"[ \t]+")


@dataclass(frozen=True)
class CleanedPage:
    title: str
    text: str


def _is_boilerplate(line: str) -> bool:
    lowered = line.lower()
    return any(phrase in lowered for phrase in _BOILERPLATE_SUBSTRINGS)


def clean_html(html: bytes | str) -> CleanedPage:
    soup = BeautifulSoup(html, "html.parser")

    title = soup.title.get_text(strip=True) if soup.title else ""

    for tag in soup(_STRUCTURAL_TAGS):
        tag.decompose()

    container = soup.find("main") or soup.find("body") or soup
    raw_text = container.get_text(separator="\n", strip=True)

    lines = [_WHITESPACE_RE.sub(" ", line).strip() for line in raw_text.splitlines()]
    lines = [line for line in lines if line and not _is_boilerplate(line)]

    return CleanedPage(title=title, text="\n".join(lines))
