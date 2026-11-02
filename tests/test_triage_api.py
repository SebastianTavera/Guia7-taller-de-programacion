"""Triage registration and the prioritized ER queue."""

from collections.abc import Callable
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from tests.conftest import Headers
from vitreo.models import Rol

TRIAGE = "/api/v1/triage"
VITALES = {
    "frecuencia_cardiaca": 80,
    "frecuencia_respiratoria": 16,
    "saturacion_oxigeno": 98,
    "presion_sistolica": 120,
    "temperatura": 36.8,
    "dolor": 2,
    "recursos_estimados": 1,
}


@pytest.fixture
def enfermeria(auth: Callable[..., Headers]) -> Headers:
    return auth(Rol.ENFERMERIA)


def _registrar(client: TestClient, headers: Headers, paciente_id: int, **cambios: object) -> dict:
    payload = {"paciente_id": paciente_id, "sintomas": "Dolor torácico", **VITALES, **cambios}
    response = client.post(TRIAGE, json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def test_triage_is_classified_automatically(
    client: TestClient, enfermeria: Headers, catalogo: SimpleNamespace, caplog: pytest.LogCaptureFixture
) -> None:
    critico = _registrar(client, enfermeria, catalogo.paciente, saturacion_oxigeno=85)
    leve = _registrar(client, enfermeria, catalogo.paciente)

    assert (critico["nivel_esi"], critico["critico"]) == (1, True)
    assert (leve["nivel_esi"], leve["critico"]) == (4, False)
    assert f"critical_triage triage_id={critico['id']}" in caplog.text


def test_queue_is_ordered_by_esi_then_arrival(
    client: TestClient, enfermeria: Headers, auth: Callable[..., Headers], catalogo: SimpleNamespace
) -> None:
    esi4 = _registrar(client, enfermeria, catalogo.paciente)
    esi2_first = _registrar(client, enfermeria, catalogo.paciente, dolor=8)
    esi2_second = _registrar(client, enfermeria, catalogo.paciente, alto_riesgo=True)

    cola = client.get(f"{TRIAGE}/cola", headers=auth(Rol.MEDICO, catalogo.nieto)).json()

    assert [t["id"] for t in cola] == [esi2_first["id"], esi2_second["id"], esi4["id"]]


def test_attended_patients_leave_the_queue(
    client: TestClient, enfermeria: Headers, catalogo: SimpleNamespace
) -> None:
    triage = _registrar(client, enfermeria, catalogo.paciente)

    first = client.post(f"{TRIAGE}/{triage['id']}/atender", headers=enfermeria)
    again = client.post(f"{TRIAGE}/{triage['id']}/atender", headers=enfermeria)

    assert first.json()["atendido"] is True
    assert again.status_code == 409
    assert client.get(f"{TRIAGE}/cola", headers=enfermeria).json() == []
    assert client.post(f"{TRIAGE}/999/atender", headers=enfermeria).status_code == 404


def test_triage_permissions_and_validation(
    client: TestClient, enfermeria: Headers, auth: Callable[..., Headers], catalogo: SimpleNamespace
) -> None:
    payload = {"paciente_id": catalogo.paciente, "sintomas": "Fiebre", **VITALES}

    assert client.post(TRIAGE, json=payload, headers=auth(Rol.RECEPCION)).status_code == 403
    assert client.get(f"{TRIAGE}/cola", headers=auth(Rol.RECEPCION)).status_code == 403
    assert client.post(TRIAGE, json={**payload, "paciente_id": 999}, headers=enfermeria).status_code == 404
    assert client.post(TRIAGE, json={**payload, "saturacion_oxigeno": 150}, headers=enfermeria).status_code == 422
    assert client.post(TRIAGE, json={**payload, "nivel_esi": 5}, headers=enfermeria).status_code == 422
