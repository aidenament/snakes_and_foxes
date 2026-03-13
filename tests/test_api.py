from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from snakes_and_foxes.app import create_app
from snakes_and_foxes.session_store import SESSION_COOKIE_NAME, InMemoryGameSessionStore
from snakes_and_foxes.settings import AppSettings

REPO_ROOT = Path(__file__).resolve().parents[1]


def _new_game(client: TestClient, *, seed: int = 123, headers: dict[str, str] | None = None):
    return client.post("/api/game/new", json={"seed": seed}, headers=headers or {})


def test_homepage_renders(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert "Snakes and Foxes" in response.text
    assert "board-svg" in response.text
    assert "token-layer" in response.text
    assert "game-workspace" in response.text
    assert "Resume saved" in response.text
    assert "fonts.googleapis.com" not in response.text
    assert "fonts.gstatic.com" not in response.text


def test_frontend_bundle_uses_server_resume_and_no_local_storage():
    bundle = (REPO_ROOT / "src" / "snakes_and_foxes" / "static" / "js" / "app.js").read_text()
    assert "/api/game/current" in bundle
    assert "localStorage" not in bundle


def test_new_game_sets_session_cookie_and_returns_csrf_token(client: TestClient):
    response = _new_game(client)

    payload = response.json()
    assert response.status_code == 200
    assert payload["state"]["seed"] == 123
    assert payload["state"]["active_piece_id"] == "white"
    assert payload["state"]["phase"] == "waiting_for_roll"
    assert payload["csrf_token"]
    assert len(payload["state"]["enemies"]) == 16

    set_cookie = response.headers["set-cookie"]
    assert f"{SESSION_COOKIE_NAME}=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie


def test_get_current_requires_session(client: TestClient):
    response = client.get("/api/game/current")

    assert response.status_code == 404
    assert response.json()["detail"] == "No live game session."


def test_get_current_returns_state_and_csrf_when_session_exists(client: TestClient):
    created = _new_game(client).json()

    response = client.get("/api/game/current")

    payload = response.json()
    assert response.status_code == 200
    assert payload["state"]["seed"] == created["state"]["seed"]
    assert payload["csrf_token"] == created["csrf_token"]


def test_new_game_replaces_existing_session_without_needing_csrf(client: TestClient):
    first_payload = _new_game(client).json()

    replaced = _new_game(client, seed=456)

    assert replaced.status_code == 200
    assert replaced.json()["state"]["seed"] == 456
    assert replaced.json()["csrf_token"] != first_payload["csrf_token"]


def test_action_requires_session(client: TestClient):
    response = client.post("/api/game/action", json={"action": {"type": "roll"}})

    assert response.status_code == 404
    assert response.json()["detail"] == "No live game session."


def test_action_requires_matching_csrf_token(client: TestClient):
    payload = _new_game(client).json()

    missing = client.post("/api/game/action", json={"action": {"type": "roll"}})
    invalid = client.post(
        "/api/game/action",
        json={"action": {"type": "roll"}},
        headers={"X-CSRF-Token": "wrong-token"},
    )
    valid = client.post(
        "/api/game/action",
        json={"action": {"type": "roll"}},
        headers={"X-CSRF-Token": payload["csrf_token"]},
    )

    assert missing.status_code == 403
    assert invalid.status_code == 403
    assert valid.status_code == 200
    assert valid.json()["result"]["ok"] is True


def test_oversized_json_body_is_rejected(client: TestClient):
    huge_payload = '{"seed":1,"padding":"' + ("x" * 17_000) + '"}'

    response = client.post(
        "/api/game/new",
        content=huge_payload,
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "Request body too large."


def test_production_app_disables_docs_and_sets_security_headers():
    settings = AppSettings(
        app_env="production",
        allowed_hosts=("testserver",),
        public_origin="http://testserver",
        session_backend="redis",
        redis_url="redis://example.invalid/0",
        session_ttl_seconds=60 * 60,
        max_request_body_bytes=16_384,
    )
    store = InMemoryGameSessionStore(ttl_seconds=settings.session_ttl_seconds)

    with TestClient(create_app(settings=settings, session_store=store)) as client:
        homepage = client.get("/")
        docs = client.get("/docs")
        openapi = client.get("/openapi.json")
        created = _new_game(client, headers={"Origin": "http://testserver"})
        static_asset = client.get("/static/css/app.css")

        assert docs.status_code == 404
        assert openapi.status_code == 404
        assert homepage.headers["content-security-policy"].startswith("default-src 'self'")
        assert homepage.headers["x-content-type-options"] == "nosniff"
        assert homepage.headers["x-frame-options"] == "DENY"
        assert homepage.headers["referrer-policy"] == "no-referrer"
        assert homepage.headers["permissions-policy"] == "camera=(), microphone=(), geolocation=()"
        assert homepage.headers["cache-control"] == "no-store"
        assert created.headers["cache-control"] == "no-store"
        assert static_asset.headers["cache-control"] == "public, max-age=86400"
        assert "Secure" in created.headers["set-cookie"]


def test_production_app_rejects_invalid_origin_on_action():
    settings = AppSettings(
        app_env="production",
        allowed_hosts=("testserver",),
        public_origin="http://testserver",
        session_backend="redis",
        redis_url="redis://example.invalid/0",
        session_ttl_seconds=60 * 60,
        max_request_body_bytes=16_384,
    )
    store = InMemoryGameSessionStore(ttl_seconds=settings.session_ttl_seconds)

    with TestClient(create_app(settings=settings, session_store=store)) as client:
        created = _new_game(client, headers={"Origin": "http://testserver"}).json()
        blocked = client.post(
            "/api/game/action",
            json={"action": {"type": "roll"}},
            headers={
                "Origin": "https://evil.example",
                "X-CSRF-Token": created["csrf_token"],
            },
        )

        assert blocked.status_code == 403
        assert blocked.json()["detail"] == "Invalid request origin."


def test_static_assets_use_cache_headers(client: TestClient):
    response = client.get("/static/css/app.css")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"


def test_create_app_rejects_invalid_production_settings():
    with pytest.raises(ValueError):
        create_app(
            settings=AppSettings(
                app_env="production",
                session_backend="memory",
                session_ttl_seconds=60 * 60,
                max_request_body_bytes=16_384,
            ),
            session_store=InMemoryGameSessionStore(ttl_seconds=60 * 60),
        )
