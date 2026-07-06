"""Modelos Pydantic de request/response de la API."""
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=4000)


class SourceItem(BaseModel):
    title: str
    url: str
    score: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceItem]
