"""Regression tests for security fixes."""
import uuid
from datetime import date, timedelta
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from pydantic import ValidationError

import app.main as main_module
from app.config import Settings
from app.database import init_db, close_db
from app.main import app
from app.services import auth_service
from app.utils.security import auth_limiter


@pytest_asyncio.fixture(loop_scope="session", autouse=True)
async def setup_test_db():
    await init_db()
    yield
    await close_db()


def client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def register(c: AsyncClient, prefix: str = "sec"):
    email = f"{prefix}_{uuid.uuid4().hex[:8]}@example.com"
    resp = await c.post("/api/auth/register", json={
        "name": "Sec Tester", "email": email, "password": "correct-horse-battery",
    })
    assert resp.status_code == 200, resp.text
    return email, {"Authorization": f"Bearer {resp.json()['access_token']}"}


# --- Static file serving -----------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("path", [
    "/%2Fetc%2Fpasswd",
    "//etc/passwd",
    "/..%2Fconfig.py",
    "/..%2F..%2Fpyproject.toml",
    "/_app/..%2F..%2Fconfig.py",
])
async def test_static_serving_blocks_path_traversal(path, tmp_path, monkeypatch):
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("<html>spa</html>")
    (tmp_path / "config.py").write_text("SECRET = 'leak'")
    monkeypatch.setattr(main_module, "STATIC_DIR", static.resolve())

    async with client() as c:
        resp = await c.get(path)
    assert "SECRET" not in resp.text
    assert "root:" not in resp.text


@pytest.mark.asyncio
async def test_static_serving_still_serves_files(tmp_path, monkeypatch):
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("<html>spa</html>")
    (static / "robots.txt").write_text("User-agent: *")
    (static / "stats.html").write_text("<html>stats</html>")
    monkeypatch.setattr(main_module, "STATIC_DIR", static.resolve())

    async with client() as c:
        assert (await c.get("/robots.txt")).text == "User-agent: *"
        assert (await c.get("/stats")).text == "<html>stats</html>"
        assert (await c.get("/some/client/route")).text == "<html>spa</html>"


# --- Sessions ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cookie_auth_requires_csrf_header_for_writes():
    async with client() as c:
        await register(c, "csrf")  # sets the session cookie on the client
        c.headers.pop("Authorization", None)

        # Reads via cookie are fine
        assert (await c.get("/api/auth/me")).status_code == 200

        # Writes via cookie without the header are rejected (cross-site form/CSRF)
        blocked = await c.post("/api/goals", json={"title": "x", "target_value": 10})
        assert blocked.status_code == 403

        allowed = await c.post(
            "/api/goals",
            json={"title": "x", "target_value": 10},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert allowed.status_code == 201


@pytest.mark.asyncio
async def test_logout_revokes_existing_tokens():
    async with client() as c:
        _, headers = await register(c, "logout")
        assert (await c.get("/api/auth/me", headers=headers)).status_code == 200

        resp = await c.post("/api/auth/logout", headers=headers)
        assert resp.status_code == 200

        assert (await c.get("/api/auth/me", headers=headers)).status_code == 401


@pytest.mark.asyncio
async def test_forged_token_with_old_default_secret_rejected():
    from jose import jwt
    async with client() as c:
        _, headers = await register(c, "forge")
        me = (await c.get("/api/auth/me", headers=headers)).json()
        forged = jwt.encode(
            {"sub": me["_id"], "exp": 4102444800},
            "super-secret-workout-tracker-token-key-2026-prod",
            algorithm="HS256",
        )
        resp = await c.get("/api/auth/me", headers={"Authorization": f"Bearer {forged}"})
        assert resp.status_code == 401


def test_production_rejects_insecure_jwt_secret():
    for bad in ("", "super-secret-workout-tracker-token-key-change-in-prod-2026", "short"):
        with pytest.raises(ValidationError):
            Settings(ENVIRONMENT="production", JWT_SECRET=bad, _env_file=None)

    ok = Settings(ENVIRONMENT="production", JWT_SECRET="x" * 48, _env_file=None)
    assert ok.ALLOW_DEV_LOGIN is False
    assert "http://localhost:5173" not in ok.allowed_origins


@pytest.mark.asyncio
async def test_login_errors_do_not_reveal_account_type():
    async with client() as c:
        email, _ = await register(c, "enum")
        wrong = await c.post("/api/auth/login", json={"email": email, "password": "nope-nope"})
        missing = await c.post("/api/auth/login", json={"email": "nobody@example.com", "password": "nope-nope"})
        assert wrong.status_code == missing.status_code == 401
        assert wrong.json()["detail"] == missing.json()["detail"]


@pytest.mark.asyncio
async def test_login_is_rate_limited():
    auth_limiter.reset()
    async with client() as c:
        statuses = []
        for _ in range(auth_limiter.max_requests + 2):
            r = await c.post("/api/auth/login", json={"email": "brute@example.com", "password": "guess-guess"})
            statuses.append(r.status_code)
        assert statuses[0] == 401
        assert statuses[-1] == 429


def test_legacy_password_hashes_still_verify():
    import hashlib
    salt = "abcd" * 8
    legacy = f"{salt}:{hashlib.pbkdf2_hmac('sha256', b'pw123456', salt.encode(), 100000).hex()}"
    assert auth_service.verify_password("pw123456", legacy)
    assert auth_service.password_needs_rehash(legacy)
    assert not auth_service.password_needs_rehash(auth_service.hash_password("pw123456"))


# --- Google sign-in ------------------------------------------------------------

class _FakeResp:
    def __init__(self, data):
        self.status_code = 200
        self._data = data

    def json(self):
        return self._data


class _FakeAsyncClient:
    def __init__(self, data):
        self._data = data

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, *a, **k):
        return _FakeResp(self._data)


