"""Health endpoint tests."""
import uuid


def test_root_ok(client):
    # "/" serves the ZOYA Control Center website (StaticFiles), not JSON.
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "ZOYA AI Control Center" in r.text


def test_remix_site_ok(client):
    # "/remix/" serves the remix ZOYA site (StaticFiles, Vite base '/remix/').
    r = client.get("/remix/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "<title>ZOYA AI</title>" in r.text
    assert "/remix/assets/" in r.text


def test_remix_avatar_ok(client):
    r = client.get("/remix/zoya-character.png")
    assert r.status_code == 200
    assert "image/png" in r.headers["content-type"]


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
