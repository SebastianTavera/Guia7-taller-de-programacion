"""JWT access tokens (HS256) with mandatory expiration, issuer and role claims."""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from vitreo.config import settings

ALGORITHM = "HS256"
ISSUER = "vitreo-api"
REQUIRED_CLAIMS = ["sub", "rol", "iat", "exp", "iss"]


def create_access_token(user_id: int, rol: str, now: datetime | None = None) -> str:
    issued_at = now or datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "rol": rol,
        "iat": issued_at,
        "exp": issued_at + timedelta(minutes=settings.jwt_expire_minutes),
        "iss": ISSUER,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Validate signature, algorithm, expiration and issuer. Raises jwt.InvalidTokenError."""
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[ALGORITHM],  # pinned: rejects "none" and algorithm-confusion attacks
        issuer=ISSUER,
        options={"require": REQUIRED_CLAIMS},
    )
