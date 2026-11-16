"""Voice engine — pluggable STT/TTS.

Phase 1 ships an HONEST STUB: no speech engine is installed, so the
endpoints return HTTP 501 with instructions. This is deliberate — the
backend must not pretend to transcribe audio it cannot hear.

Upgrade path (README "Voice"):
- STT: install faster-whisper, set VOICE_ENGINE=whisper and implement
  WhisperEngine.transcribe() (10 lines — model + transcribe call).
- TTS: install Piper, set VOICE_ENGINE=piper and implement
  PiperEngine.synthesize() (write text to a wav file, return bytes).
Both engines share this interface, so routers need no changes.
"""
from abc import ABC, abstractmethod

from app.core.config import get_settings


class VoiceEngine(ABC):
    name: str = "stub"

    @abstractmethod
    def transcribe(self, audio_bytes: bytes, language: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def synthesize(self, text: str, language: str) -> bytes:
        raise NotImplementedError


class StubVoiceEngine(VoiceEngine):
    """Placeholder engine — always reports itself as unavailable."""

    name = "stub"

    def transcribe(self, audio_bytes: bytes, language: str) -> str:
        raise RuntimeError(
            "STT is not configured: VOICE_ENGINE=stub. "
            "Install faster-whisper and set VOICE_ENGINE=whisper (see README)."
        )

    def synthesize(self, text: str, language: str) -> bytes:
        raise RuntimeError(
            "TTS is not configured: VOICE_ENGINE=stub. "
            "Install Piper and set VOICE_ENGINE=piper (see README)."
        )


def get_voice_engine() -> VoiceEngine:
    engine = get_settings().voice_engine.lower()
    if engine == "stub":
        return StubVoiceEngine()
    # Future engines register here. Unknown values fall back to the stub
    # rather than crashing the server.
    return StubVoiceEngine()


def voice_status() -> dict:
    settings = get_settings()
    engine = get_voice_engine()
    available = engine.name != "stub"
    return {
        "engine": engine.name,
        "stt_available": available,
        "tts_available": available,
        "languages": settings.languages,
        "note": (
            "Voice engine is configured and ready."
            if available
            else "STUB engine: install faster-whisper (STT) / Piper (TTS) and set VOICE_ENGINE — see README."
        ),
    }
