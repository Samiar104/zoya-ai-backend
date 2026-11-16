"""Backup tests — create, list, download, restore."""
import io


def test_backup_create_list_download(client, auth_headers):
    r = client.post("/backup/create", headers=auth_headers)
    assert r.status_code == 200, r.text
    filename = r.json()["filename"]
    assert filename.startswith("zoya-backup-")

    r = client.get("/backup/list", headers=auth_headers)
    assert r.status_code == 200
    assert any(b["filename"] == filename for b in r.json()["backups"])

    r = client.get(f"/backup/download/{filename}", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.content) > 0


def test_backup_restore_missing_file(client, auth_headers):
    r = client.post("/backup/restore", json={"filename": "no-such-backup.db"}, headers=auth_headers)
    assert r.status_code == 404


def test_backup_requires_auth(client):
    r = client.post("/backup/create")
    assert r.status_code == 401
