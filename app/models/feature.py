"""Feature/plugin model — modular feature registry.

Features are metadata only: name, version, description, compatibility.
No arbitrary code is executed from the registry — a feature's code lives
in the Android app / backend services and is enabled through this table.
Phase 8 (AI Feature Builder) will generate new entries here.
"""
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class Feature(Base):
    __tablename__ = "features"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), unique=True, index=True, nullable=False)  # slug, e.g. "teaching_mode"
    display_name = Column(String(128), nullable=False)
    version = Column(String(32), default="1.0.0", nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(64), nullable=True)
    min_android_version = Column(String(16), nullable=True)
    enabled = Column(Boolean, default=True, nullable=False)
    installed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
