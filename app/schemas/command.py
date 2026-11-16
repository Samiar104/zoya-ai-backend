"""Command schemas."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.command import CommandStatus, CommandType


class CommandCreate(BaseModel):
    device_id: int
    command_type: CommandType
    payload: dict[str, Any] | None = None
    text: str | None = None


class CommandOut(BaseModel):
    id: int
    device_id: int
    command_type: CommandType
    payload: str | None
    text: str | None
    status: CommandStatus
    result: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CommandResult(BaseModel):
    status: CommandStatus = Field(..., description="completed | failed | delivered")
    result: str | None = None
