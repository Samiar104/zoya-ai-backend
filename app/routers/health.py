"""Health endpoints — liveness and readiness probes."""
import time

from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.schemas.common import HealthResponse

router = APIRouter(tags=["health"])
log = get_logger("zoya.health")
STARTED_AT = time.time()


def _db_status() -> str:
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return "ok"
    except Exception as exc:  # noqa: BLE001
        log.error("DB health check failed: %s", exc)
        return "error"


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        uptime_seconds=round(time.time() - STARTED_AT, 1),
        database=_db_status(),
    )


@router.get("/health/ready")
def ready() -> dict:
    db = _db_status()
    return {"ready": db == "ok", "database": db}
