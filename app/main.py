"""Aplicación FastAPI: uso -> uvicorn app.main:app --reload"""
import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse

from app.routers import analytics, chat, history

logger = logging.getLogger(__name__)
STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Asistente RAG BBVA", version="0.1.0")
app.include_router(chat.router)
app.include_router(history.router)
app.include_router(analytics.router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Red de seguridad: cualquier excepción no capturada explícitamente en un endpoint
    (bug, dependencia caída, lo que sea) devuelve un 500 con mensaje genérico en vez de
    filtrar un traceback interno al cliente. Los endpoints ya manejan sus errores
    esperables (Ollama caído, DB caída, etc.) con mensajes específicos; esto es el
    respaldo para lo inesperado."""
    logger.exception("Excepción no manejada en %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Ocurrió un error interno inesperado."})


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/analytics")
def analytics_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "analytics.html")
