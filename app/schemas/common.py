"""Shared schema helpers."""
from pydantic import BaseModel


class MessageResponse(BaseModel):
    detail: str


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    environment: str
    uptime_seconds: float
    database: str
