"""Aplicación FastAPI: uso -> uvicorn app.main:app --reload"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.routers import analytics, chat, history

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Asistente RAG BBVA", version="0.1.0")
app.include_router(chat.router)
app.include_router(history.router)
app.include_router(analytics.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/analytics")
def analytics_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "analytics.html")
