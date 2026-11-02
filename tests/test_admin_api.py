"""ADMIN endpoints: user management and reports."""

from collections.abc import Callable
from types import SimpleNamespace

from fastapi.testclient import TestClient

from tests.conftest import Headers, future
from vitreo.models import Rol

USERS = "/api/v1/admin/usuarios"
NEW_USER = {"nombre": "Elena Castaño", "correo": "Elena@Vitreo.local", "password": "a-long-password-123", "rol": "ENFERMERIA"}


def test_admin_creates_user_without_exposing_the_password(client: TestClient, auth: Callable[..., Headers]) -> None:
    admin = auth(Rol.ADMIN)

    response = client.post(USERS, json=NEW_USER, headers=admin)

    assert response.status_code == 201
    body = response.json()
    assert body["correo"] == "elena@vitreo.local"
    assert body["rol"] == "ENFERMERIA"
    assert body["activo"] is True
    assert not {"password", "contrasena_hash"} & body.keys()
    login = client.post("/api/v1/auth/login", json={"correo": "elena@vitreo.local", "password": NEW_USER["password"]})
    assert login.status_code == 200


def test_duplicate_email_is_409(client: TestClient, auth: Callable[..., Headers]) -> None:
    admin = auth(Rol.ADMIN)
    client.post(USERS, json=NEW_USER, headers=admin)

    assert client.post(USERS, json=NEW_USER, headers=admin).status_code == 409


def test_mass_assignment_of_extra_fields_is_rejected(client: TestClient, auth: Callable[..., Headers]) -> None:
    response = client.post(USERS, json={**NEW_USER, "activo": False, "id": 1}, headers=auth(Rol.ADMIN))

    assert response.status_code == 422
    assert {p["field"] for p in response.json()["detail"]} == {"body.activo", "body.id"}


def test_weak_password_is_rejected(client: TestClient, auth: Callable[..., Headers]) -> None:
    response = client.post(USERS, json={**NEW_USER, "password": "short"}, headers=auth(Rol.ADMIN))

    assert response.status_code == 422
    assert "short" not in response.text  # rejected input is never echoed back


def test_medico_users_must_be_linked_to_an_existing_doctor(
    client: TestClient, auth: Callable[..., Headers], catalogo: SimpleNamespace
) -> None:
    admin = auth(Rol.ADMIN)
    medico = {**NEW_USER, "correo": "anieto@vitreo.local", "rol": "MEDICO"}

    assert client.post(USERS, json=medico, headers=admin).status_code == 422
    assert client.post(USERS, json={**NEW_USER, "medico_id": catalogo.nieto}, headers=admin).status_code == 422
    assert client.post(USERS, json={**medico, "medico_id": 999}, headers=admin).status_code == 404
    created = client.post(USERS, json={**medico, "medico_id": catalogo.nieto}, headers=admin)
    assert created.status_code == 201
    assert created.json()["medico_id"] == catalogo.nieto


def test_reports_count_appointments_and_triage(
    client: TestClient, auth: Callable[..., Headers], catalogo: SimpleNamespace
) -> None:
    recepcion, enfermeria = auth(Rol.RECEPCION), auth(Rol.ENFERMERIA)
    cita = {"paciente_id": catalogo.paciente, "medico_id": catalogo.nieto, "consultorio_id": catalogo.c302}
    first = client.post("/api/v1/citas", json={**cita, "fecha_hora": future(1)}, headers=recepcion).json()
    client.post("/api/v1/citas", json={**cita, "fecha_hora": future(2)}, headers=recepcion)
    client.post(f"/api/v1/citas/{first['id']}/cancelar", json={"motivo": "Paciente viaja"}, headers=recepcion)
    vitals = {"frecuencia_cardiaca": 80, "frecuencia_respiratoria": 16, "saturacion_oxigeno": 98,
              "presion_sistolica": 120, "temperatura": 36.5, "dolor": 1}  # fmt: skip
    triage = {"paciente_id": catalogo.paciente, "sintomas": "Control", **vitals}
    client.post("/api/v1/triage", json={**triage, "recursos_estimados": 0}, headers=enfermeria)
    client.post("/api/v1/triage", json={**triage, "recursos_estimados": 0}, headers=enfermeria)

    response = client.get("/api/v1/admin/reportes", headers=auth(Rol.ADMIN))

    assert response.status_code == 200
    assert response.json() == {
        "citas_por_estado": {"CANCELADA": 1, "PROGRAMADA": 1},
        "triage_por_nivel": {"5": 2},
        "pacientes_registrados": 1,
    }
