"""Conversation schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SessionCreate(BaseModel):
    language: str = "hi"
    mode: str = "assistant"
    device_id: int | None = None
    title: str | None = None


class ChatMessage(BaseModel):
    session_id: int
    content: str = Field(..., min_length=1, max_length=4000)
    language: str | None = None


class ChatReply(BaseModel):
    session_id: int
    reply: str
    language: str
    mode: str
    intent: str | None = None
    emotion: str = "neutral"
    emotion_confidence: float = 0.5


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    emotion: str | None = None
    emotion_confidence: float | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SessionOut(BaseModel):
    id: int
    language: str
    mode: str
    title: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