@pytest.mark.asyncio
async def test_google_tokeninfo_fallback_checks_audience(monkeypatch):
    monkeypatch.setattr(auth_service.settings, "GOOGLE_CLIENT_ID", "our-client-id")
    claims = {
        "aud": "some-other-app", "iss": "https://accounts.google.com",
        "sub": "123", "email": "victim@example.com", "email_verified": "true",
    }

    def boom(*a, **k):
        raise RuntimeError("cert fetch failed")

    with patch.object(auth_service.id_token, "verify_oauth2_token", boom), \
         patch.object(auth_service.httpx, "AsyncClient", lambda: _FakeAsyncClient(claims)):
        assert await auth_service.verify_google_credential("tok") is None

        claims["aud"] = "our-client-id"
        assert (await auth_service.verify_google_credential("tok"))["email"] == "victim@example.com"

        claims["email_verified"] = "false"
        assert await auth_service.verify_google_credential("tok") is None


@pytest.mark.asyncio
async def test_google_verify_rejected_without_client_id(monkeypatch):
    monkeypatch.setattr(auth_service.settings, "GOOGLE_CLIENT_ID", "")
    assert await auth_service.verify_google_credential("anything") is None


@pytest.mark.asyncio
async def test_google_callback_requires_matching_state():
    async with client() as c:
        resp = await c.get("/api/auth/google/callback?code=abc&state=attacker")
        assert resp.status_code in (302, 307)
        assert "error=oauth_failed" in resp.headers["location"]


# --- Challenges & validation ---------------------------------------------------

@pytest.mark.asyncio
async def test_challenge_detail_hidden_from_non_members():
    async with client() as c:
        _, owner = await register(c, "owner")
        _, outsider = await register(c, "outsider")
        start = date.today()
        created = await c.post("/api/challenges", headers=owner, json={
            "title": "Private", "challenge_type": "total_volume", "exercise_name": "Push-ups",
            "target_value": 100, "start_date": start.isoformat(),
            "end_date": (start + timedelta(days=7)).isoformat(),
        })
        assert created.status_code == 201
        c_id = created.json()["_id"]

        resp = await c.get(f"/api/challenges/{c_id}", headers=outsider)
        assert resp.status_code == 404
        assert created.json()["invite_code"] not in resp.text


@pytest.mark.asyncio
async def test_regex_metacharacters_in_names_are_escaped():
    async with client() as c:
        _, headers = await register(c, "regex")
        # ".*" would previously match an existing exercise and be reported as a duplicate
        resp = await c.post("/api/exercises", headers=headers, json={"name": ".*"})
        assert resp.status_code == 201
        # An invalid pattern previously caused a server error
        resp = await c.post("/api/exercises", headers=headers, json={"name": "(unclosed"})
        assert resp.status_code == 201


@pytest.mark.asyncio
async def test_input_bounds_are_enforced():
    async with client() as c:
        _, headers = await register(c, "bounds")
        assert (await c.post("/api/workouts/quick-log", headers=headers, json={
            "exercise_name": "Push-ups", "reps": -50,
        })).status_code == 422
        assert (await c.post("/api/workouts/quick-log", headers=headers, json={
            "exercise_name": "Push-ups", "reps": 10_000_000,
        })).status_code == 422
        assert (await c.put("/api/auth/preferences", headers=headers, json={
            "theme": "<script>",
        })).status_code == 422


@pytest.mark.asyncio
async def test_account_export_and_delete():
    async with client() as c:
        email, headers = await register(c, "gdpr")
        await c.post("/api/workouts/quick-log", headers=headers, json={"exercise_name": "Push-ups", "reps": 5})

        export = await c.get("/api/auth/me/export", headers=headers)
        assert export.status_code == 200
        body = export.json()
        assert body["profile"]["email"] == email
        assert "hashed_password" not in body["profile"]
        assert len(body["workouts"]) == 1

        assert (await c.delete("/api/auth/me", headers=headers)).status_code == 204
        assert (await c.get("/api/auth/me", headers=headers)).status_code == 401


@pytest.mark.asyncio
async def test_security_headers_present():
    async with client() as c:
        resp = await c.get("/api/health")
        assert resp.headers["x-content-type-options"] == "nosniff"
        assert resp.headers["x-frame-options"] == "DENY"
        assert resp.headers["cache-control"] == "no-store"
        assert "database" not in resp.json()
