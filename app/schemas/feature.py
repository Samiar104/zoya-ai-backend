"""Feature/plugin schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FeatureCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=128)
    version: str = "1.0.0"
    description: str | None = None
    category: str | None = None
    min_android_version: str | None = None
    enabled: bool = True


class FeatureUpdate(BaseModel):
    display_name: str | None = None
    version: str | None = None
    description: str | None = None
    category: str | None = None
    min_android_version: str | None = None
    enabled: bool | None = None


class FeatureOut(BaseModel):
    id: int
    name: str
    display_name: str
    version: str
    description: str | None
    category: str | None
    min_android_version: str | None
    enabled: bool
    installed_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
