"""Backup & recovery router.

SQLite: backups are plain file copies of ``zoya.db`` (safe, atomic enough
for Phase 1 — the DB is small). PostgreSQL: pg_dump is used when the
``pg_dump`` binary is available.
Restore replaces the database file; the server must be restarted after a
restore (the endpoint says so in its response).
"""
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.core.config import get_settings
from app.core.database import get_db  # noqa: F401  (keeps session pattern uniform)
from app.core.logging import get_logger
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.common import MessageResponse
from pydantic import BaseModel

router = APIRouter(prefix="/backup", tags=["backup"])
log = get_logger("zoya.backup")


def _backup_dir() -> Path:
    settings = get_settings()
    d = Path(settings.backup_dir)
    if not d.is_absolute():
        from app.core.config import BASE_DIR

        d = BASE_DIR / d
    d.mkdir(parents=True, exist_ok=True)
    return d


class RestoreRequest(BaseModel):
    filename: str


@router.post("/create")
def create_backup(_user: User = Depends(get_current_user)) -> dict:
    settings = get_settings()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = _backup_dir() / f"zoya-backup-{stamp}.db"
    db_path = settings.db_path
    if db_path is not None:
        if not db_path.exists():
            raise HTTPException(status_code=404, detail="Database file not found (nothing to back up yet)")
        shutil.copy2(db_path, dest)
    else:
        # PostgreSQL path — try pg_dump.
        result = subprocess.run(
            ["pg_dump", settings.database_url, "-f", str(dest)], capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"pg_dump failed: {result.stderr[:300]}")
    log.info("Backup created: %s (%d bytes)", dest.name, dest.stat().st_size)
    return {"filename": dest.name, "size_bytes": dest.stat().st_size, "created": stamp}


@router.get("/list")
def list_backups(_user: User = Depends(get_current_user)) -> dict:
    files = sorted(_backup_dir().glob("zoya-backup-*"), reverse=True)
    return {
        "backups": [
            {"filename": f.name, "size_bytes": f.stat().st_size, "modified": f.stat().st_mtime} for f in files
        ]
    }


@router.get("/download/{filename}")
def download_backup(filename: str, _user: User = Depends(get_current_user)) -> FileResponse:
    path = _backup_dir() / filename
    if not path.exists() or ".." in filename or "/" in filename:
        raise HTTPException(status_code=404, detail="Backup not found")
    return FileResponse(path, filename=filename)


@router.post("/restore", response_model=MessageResponse)
def restore_backup(data: RestoreRequest, _user: User = Depends(get_current_user)) -> MessageResponse:
    settings = get_settings()
    src = _backup_dir() / data.filename
    if not src.exists() or ".." in data.filename or "/" in data.filename:
        raise HTTPException(status_code=404, detail="Backup not found")
    db_path = settings.db_path
    if db_path is None:
        raise HTTPException(status_code=501, detail="Restore for PostgreSQL must be done with psql (see README)")
    shutil.copy2(src, db_path)
    log.warning("Database restored from %s — restart required", data.filename)
    return MessageResponse(detail=f"Restored from {data.filename}. Restart the server to use the restored database.")
