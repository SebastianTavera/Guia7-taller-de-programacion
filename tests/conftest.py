"""Shared fixtures: in-memory database, API client, catalog data and per-role auth headers."""

import os
import secrets

# Must be set before importing the app so nothing touches a real database or secret.
os.environ.update(APP_ENV="test", DATABASE_URL="sqlite://", JWT_SECRET=secrets.token_urlsafe(48))

from collections.abc import Callable, Iterator
from datetime import date, datetime, timedelta
from itertools import count
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from vitreo.api.main import app
from vitreo.api.routers.auth import login_limiter
from vitreo.db import Base, SessionLocal, engine
from vitreo.models import Consultorio, Especialidad, Medico, Paciente, Rol, Usuario
from vitreo.security.passwords import hash_password
from vitreo.security.tokens import create_access_token

PASSWORD = secrets.token_urlsafe(16)
PASSWORD_HASH = hash_password(PASSWORD)  # hashed once: scrypt is deliberately slow
_emails = count(1)

Headers = dict[str, str]


@pytest.fixture(autouse=True)
def _clean_state() -> Iterator[None]:
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    login_limiter.clear()


@pytest.fixture
def db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def catalogo(db: Session) -> SimpleNamespace:
    cardio = Especialidad(nombre="Cardiología")
    pediatria = Especialidad(nombre="Pediatría")
    nieto = Medico(nombres="Andrés", apellidos="Nieto", especialidad=cardio, turno="Mañana")
    ruiz = Medico(nombres="Valentina", apellidos="Ruiz", especialidad=pediatria, turno="Mañana")
    c302 = Consultorio(numero="302", ubicacion="Piso 3")
    c105 = Consultorio(numero="105", ubicacion="Piso 1")
    paciente = Paciente(
        documento="1010101010",
        nombres="Marcela",
        apellidos="Rincón",
        fecha_nacimiento=date(1958, 3, 14),
        tipo_sangre="O+",
        alergias="Penicilina",
    )
    db.add_all([cardio, pediatria, nieto, ruiz, c302, c105, paciente])
    db.commit()
    return SimpleNamespace(
        cardio=cardio.id, pediatria=pediatria.id, nieto=nieto.id, ruiz=ruiz.id,
        c302=c302.id, c105=c105.id, paciente=paciente.id,
    )  # fmt: skip


@pytest.fixture
def make_user(db: Session) -> Callable[..., Usuario]:
    def _make(rol: Rol, medico_id: int | None = None, activo: bool = True) -> Usuario:
        user = Usuario(
            nombre=f"{rol.title()} Test",
            correo=f"{rol.lower()}{next(_emails)}@vitreo.test",
            contrasena_hash=PASSWORD_HASH,
            rol=rol,
            activo=activo,
            medico_id=medico_id,
        )
        db.add(user)
        db.commit()
        return user

    return _make


@pytest.fixture
def auth(make_user: Callable[..., Usuario]) -> Callable[..., Headers]:
    """Return Authorization headers for a new user with the given role."""

    def _auth(rol: Rol, medico_id: int | None = None) -> Headers:
        user = make_user(rol, medico_id)
        return {"Authorization": f"Bearer {create_access_token(user.id, user.rol)}"}

    return _auth


def future(hours: int = 24, minutes: int = 0) -> str:
    """ISO datetime in the future, aligned to the hour so tests can reason about overlaps."""
    base = datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(days=1)
    return (base + timedelta(hours=hours, minutes=minutes)).isoformat()
