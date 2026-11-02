"""SQLAlchemy engine, session factory, declarative base and the request-scoped session."""

from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from vitreo.config import settings

_IS_SQLITE = settings.database_url.startswith("sqlite")
_IN_MEMORY = settings.database_url in ("sqlite://", "sqlite:///:memory:")

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if _IS_SQLITE else {},
    # An in-memory SQLite database lives in one connection, so it must be shared.
    poolclass=StaticPool if _IN_MEMORY else None,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

if _IS_SQLITE:

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _record) -> None:  # type: ignore[no-untyped-def]
        dbapi_connection.execute("PRAGMA foreign_keys=ON")


class Base(DeclarativeBase):
    """Base class for all ORM models."""


def get_db() -> Iterator[Session]:
    with SessionLocal() as db:
        yield db
