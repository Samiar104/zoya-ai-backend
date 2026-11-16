"""Voice schemas."""
from pydantic import BaseModel


class STTResponse(BaseModel):
    text: str
    language: str
    engine: str


class TTSRequest(BaseModel):
    text: str
    language: str = "hi"
    voice: str = "zoya-female"


class VoiceStatus(BaseModel):
    engine: str
    stt_available: bool
    tts_available: bool
    languages: list[str]
    note: str
