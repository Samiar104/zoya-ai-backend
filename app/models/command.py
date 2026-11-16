"""Command model — queued instructions for a device.

Lifecycle: queued -> sent -> delivered -> completed | failed
Commands are delivered over the device WebSocket when the device is
connected; otherwise they wait in the queue (status=queued).
"""
import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class CommandType(str, enum.Enum):
    TAP = "tap"
    SWIPE = "swipe"
    SCROLL = "scroll"
    OPEN_APP = "open_app"
    CLOSE_APP = "close_app"
    BACK = "back"
    HOME = "home"
    PLAY_PAUSE = "play_pause"
    NEXT = "next"
    PREVIOUS = "previous"
    VOLUME = "volume"
    SEARCH = "search"
    CALL = "call"
    MESSAGE = "message"
    CAMERA = "camera"
    CUSTOM = "custom"


class CommandStatus(str, enum.Enum):
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Command(Base):
    __tablename__ = "commands"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, index=True)
    command_type = Column(Enum(CommandType), nullable=False)
    payload = Column(Text, nullable=True)  # JSON string, e.g. {"x": 100, "y": 200}
    text = Column(String(512), nullable=True)  # human-readable description
    status = Column(Enum(CommandStatus), default=CommandStatus.QUEUED, nullable=False)
    result = Column(Text, nullable=True)  # device-reported result / error
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    device = relationship("Device", back_populates="commands")
    created_by = relationship("User")
