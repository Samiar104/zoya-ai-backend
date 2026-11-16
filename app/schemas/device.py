"""Device schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DeviceRegister(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=128)
    name: str = Field(..., min_length=1, max_length=128)
    model: str | None = None
    android_version: str | None = None


class DeviceOut(BaseModel):
    id: int
    device_id: str
    name: str
    model: str | None
    android_version: str | None
    is_online: bool
    last_seen_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeviceHeartbeat(BaseModel):
    device_id: str
    battery_level: int | None = None
    network: str | None = None
