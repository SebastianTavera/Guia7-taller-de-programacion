"""Patients and doctors endpoints."""

from collections.abc import Callable
from types import SimpleNamespace

from fastapi.testclient import TestClient

from tests.conftest import Headers
from vitreo.models import Rol

PACIENTES = "/api/v1/pacientes"
NUEVO = {
    "documento": "1020202020",
    "nombres": "Julián",
    "apellidos": "Torres",
    "fecha_nacimiento": "1992-07-02",
    "tipo_sangre": "A-",
    "telefono": "+57 300 123 4567",
}


def test_reception_registers_patient(client: TestClient, auth: Callable[..., Headers]) -> None:
    response = client.post(PACIENTES, json=NUEVO, headers=auth(Rol.RECEPCION))

    assert response.status_code == 201
    assert response.json() | NUEVO == response.json()
    assert response.json()["alergias"] is None


def test_nurses_cannot_register_patients(client: TestClient, auth: Callable[..., Headers]) -> None:
    assert client.post(PACIENTES, json=NUEVO, headers=auth(Rol.ENFERMERIA)).status_code == 403


def test_duplicate_document_is_409(client: TestClient, auth: Callable[..., Headers]) -> None:
    headers = auth(Rol.RECEPCION)
    client.post(PACIENTES, json=NUEVO, headers=headers)

    assert client.post(PACIENTES, json=NUEVO, headers=headers).status_code == 409


def test_invalid_patient_data_is_422(client: TestClient, auth: Callable[..., Headers]) -> None:
    headers = auth(Rol.RECEPCION)

    for cambio in ({"fecha_nacimiento": "2999-01-01"}, {"tipo_sangre": "Z+"}, {"documento": "12; DROP"}):
        assert client.post(PACIENTES, json={**NUEVO, **cambio}, headers=headers).status_code == 422


def test_list_search_and_get_patients(
    client: TestClient, auth: Callable[..., Headers], catalogo: SimpleNamespace
) -> None:
    headers = auth(Rol.MEDICO, catalogo.nieto)
    client.post(PACIENTES, json=NUEVO, headers=auth(Rol.RECEPCION))

    todos = client.get(PACIENTES, headers=headers).json()
    encontrados = client.get(PACIENTES, params={"q": "torr"}, headers=headers).json()

    assert [p["apellidos"] for p in todos] == ["Rincón", "Torres"]
    assert [p["documento"] for p in encontrados] == ["1020202020"]
    assert client.get(f"{PACIENTES}/{catalogo.paciente}", headers=headers).json()["nombres"] == "Marcela"
    assert client.get(f"{PACIENTES}/999", headers=headers).status_code == 404
    assert client.get(PACIENTES, params={"limit": 101}, headers=headers).status_code == 422
    assert client.get(PACIENTES).status_code == 401


def test_doctors_can_be_filtered_by_specialty(
    client: TestClient, auth: Callable[..., Headers], catalogo: SimpleNamespace
) -> None:
    headers = auth(Rol.RECEPCION)

    todos = client.get("/api/v1/medicos", headers=headers).json()
    pediatras = client.get("/api/v1/medicos", params={"especialidad_id": catalogo.pediatria}, headers=headers).json()

    assert [m["apellidos"] for m in todos] == ["Nieto", "Ruiz"]
    assert pediatras == [
        {"id": catalogo.ruiz, "nombres": "Valentina", "apellidos": "Ruiz", "especialidad": "Pediatría", "turno": "Mañana"}
    ]
