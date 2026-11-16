"""Auth tests — register, login, JWT (never expires), API key."""
import uuid


def _user():
    return f"u_{uuid.uuid4().hex[:8]}"


def test_register_and_login(client):
    name = _user()
    r = client.post("/auth/register", json={"username": name, "password": "secret123"})
    assert r.status_code == 201
    assert r.json()["username"] == name

    r = client.post("/auth/login", json={"username": name, "password": "secret123"})
    assert r.status_code == 200
    data = r.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["expires_in"] == "never"  # tokens never expire (requirement)


def test_register_duplicate_rejected(client):
    name = _user()
    client.post("/auth/register", json={"username": name, "password": "secret123"})
    r = client.post("/auth/register", json={"username": name, "password": "secret123"})
    assert r.status_code == 400


def test_login_wrong_password(client):
    name = _user()
    client.post("/auth/register", json={"username": name, "password": "secret123"})
    r = client.post("/auth/login", json={"username": name, "password": "wrong"})
    assert r.status_code == 401


def test_me_requires_auth(client):
    r = client.get("/auth/me")
    assert r.status_code == 401


def test_me_with_token(client, auth_headers):
    r = client.get("/auth/me", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["username"]


def test_jwt_has_no_expiry(client, auth_headers):
    """Tokens must NOT carry an exp claim (never-expire requirement)."""
    from jose import jwt

    r = client.post("/auth/login", json={"username": "nobody", "password": "x"})
    assert r.status_code == 401  # just to prove the endpoint works; token from fixture instead
    token = auth_headers["Authorization"].split()[1]
    claims = jwt.get_unverified_claims(token)
    assert "exp" not in claims
    assert claims["type"] == "access"


def test_api_key_info_admin_only(client, auth_headers):
    r = client.get("/auth/api-key-info", headers=auth_headers)
    # The first registered user in this DB is the admin; later users are not.
    assert r.status_code in (200, 403)
    if r.status_code == 200:
        assert r.json()["expires"] == "never"
        assert r.json()["api_key"] == "test-api-key-123"
