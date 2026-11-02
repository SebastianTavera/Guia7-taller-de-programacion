"""Request dependencies: DB session, JWT authentication and role-based authorization (RBAC)."""

from collections.abc import Callable
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from vitreo.db import Base, get_db
from vitreo.models import Rol, Usuario
from vitreo.security.tokens import decode_access_token

DbSession = Annotated[Session, Depends(get_db)]

_bearer = HTTPBearer(auto_error=False)


def _unauthorized() -> HTTPException:
    return HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Missing, invalid or expired access token.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    db: DbSession, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]
) -> Usuario:
    if credentials is None:
        raise _unauthorized()
    try:
        user_id = int(decode_access_token(credentials.credentials)["sub"])
    except (jwt.InvalidTokenError, ValueError):
        raise _unauthorized() from None
    # The role is read from the database, so a role change or deactivation applies immediately.
    user = db.get(Usuario, user_id)
    if user is None or not user.activo:
        raise _unauthorized()
    return user


CurrentUser = Annotated[Usuario, Depends(get_current_user)]


def require_roles(*roles: Rol) -> Callable[[Usuario], Usuario]:
    def checker(user: CurrentUser) -> Usuario:
        if user.rol not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role is not allowed to perform this action.")
        return user

    return checker


def get_or_404[M: Base](db: Session, model: type[M], object_id: int, label: str) -> M:
    obj = db.get(model, object_id)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{label} {object_id} was not found.")
    return obj
