"""Cross-cutting controls: security headers, body size limit, error shape, docs and settings."""

import asyncio
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from vitreo.api.errors import integrity_error_handler, unhandled_exception_handler
from vitreo.api.main import MAX_BODY_BYTES
from vitreo.config import MIN_SECRET_LENGTH, load_settings


def test_security_headers_are_sent(client: TestClient) -> None:
    response = client.get("/health")

    assert response.json() == {"status": "ok", "version": "1.0.0"}
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Content-Security-Policy"] == "default-src 'none'; frame-ancestors 'none'"
    assert "Strict-Transport-Security" not in response.headers  # only in production (HTTPS)


def test_swagger_ui_works_without_the_strict_csp(client: TestClient) -> None:
    response = client.get("/docs")

    assert response.status_code == 200
    assert "Content-Security-Policy" not in response.headers


def test_oversized_or_invalid_body_length_is_rejected(client: TestClient) -> None:
    big = client.post("/api/v1/auth/login", content=b"x" * (MAX_BODY_BYTES + 1))
    invalid = client.post("/api/v1/auth/login", content=b"{}", headers={"Content-Length": "-1"})

    assert big.status_code == 413
    assert big.json()["status"] == 413
    assert invalid.status_code == 413


def test_unknown_route_uses_the_error_shape(client: TestClient) -> None:
    response = client.get("/api/v1/nope")

    assert response.status_code == 404
    assert response.json() == {"error": "Not Found", "detail": "Not Found", "status": 404}


REQUEST = SimpleNamespace(method="POST", url=SimpleNamespace(path="/x"))


def test_unexpected_errors_hide_internal_details() -> None:
    response = asyncio.run(unhandled_exception_handler(REQUEST, RuntimeError("db password=secret")))  # type: ignore[arg-type]

    assert response.status_code == 500
    assert json.loads(response.body) == {
        "error": "Internal Server Error", "detail": "An unexpected error occurred.", "status": 500,
    }  # fmt: skip


def test_database_constraint_errors_become_409_without_sql_details() -> None:
    error = IntegrityError("INSERT INTO usuarios ...", {}, Exception("UNIQUE constraint failed"))

    response = asyncio.run(integrity_error_handler(REQUEST, error))  # type: ignore[arg-type]

    assert response.status_code == 409
    assert b"UNIQUE" not in response.body
    assert b"INSERT" not in response.body


def test_production_requires_a_strong_jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("JWT_SECRET", "short")

    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        load_settings()

    monkeypatch.setenv("JWT_SECRET", "k" * MIN_SECRET_LENGTH)
    assert load_settings().is_production is True


def test_development_without_secret_gets_a_random_one(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("JWT_SECRET")
    monkeypatch.setenv("CORS_ORIGINS", "http://a.test, ,http://b.test")

    first, second = load_settings(), load_settings()

    assert len(first.jwt_secret) >= MIN_SECRET_LENGTH
    assert first.jwt_secret != second.jwt_secret
    assert first.cors_origins == ("http://a.test", "http://b.test")


def test_production_disables_api_docs_and_adds_hsts(monkeypatch: pytest.MonkeyPatch) -> None:
    import vitreo.api.main as main

    monkeypatch.setattr(main, "settings", load_settings().__class__(**{**vars(main.settings), "env": "production"}))
    with TestClient(main.create_app()) as prod:
        assert prod.get("/docs").status_code == 404
        assert prod.get("/openapi.json").status_code == 404
        assert prod.get("/health").headers["Strict-Transport-Security"].startswith("max-age=")
