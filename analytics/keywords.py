"""Extracción simple de palabras clave de los mensajes de usuario (sin dependencias de NLP)."""
from __future__ import annotations

import re
from collections import Counter

_TOKEN_RE = re.compile(r"[a-záéíóúñü]+", re.IGNORECASE)

# Stopwords en español + signos de interrogación frecuentes en preguntas, para que el
# conteo de palabras frecuentes refleje temas reales y no conectores gramaticales.
_STOPWORDS_ES = {
    "de", "la", "que", "el", "en", "y", "a", "los", "del", "se", "las", "por", "un",
    "para", "con", "no", "una", "su", "al", "lo", "como", "más", "pero", "sus", "le",
    "ya", "o", "este", "sí", "porque", "esta", "entre", "cuando", "muy", "sin", "sobre",
    "también", "me", "hasta", "hay", "donde", "quien", "desde", "todo", "nos", "durante",
    "todos", "uno", "les", "ni", "contra", "otros", "ese", "eso", "ante", "ellos", "e",
    "esto", "mí", "antes", "algunos", "qué", "unos", "yo", "otro", "otras", "otra", "él",
    "tanto", "esa", "estos", "mucho", "quienes", "nada", "muchos", "cual", "poco", "ella",
    "estar", "estas", "algunas", "algo", "nosotros", "mi", "mis", "tú", "te", "ti", "tu",
    "tus", "ellas", "nosotras", "vosotros", "vosotras", "os", "mío", "mía", "míos", "mías",
    "tuyo", "tuya", "tuyos", "tuyas", "suyo", "suya", "suyos", "suyas", "nuestro",
    "nuestra", "nuestros", "nuestras", "vuestro", "vuestra", "vuestros", "vuestras",
    "es", "son", "soy", "eres", "somos", "sois", "puede", "puedo", "puedes", "podemos",
    "quiero", "quiere", "quieres", "tengo", "tiene", "tienes", "hacer", "cómo", "qué",
    "cuál", "cuáles", "cuánto", "cuánta", "cuántos", "cuántas", "dónde", "bbva",
}


def top_keywords(texts: list[str], top_n: int = 15) -> list[tuple[str, int]]:
    counter: Counter[str] = Counter()
    for text in texts:
        words = (w.lower() for w in _TOKEN_RE.findall(text))
        counter.update(w for w in words if len(w) > 2 and w not in _STOPWORDS_ES)
    return counter.most_common(top_n)
