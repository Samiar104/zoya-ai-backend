"""User memory model — ZOYA's long-term memory of each user.

One row per remembered item. Kinds:
- preference: something the user likes/dislikes ("likes_chai", "favourite_singer")
- fact: a personal detail ("name", "city", "birthday")
- topic: a subject the user talked about ("cricket", "exams")
- mood: an emotion snapshot ("sad" with a timestamp) — mood history

The conversation service writes these; the reply engine reads them so
ZOYA remembers the user across sessions (her "brain").
"""
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class UserMemory(Base):
    __tablename__ = "user_memory"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    kind = Column(String(32), nullable=False, index=True)  # preference | fact | topic | mood
    key = Column(String(128), nullable=False)
    value = Column(Text, nullable=False)
    confidence = Column(Float, default=1.0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
