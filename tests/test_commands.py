"""Command tests — queue, status, results, cancel."""
import uuid


def _mk_device(client, api_key_headers):
    did = f"dev_{uuid.uuid4().hex[:8]}"
    r = client.post("/devices/register", json={"device_id": did, "name": "Pixel"}, headers=api_key_headers)
    assert r.status_code == 201
    return r.json()["id"], did


def test_queue_command_offline_device_stays_queued(client, auth_headers, api_key_headers):
    device_id, _ = _mk_device(client, api_key_headers)
    r = client.post("/commands", json={"device_id": device_id, "command_type": "open_app", "payload": {"app": "youtube"}, "text": "Open YouTube"}, headers=auth_headers)
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["command_type"] == "open_app"
    assert data["status"] == "queued"  # device not on WebSocket


def test_command_unknown_device(client, auth_headers):
    r = client.post("/commands", json={"device_id": 999999, "command_type": "back"}, headers=auth_headers)
    assert r.status_code == 404


def test_command_invalid_type(client, auth_headers, api_key_headers):
    device_id, _ = _mk_device(client, api_key_headers)
    r = client.post("/commands", json={"device_id": device_id, "command_type": "teleport"}, headers=auth_headers)
    assert r.status_code == 422


def test_command_result_and_cancel(client, auth_headers, api_key_headers):
    device_id, _ = _mk_device(client, api_key_headers)
    r = client.post("/commands", json={"device_id": device_id, "command_type": "volume", "payload": {"level": 5}}, headers=auth_headers)
    cmd_id = r.json()["id"]
    r = client.post(f"/commands/{cmd_id}/result", json={"status": "completed", "result": "ok"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "completed"

    r = client.post("/commands", json={"device_id": device_id, "command_type": "home"}, headers=auth_headers)
    cmd2 = r.json()["id"]
    r = client.post(f"/commands/{cmd2}/cancel", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"


def test_list_commands_filtered(client, auth_headers, api_key_headers):
    device_id, _ = _mk_device(client, api_key_headers)
    client.post("/commands", json={"device_id": device_id, "command_type": "back"}, headers=auth_headers)
    r = client.get(f"/commands?device_id={device_id}", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) >= 1
