"""ZOYA AI Backend — core configuration.

All settings come from environment variables / a .env file.
Secrets are never hard-coded; see .env.example.
"""
import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]  # backend/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ZOYA AI Backend"
    app_version: str = "1.0.0"
    environment: str = "development"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    database_url: str = "sqlite:///./zoya.db"
    secret_key: str = "change-me-to-a-long-random-secret"
    zoya_api_key: str = ""

    allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    rate_limit_per_minute: int = 120

    voice_engine: str = "stub"
    voice_default_language: str = "hi"
    zoya_languages: str = "hi,ur,pa,en"
    zoya_personality: str = "friendly,witty,supportive"

    backup_dir: str = "./backups"
    backup_retention_days: int = 30

    # --- ZOYA character profile ---
    # Shown by GET /character; the website/app display this face & story.
    # avatar_url points at the character image (default file in the goal
    # workspace: zoya-character.png, generated separately).
    zoya_name: str = "ZOYA"
    zoya_tagline: str = "Your AI friend, assistant and companion."
    zoya_description: str = (
        "ZOYA is a warm, witty and supportive AI personal assistant. "
        "She speaks Hindi, Urdu, Punjabi and English, remembers what matters "
        "to you, notices how you feel, and helps you get things done on your "
        "phone — gently, and always with your permission."
    )
    zoya_backstory: str = (
        "ZOYA was built as a personal companion who grows with her user. "
        "She started as a voice in a phone and became a friend who remembers "
        "your favourite songs, your late-night worries and your small wins — "
        "and celebrates them with you."
    )
    zoya_traits: str = "friendly,witty,supportive,curious,patient,playful"
    zoya_voice_character: str = "Natural human-like female voice, warm and expressive, medium pitch, calm pace"
    zoya_avatar_url: str = "zoya-character.png"
    zoya_modes: str = "assistant,companion"

    @property
    def traits(self) -> list[str]:
        return [t.strip() for t in self.zoya_traits.split(",") if t.strip()]

    @property
    def modes(self) -> list[str]:
        return [m.strip() for m in self.zoya_modes.split(",") if m.strip()]

    def character_profile(self) -> dict:
        return {
            "name": self.zoya_name,
            "tagline": self.zoya_tagline,
            "description": self.zoya_description,
            "backstory": self.zoya_backstory,
            "personality_traits": self.traits,
            "voice_character": self.zoya_voice_character,
            "avatar_url": self.zoya_avatar_url,
            "languages": self.languages,
            "modes": self.modes,
        }

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def languages(self) -> list[str]:
        return [x.strip() for x in self.zoya_languages.split(",") if x.strip()]

    @property
    def db_path(self) -> Path | None:
        """Local file path when DATABASE_URL points at SQLite, else None."""
        url = self.database_url
        if url.startswith("sqlite:///"):
            raw = url[len("sqlite:///"):]
            p = Path(raw)
            return p if p.is_absolute() else (BASE_DIR / p)
        return None


@lru_cache
def get_settings() -> Settings:
    return Settings()


def ensure_api_key() -> str:
    """Return the static API key, generating + persisting one on first run.

    The key NEVER expires by design (project requirement). It is generated
    once, stored in backend/.env (never in source code), and can be rotated
    by replacing ZOYA_API_KEY in .env and restarting.
    """
    from app.core.logging import get_logger

    log = get_logger("zoya.security")
    settings = get_settings()
    if settings.zoya_api_key:
        return settings.zoya_api_key

    import secrets

    key = "zoya_" + secrets.token_urlsafe(32)
    env_file = BASE_DIR / ".env"
    try:
        if env_file.exists():
            text = env_file.read_text(encoding="utf-8")
            if "ZOYA_API_KEY=" in text:
                lines = []
                for line in text.splitlines():
                    lines.append(f"ZOYA_API_KEY={key}" if line.startswith("ZOYA_API_KEY=") else line)
                env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
            else:
                with env_file.open("a", encoding="utf-8") as fh:
                    fh.write(f"\nZOYA_API_KEY={key}\n")
        else:
            env_file.write_text(f"ZOYA_API_KEY={key}\n", encoding="utf-8")
        # Refresh the cached settings object so this process uses the new key.
        get_settings.cache_clear()
        log.warning("Generated a new static ZOYA_API_KEY and saved it to .env. Keep it secret.")
    except OSError as exc:  # pragma: no cover - filesystem failure
        log.error("Could not persist generated API key to .env: %s", exc)
    return key
