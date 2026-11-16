"""ZOYA AI Backend — FastAPI application entrypoint (Phase 1).

Run with:
    uvicorn app.main:app --host 0.0.0.0 --port 8000
or:
    ./run.sh
"""
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import ensure_api_key, get_settings
from app.core.database import init_db
from app.core.logging import get_logger, setup_logging
from app.core.ratelimit import RateLimitMiddleware
from app.routers import auth, backup, character, chat, commands, conversation, devices, features, health, remix_compat, voice
from app.services import plugins

settings = get_settings()
setup_logging(settings.log_level)
log = get_logger("zoya.main")

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "ZOYA AI Backend (Phase 1) — AI Brain for the ZOYA Android assistant. "
        "Auth, devices, commands, conversation with memory, emotion and "
        "companion modes, character profile, features, voice (stub), "
        "backups and WebSockets. See /docs for the interactive API."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    key = ensure_api_key()
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        plugins.seed_builtin_features(db)
    finally:
        db.close()
    log.info("%s v%s starting in %s mode", settings.app_name, settings.app_version, settings.environment)
    log.info("API docs at /docs — static API key present: %s", bool(key))


@app.get("/", tags=["root"])
def root() -> dict:
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
        "health": "/health",
    }


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(devices.router)
app.include_router(commands.router)
app.include_router(features.router)
app.include_router(voice.router)
app.include_router(backup.router)
app.include_router(chat.router)
app.include_router(conversation.router)
app.include_router(character.router)
app.include_router(remix_compat.router)
