"""JWT login, current user and RBAC: the three test endpoints required by the guide (login, ADMIN, USER)."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import jwt
from fastapi.testclient import TestClient

from tests.conftest import PASSWORD, Headers
from vitreo.config import settings
from vitreo.models import Rol, Usuario
from vitreo.security.tokens import ISSUER, create_access_token

LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"
ADMIN_USERS = "/api/v1/admin/usuarios"


def _login(client: TestClient, correo: str, password: str = PASSWORD):  # type: ignore[no-untyped-def]
    return client.post(LOGIN, json={"correo": correo, "password": password})


def test_login_returns_a_bearer_token_that_identifies_the_user(
    client: TestClient, make_user: Callable[..., Usuario]
) -> None:
    user = make_user(Rol.ENFERMERIA)

    response = _login(client, user.correo.upper())  # emails are case-insensitive

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == settings.jwt_expire_minutes * 60
    me = client.get(ME, headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["id"] == user.id
    assert me.json()["rol"] == "ENFERMERIA"
    assert "contrasena_hash" not in me.json()


def test_wrong_password_and_unknown_email_get_the_same_generic_401(
    client: TestClient, make_user: Callable[..., Usuario]
) -> None:
    user = make_user(Rol.ADMIN)

    wrong_password = _login(client, user.correo, "not-the-password")
    unknown_email = _login(client, "nobody@vitreo.test")

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()
    assert wrong_password.json()["detail"] == "Invalid email or password."


def test_inactive_user_cannot_log_in(client: TestClient, make_user: Callable[..., Usuario]) -> None:
    user = make_user(Rol.RECEPCION, activo=False)

    assert _login(client, user.correo).status_code == 401


def test_account_is_locked_after_five_failed_attempts(client: TestClient, make_user: Callable[..., Usuario]) -> None:
    user = make_user(Rol.ADMIN)
    for _ in range(5):
        assert _login(client, user.correo, "wrong-password").status_code == 401

    locked = _login(client, user.correo)  # even the right password is refused while locked

    assert locked.status_code == 429
    assert int(locked.headers["Retry-After"]) > 0


def test_successful_login_resets_the_failure_counter(client: TestClient, make_user: Callable[..., Usuario]) -> None:
    user = make_user(Rol.ADMIN)
    for _ in range(4):
        _login(client, user.correo, "wrong-password")
    assert _login(client, user.correo).status_code == 200

    for _ in range(4):
        _login(client, user.correo, "wrong-password")

    assert _login(client, user.correo).status_code == 200


def test_login_rejects_unknown_fields(client: TestClient) -> None:
    response = client.post(LOGIN, json={"correo": "a@b.co", "password": "x", "rol": "ADMIN"})

    assert response.status_code == 422


def test_me_without_token_is_401(client: TestClient) -> None:
    response = client.get(ME)

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_tampered_token_is_401(client: TestClient, make_user: Callable[..., Usuario]) -> None:
    token = create_access_token(make_user(Rol.RECEPCION).id, "RECEPCION")
    header, payload, signature = token.split(".")
    tampered = f"{header}.{payload}.{signature[::-1]}"

    assert client.get(ME, headers={"Authorization": f"Bearer {tampered}"}).status_code == 401


def test_expired_token_is_401(client: TestClient, make_user: Callable[..., Usuario]) -> None:
    old = datetime.now(UTC) - timedelta(hours=2)
    token = create_access_token(make_user(Rol.ADMIN).id, "ADMIN", now=old)

    assert client.get(ME, headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_token_of_deactivated_or_deleted_user_is_401(client: TestClient, db, make_user) -> None:  # type: ignore[no-untyped-def]
    user = make_user(Rol.ADMIN)
    token = create_access_token(user.id, "ADMIN")
    user.activo = False
    db.commit()

    assert client.get(ME, headers={"Authorization": f"Bearer {token}"}).status_code == 401
    assert client.get(ME, headers={"Authorization": f"Bearer {create_access_token(999, 'ADMIN')}"}).status_code == 401


def test_token_with_non_numeric_subject_is_401(client: TestClient) -> None:
    now = datetime.now(UTC)
    claims = {"sub": "admin", "rol": "ADMIN", "iat": now, "exp": now + timedelta(minutes=5), "iss": ISSUER}
    token = jwt.encode(claims, settings.jwt_secret, algorithm="HS256")

    assert client.get(ME, headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_role_comes_from_database_not_from_token(client: TestClient, make_user: Callable[..., Usuario]) -> None:
    user = make_user(Rol.RECEPCION)
    token_claiming_admin = create_access_token(user.id, "ADMIN")

    response = client.get(ADMIN_USERS, headers={"Authorization": f"Bearer {token_claiming_admin}"})

    assert response.status_code == 403


def test_admin_endpoint_allows_admin_and_forbids_every_other_role(
    client: TestClient, auth: Callable[..., Headers]
) -> None:
    assert client.get(ADMIN_USERS, headers=auth(Rol.ADMIN)).status_code == 200
    for rol in (Rol.RECEPCION, Rol.ENFERMERIA):
        response = client.get(ADMIN_USERS, headers=auth(rol))
        assert response.status_code == 403
        assert response.json()["error"] == "Forbidden"
    assert client.get(ADMIN_USERS).status_code == 401
