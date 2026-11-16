"""Device model — Android devices registered with ZOYA."""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(128), unique=True, index=True, nullable=False)  # Android-side id
    name = Column(String(128), nullable=False)
    model = Column(String(128), nullable=True)
    android_version = Column(String(32), nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_online = Column(Boolean, default=False, nullable=False)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    owner = relationship("User")
    commands = relationship("Command", back_populates="device", cascade="all, delete-orphan")
