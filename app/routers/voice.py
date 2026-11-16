"""Voice router — speech-to-text and text-to-speech.

Phase 1 ships a STUB engine: endpoints return HTTP 501 with setup help
until a real engine is installed (see README "Voice" and
app/services/voice_engine.py). The routes, request shapes and auth are
final — only the engine implementation changes later.
"""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response

from app.core.security import get_current_user
from app.models.user import User
from app.schemas.voice import STTResponse, TTSRequest, VoiceStatus
from app.services.voice_engine import get_voice_engine, voice_status

router = APIRouter(prefix="/voice", tags=["voice"])


@router.get("/status", response_model=VoiceStatus)
def status(_user: User = Depends(get_current_user)) -> VoiceStatus:
    return VoiceStatus(**voice_status())


@router.post("/stt", response_model=STTResponse)
async def speech_to_text(
    file: UploadFile = File(...),
    language: str = "hi",
    _user: User = Depends(get_current_user),
) -> STTResponse:
    audio = await file.read()
    if not audio:
        raise HTTPException(status_code=400, detail="Empty audio file")
    engine = get_voice_engine()
    try:
        text = engine.transcribe(audio, language)
    except RuntimeError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    return STTResponse(text=text, language=language, engine=engine.name)


@router.post("/tts")
async def text_to_speech(
    data: TTSRequest,
    _user: User = Depends(get_current_user),
) -> Response:
    engine = get_voice_engine()
    try:
        audio = engine.synthesize(data.text, data.language)
    except RuntimeError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    return Response(content=audio, media_type="audio/wav")
