"""Auth schemas."""
from pydantic import BaseModel, ConfigDict, Field


class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)
    email: str | None = None
    display_name: str | None = None


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    # Tokens never expire by design (see README "Security & key lifecycle").
    expires_in: str = "never"


class UserOut(BaseModel):
    id: int
    username: str
    email: str | None
    display_name: str | None
    is_active: bool
    is_admin: bool

    model_config = ConfigDict(from_attributes=True)
