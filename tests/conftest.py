"""Test setup — isolated SQLite DB and fixed test API key.

Env vars are set BEFORE the app is imported, so the engine binds to a
throwaway database file that is removed after the session.
"""
import os
import tempfile
from pathlib import Path

TMP_DIR = Path(tempfile.mkdtemp(prefix="zoya-test-"))
DB_PATH = TMP_DIR / "test.db"

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "test-secret-key-for-pytest-only"
os.environ["ZOYA_API_KEY"] = "test-api-key-123"
os.environ["ALLOWED_ORIGINS"] = "http://localhost:3000"
os.environ["RATE_LIMIT_PER_MINUTE"] = "1000"
os.environ["ENVIRONMENT"] = "test"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import init_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _init_test_db():
    init_db()
    yield
    import shutil

    shutil.rmtree(TMP_DIR, ignore_errors=True)


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth_headers(client):
    """Register a fresh user and return Authorization headers."""
    import uuid

    username = f"user_{uuid.uuid4().hex[:8]}"
    r = client.post("/auth/register", json={"username": username, "password": "secret123"})
    assert r.status_code == 201, r.text
    r = client.post("/auth/login", json={"username": username, "password": "secret123"})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def api_key_headers():
    return {"X-API-Key": "test-api-key-123"}
