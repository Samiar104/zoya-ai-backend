"""Health endpoint tests."""
import uuid


def test_root_ok(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["app"] == "ZOYA AI Backend"


def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["database"] == "ok"
    assert data["version"] == "1.0.0"


def test_readiness(client):
    r = client.get("/health/ready")
    assert r.status_code == 200
    assert r.json()["ready"] is True
