"""Authentication: login (JWT issuance) and the current-user endpoint."""

import logging
import secrets
from functools import cache

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from vitreo.api.deps import CurrentUser, DbSession
from vitreo.config import settings
from vitreo.models import Usuario
from vitreo.schemas import ErrorOut, LoginIn, TokenOut, UsuarioOut
from vitreo.security.passwords import hash_password, verify_password
from vitreo.security.rate_limit import LoginAttemptLimiter
from vitreo.security.tokens import create_access_token

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])

audit = logging.getLogger("vitreo.audit")
login_limiter = LoginAttemptLimiter()

INVALID_CREDENTIALS = "Invalid email or password."


@cache
def _dummy_hash() -> str:
    """Hash checked when the account does not exist, so response time does not reveal valid emails."""
    return hash_password(secrets.token_urlsafe(16))


@router.post(
    "/login",
    response_model=TokenOut,
    summary="Log in and get a JWT access token",
    responses={
        401: {"model": ErrorOut, "description": "Invalid credentials."},
        429: {"model": ErrorOut, "description": "Too many failed attempts for this account."},
    },
)
def login(payload: LoginIn, db: DbSession) -> TokenOut:
    correo = payload.correo.lower()
    if login_limiter.is_blocked(correo):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Too many failed login attempts. Try again later.",
            headers={"Retry-After": str(login_limiter.retry_after(correo))},
        )

    user = db.scalar(select(Usuario).where(Usuario.correo == correo))
    password_ok = verify_password(payload.password, user.contrasena_hash if user else _dummy_hash())
    if user is None or not password_ok or not user.activo:
        login_limiter.register_failure(correo)
        audit.warning("login_failed user_id=%s", user.id if user else "unknown")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, INVALID_CREDENTIALS, headers={"WWW-Authenticate": "Bearer"})

    login_limiter.reset(correo)
    audit.info("login_ok user_id=%s rol=%s", user.id, user.rol)
    return TokenOut(
        access_token=create_access_token(user.id, user.rol), expires_in=settings.jwt_expire_minutes * 60
    )


@router.get(
    "/me",
    response_model=UsuarioOut,
    summary="Current user (any authenticated role)",
    responses={401: {"model": ErrorOut, "description": "Missing or invalid token."}},
)
def me(user: CurrentUser) -> Usuario:
    return user
