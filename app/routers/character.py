"""Character router — ZOYA's face and character profile.

GET /character returns the profile the website and Android app display:
name, description, backstory, traits, voice character, avatar URL,
languages and modes. Configured in .env (ZOYA_* settings) — see README.
"""
from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.emotion import CharacterProfile

router = APIRouter(tags=["character"])


@router.get("/character", response_model=CharacterProfile)
def get_character() -> CharacterProfile:
    return CharacterProfile(**get_settings().character_profile())
