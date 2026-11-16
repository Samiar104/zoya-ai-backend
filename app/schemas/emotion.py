"""Emotion / memory / character schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EmotionRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    language: str | None = None
    voice_metadata: dict | None = None  # e.g. {"energy": 0.8, "pitch": 0.7, "speech_rate": 0.6}


class EmotionResponse(BaseModel):
    emotion: str
    confidence: float
    label: str


class MemoryEntryOut(BaseModel):
    id: int
    kind: str
    key: str
    value: str
    confidence: float
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MemoryCreate(BaseModel):
    kind: str = Field(..., description="preference | fact | topic")
    key: str
    value: str


class CharacterProfile(BaseModel):
    name: str
    tagline: str
    description: str
    backstory: str
    personality_traits: list[str]
    voice_character: str
    avatar_url: str
    languages: list[str]
    modes: list[str]
