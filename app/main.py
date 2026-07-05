"""Aplicación FastAPI: uso -> uvicorn app.main:app --reload"""
from fastapi import FastAPI

from app.routers import chat

app = FastAPI(title="Asistente RAG BBVA", version="0.1.0")
app.include_router(chat.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
