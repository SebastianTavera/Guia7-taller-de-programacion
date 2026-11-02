"""Application settings, read once from environment variables (.env in development)."""

import logging
import os
import secrets
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

MIN_SECRET_LENGTH = 32

logger = logging.getLogger("vitreo")


@dataclass(frozen=True)
class Settings:
    env: str
    database_url: str
    jwt_secret: str
    jwt_expire_minutes: int
    cors_origins: tuple[str, ...]

    @property
    def is_production(self) -> bool:
        return self.env == "production"


def load_settings() -> Settings:
    env = os.getenv("APP_ENV", "development")
    secret = os.getenv("JWT_SECRET", "")
    if len(secret) < MIN_SECRET_LENGTH:
        if env == "production":
            raise RuntimeError(f"JWT_SECRET must have at least {MIN_SECRET_LENGTH} characters in production.")
        # Never fall back to a hard-coded key: a random one only invalidates tokens on restart.
        secret = secrets.token_urlsafe(48)
        logger.warning("JWT_SECRET is not set; using a random secret for this process.")

    origins = os.getenv("CORS_ORIGINS", "http://localhost:5500")
    return Settings(
        env=env,
        database_url=os.getenv("DATABASE_URL", "sqlite:///./vitreo.db"),
        jwt_secret=secret,
        jwt_expire_minutes=int(os.getenv("JWT_EXPIRE_MINUTES", "30")),
        cors_origins=tuple(o.strip() for o in origins.split(",") if o.strip()),
    )


settings = load_settings()
