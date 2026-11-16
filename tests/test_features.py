"""Feature/plugin tests — list, create, enable/disable, delete."""
import uuid


def test_builtin_features_seeded(client, auth_headers):
    r = client.get("/features", headers=auth_headers)
    assert r.status_code == 200
    names = {f["name"] for f in r.json()}
    assert "voice_assistant" in names
    assert "device_control" in names


def test_create_enable_disable_delete(client, auth_headers):
    name = f"feat_{uuid.uuid4().hex[:6]}"
    r = client.post("/features", json={"name": name, "display_name": "Test Feature", "version": "0.1.0"}, headers=auth_headers)
    assert r.status_code == 201, r.text
    assert r.json()["enabled"] is True

    r = client.post(f"/features/{name}/disable", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["enabled"] is False

    r = client.post(f"/features/{name}/enable", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["enabled"] is True

    r = client.delete(f"/features/{name}", headers=auth_headers)
    assert r.status_code == 204

    r = client.get(f"/features/{name}", headers=auth_headers)
    assert r.status_code == 404


def test_duplicate_feature_rejected(client, auth_headers):
    r = client.post("/features", json={"name": "voice_assistant", "display_name": "Dup"}, headers=auth_headers)
    assert r.status_code == 400
