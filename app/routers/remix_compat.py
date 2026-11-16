"""Compatibility endpoints for the remix ZOYA Android app.

The remix app (Google AI Studio build, package com.aistudio.companion.aegfnt)
talks to a backend with this contract (see ZoyaBackendGeminiClient.kt and
ZoyaFastApiServerManager.kt in the remix app source):
- POST /api/chat {"prompt", "provider", "language_mode", "system_prompt"?}
  with headers X-Zoya-Device-ID and Authorization: Bearer <device-id>, or
  (ZoyaFastApiServerManager) X-Zoya-Api-Key and Authorization: Bearer <key>.
  The response JSON must contain "reply".
- GET /health -> 2xx (already exists; /api/health is an alias here).

There is NO Gemini/OpenAI here: the reply comes from ZoyaBrain (the
rule-based brain, companion/girlfriend mode). No LLM keys are used or
needed, and the "provider" / "model" fields the app sends are ignored.
Auth is the device handshake only — no JWT and no user login, because
the remix app has no user accounts.
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.routers.health import health as health_check
from app.services.conversation import ZoyaBrain

router = APIRouter(tags=["remix-compat"])
log = get_logger("zoya.remix_compat")


class RemixChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    provider: str | None = None
    language_mode: str | None = None
    system_prompt: str | None = None
    model: str | None = None

    class Config:
        extra = "ignore"


def _language_for(language_mode: str | None) -> str:
    """Map the app's language_mode to a ZoyaBrain language.

    The app is the Urdu girlfriend persona, so "girlfriend_urdu" (and
    anything unrecognised) maps to Urdu companion mode.
    """
    mode = (language_mode or "").lower()
    if "punjabi" in mode:
        return "pa"
    if "hindi" in mode:
        return "hi"
    if "english" in mode:
        return "en"
    return "ur"


@router.post("/api/chat")
def remix_chat(data: RemixChatRequest, request: Request) -> dict:
    if not data.prompt.strip():
        raise HTTPException(status_code=422, detail="prompt must not be blank")
    device_id = request.headers.get("X-Zoya-Device-ID", "").strip()
    fast_key = request.headers.get("X-Zoya-Api-Key", "").strip()
    auth_hdr = request.headers.get("Authorization", "").strip()
    static_key = request.headers.get("X-API-Key", "").strip()
    if not (device_id or fast_key or auth_hdr or static_key):
        raise HTTPException(
            status_code=401,
            detail="Missing device handshake (X-Zoya-Device-ID)",
        )
    language = _language_for(data.language_mode)
    brain = ZoyaBrain(language=language, mode="companion")
    reply_text, understanding = brain.reply(data.prompt, user_context={}, history=[])
    log.info(
        "Remix /api/chat device=%s lang=%s intent=%s",
        device_id or fast_key or "api-key",
        language,
        understanding.intent,
    )
    return {
        "reply": reply_text,
        "provider": "zoya",
        "model": "zoya-brain",
        "intent": understanding.intent,
        "emotion": understanding.emotion,
        "emotion_confidence": understanding.confidence,
    }


@router.get("/api/health")
def remix_health():
    """Alias of GET /health for the remix app."""
    return health_check()
