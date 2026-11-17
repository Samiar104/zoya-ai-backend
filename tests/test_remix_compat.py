"""Tests for the remix-app compatibility endpoints (POST /api/chat, GET /api/health).

The remix app talks to POST /api/chat with a device handshake (no JWT, no
user login) and expects {"reply": ...} back. See app/routers/remix_compat.py.
"""

import re

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


def test_api_chat_roman_urdu_prompt_gets_roman_urdu_reply(client):
    # The user writes Roman Urdu; the reply must be Latin script so the
    # app's en-IN TTS voice can pronounce it naturally (Urdu script read
    # by a Latin-script voice sounds robotic).
    r = client.post(
        "/api/chat",
        json={"prompt": "salam, kya haal hai", "provider": "google_gemini", "language_mode": "girlfriend_urdu"},
        headers=DEVICE_HEADERS,
    )
    assert r.status_code == 200, r.text
    reply = r.json()["reply"]
    assert reply
    assert not re.search(r"[\u0600-\u06FF\u0900-\u097F\u0A00-\u0A7F]", reply), "reply must be Latin script"


def test_api_chat_urdu_script_prompt_gets_urdu_script_reply(client):
    r = client.post(
        "/api/chat",
        json={"prompt": "السلام علیکم", "language_mode": "girlfriend_urdu"},
        headers=DEVICE_HEADERS,
    )
    assert r.status_code == 200, r.text
    assert re.search(r"[\u0600-\u06FF]", r.json()["reply"])


def test_api_chat_english_prompt_gets_english_reply(client):
    r = client.post(
        "/api/chat",
        json={"prompt": "hello", "language_mode": "girlfriend_urdu"},
        headers=DEVICE_HEADERS,
    )
    assert r.status_code == 200, r.text
    reply = r.json()["reply"]
    assert reply
    assert not re.search(r"[\u0600-\u06FF\u0900-\u097F\u0A00-\u0A7F]", reply), "reply must be Latin script"


def test_api_chat_roman_urdu_sad_gets_comforting_roman_reply(client):
    r = client.post(
        "/api/chat",
        json={"prompt": "main bohat udas hoon", "language_mode": "girlfriend_urdu"},
        headers=DEVICE_HEADERS,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["emotion"] == "sad"
    assert body["reply"]
    assert not re.search(r"[\u0600-\u06FF]", body["reply"]), "reply must be Latin script"
