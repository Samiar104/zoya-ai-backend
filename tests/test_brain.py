"""Brain tests — emotion, memory, companion mode, character profile."""


def test_analyze_emotion_sad(client, auth_headers):
    r = client.post("/conversation/analyze-emotion", json={"text": "I am very sad today, I feel like crying"}, headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["emotion"] == "sad"
    assert 0 < data["confidence"] <= 1


def test_analyze_emotion_happy_hindi(client, auth_headers):
    r = client.post("/conversation/analyze-emotion", json={"text": "main bohat khush hoon, aaj maza aa gaya"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["emotion"] == "happy"


def test_analyze_emotion_neutral(client, auth_headers):
    r = client.post("/conversation/analyze-emotion", json={"text": "the weather is cloudy"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["emotion"] == "neutral"


def test_character_profile(client):
    r = client.get("/character")
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "ZOYA"
    assert data["avatar_url"] == "zoya-character.png"
    assert "assistant" in data["modes"] and "companion" in data["modes"]
    assert "hi" in data["languages"]
    assert data["personality_traits"]


def test_memory_add_and_list(client, auth_headers):
    r = client.post("/conversation/memory", json={"kind": "preference", "key": "likes_chai", "value": "masala chai"}, headers=auth_headers)
    assert r.status_code == 201, r.text
    r = client.get("/conversation/memory", headers=auth_headers)
    assert r.status_code == 200
    assert any(m["key"] == "likes_chai" for m in r.json())


def test_chat_reply_includes_emotion_and_uses_memory(client, auth_headers):
    # Teach ZOYA the user's name first.
    client.post("/conversation/memory", json={"kind": "fact", "key": "name", "value": "Ayaan"}, headers=auth_headers)
    r = client.post("/chat/sessions", json={"language": "en", "mode": "companion"}, headers=auth_headers)
    session_id = r.json()["id"]
    r = client.post("/chat/message", json={"session_id": session_id, "content": "what is my name?"}, headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "Ayaan" in data["reply"]  # brain remembered the name
    assert data["mode"] == "companion"
    assert data["emotion"] in ("happy", "sad", "stressed", "angry", "tired", "lonely", "excited", "neutral")


def test_chat_sad_message_gets_comforting_reply(client, auth_headers):
    r = client.post("/chat/sessions", json={"language": "en", "mode": "companion"}, headers=auth_headers)
    session_id = r.json()["id"]
    r = client.post("/chat/message", json={"session_id": session_id, "content": "I am really sad today"}, headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["emotion"] == "sad"
    assert data["intent"] == "share_feeling"


def test_invalid_mode_rejected(client, auth_headers):
    r = client.post("/chat/sessions", json={"language": "hi", "mode": "girlfriend"}, headers=auth_headers)
    assert r.status_code == 400


def test_voice_status_stub(client, auth_headers):
    r = client.get("/voice/status", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["engine"] == "stub"
    assert data["stt_available"] is False
    assert "hi" in data["languages"]


def test_voice_stt_stub_returns_501(client, auth_headers):
    r = client.post("/voice/stt", files={"file": ("test.wav", b"RIFF....", "audio/wav")}, headers=auth_headers)
    assert r.status_code == 501
