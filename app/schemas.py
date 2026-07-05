"""Modelos Pydantic de request/response de la API."""
from pydantic import BaseModel


class ChatRequest(BaseModel):
    session_id: str
    message: str


class SourceItem(BaseModel):
    title: str
    url: str
    score: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceItem]
