"""WebSocket tests — chat echo and device channel."""
import json
import uuid


def test_chat_websocket_reply(client, auth_headers):
    # Create a session first.
    r = client.post("/chat/sessions", json={"language": "hi", "mode": "assistant"}, headers=auth_headers)
    assert r.status_code == 201, r.text
    session_id = r.json()["id"]
    with client.websocket_connect("/ws/chat") as ws:
        ws.send_text(json.dumps({"session_id": session_id, "content": "hello"}))
        data = json.loads(ws.receive_text())
        assert data["type"] == "reply"
        assert data["reply"]
        assert "emotion" in data


def test_device_websocket_requires_api_key(client):
    import pytest
    from starlette.websockets import WebSocketDisconnect

    # No api_key -> server closes with 1008 during connect.
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/ws/device/dev_x"):
            pass
    assert exc.value.code == 1008


def test_device_websocket_connect_and_heartbeat(client, api_key_headers):
    did = f"dev_{uuid.uuid4().hex[:8]}"
    r = client.post("/devices/register", json={"device_id": did, "name": "Pixel"}, headers=api_key_headers)
    assert r.status_code == 201
    with client.websocket_connect(f"/ws/device/{did}?api_key=test-api-key-123") as ws:
        ws.send_text(json.dumps({"type": "heartbeat"}))
        # No reply expected for heartbeat; connection staying open proves it.
        ws.send_text(json.dumps({"type": "result", "command_id": 999999, "status": "completed"}))
