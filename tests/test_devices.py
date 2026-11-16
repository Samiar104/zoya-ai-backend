"""Device tests — register, list, heartbeat, pending commands."""
import uuid


def _device_id():
    return f"dev_{uuid.uuid4().hex[:8]}"


def test_register_device_with_api_key(client, api_key_headers):
    did = _device_id()
    r = client.post("/devices/register", json={"device_id": did, "name": "Pixel 8", "model": "Pixel 8", "android_version": "14"}, headers=api_key_headers)
    assert r.status_code == 201, r.text
    assert r.json()["device_id"] == did


def test_register_device_without_key_rejected(client):
    r = client.post("/devices/register", json={"device_id": _device_id(), "name": "X"})
    assert r.status_code == 401


def test_list_devices_requires_jwt(client, auth_headers):
    r = client.get("/devices", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_heartbeat(client, api_key_headers):
    did = _device_id()
    client.post("/devices/register", json={"device_id": did, "name": "Pixel"}, headers=api_key_headers)
    r = client.post("/devices/heartbeat", json={"device_id": did, "battery_level": 80}, headers=api_key_headers)
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_heartbeat_unknown_device(client, api_key_headers):
    r = client.post("/devices/heartbeat", json={"device_id": "no-such-device"}, headers=api_key_headers)
    assert r.status_code == 404
