"""Tests for the remix-app compatibility endpoints (POST /api/chat, GET /api/health).

The remix app talks to POST /api/chat with a device handshake (no JWT, no
user login) and expects {"reply": ...} back. See app/routers/remix_compat.py.
"""

DEVICE_HEADERS = {
    "X-Zoya-Device-ID": "zoya-device-test-1",
    "Authorization": "Bearer zoya-device-test-1",
}

FAST_KEY_HEADERS = {
    "X-Zoya-Api-Key": "zoya-fast-24x7-abc123",
    "Authorization": "Bearer zoya-fast-24x7-abc123",
}


def test_api_chat_device_handshake(client):
    r = client.post(
        "/api/chat",
        json={"prompt": "hello", "provider": "google_gemini", "language_mode": "girlfriend_urdu"},
        headers=DEVICE_HEADERS,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["reply"], "reply must be non-empty"
    assert body["provider"] == "zoya"
    assert body["model"] == "zoya-brain"


def test_api_chat_greeting_reply_is_companion_urdu(client):
    r = client.post(
        "/api/chat",
        json={"prompt": "hello", "language_mode": "girlfriend_urdu"},
        headers=DEVICE_HEADERS,
    )
    assert r.status_code == 200, r.text
    assert r.json()["intent"] == "greeting"


def test_api_chat_fastapi_key_header(client):
    # ZoyaFastApiServerManager sends X-Zoya-Api-Key + Bearer <local key>.
    r = client.post(
        "/api/chat",
        json={"prompt": "hello", "language_mode": "girlfriend_urdu"},
        headers=FAST_KEY_HEADERS,
    )
    assert r.status_code == 200, r.text
    assert r.json()["reply"]


def test_api_chat_static_api_key(client, api_key_headers):
    r = client.post("/api/chat", json={"prompt": "hello"}, headers=api_key_headers)
    assert r.status_code == 200, r.text
    assert r.json()["reply"]


def test_api_chat_missing_prompt_rejected(client):
    r = client.post("/api/chat", json={"provider": "google_gemini"}, headers=DEVICE_HEADERS)
    assert r.status_code == 422


def test_api_chat_blank_prompt_rejected(client):
    r = client.post("/api/chat", json={"prompt": "   "}, headers=DEVICE_HEADERS)
    assert r.status_code == 422


def test_api_chat_no_handshake_rejected(client):
    r = client.post("/api/chat", json={"prompt": "hello"})
    assert r.status_code == 401


def test_api_health_alias(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
