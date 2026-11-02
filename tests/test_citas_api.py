"""Appointments: scheduling conflicts, lifecycle and object-level authorization."""

from collections.abc import Callable
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from tests.conftest import Headers, future
from vitreo.models import Rol

CITAS = "/api/v1/citas"


@pytest.fixture
def recepcion(auth: Callable[..., Headers]) -> Headers:
    return auth(Rol.RECEPCION)


@pytest.fixture
def agendar(client: TestClient, recepcion: Headers, catalogo: SimpleNamespace) -> Callable[..., dict]:
    def _agendar(fecha_hora: str, medico: int | None = None, consultorio: int | None = None) -> dict:
        payload = {
            "paciente_id": catalogo.paciente,
            "medico_id": medico or catalogo.nieto,
            "consultorio_id": consultorio or catalogo.c302,
            "fecha_hora": fecha_hora,
        }
        response = client.post(CITAS, json=payload, headers=recepcion)
        return {"status": response.status_code, **response.json()}

    return _agendar


def test_reception_schedules_an_appointment(agendar: Callable[..., dict]) -> None:
    cita = agendar(future(9))

    assert cita["status"] == 201
    assert cita["estado"] == "PROGRAMADA"
    assert cita["motivo_cancelacion"] is None


def test_past_dates_and_unknown_references_are_rejected(
    agendar: Callable[..., dict], client: TestClient, recepcion: Headers, catalogo: SimpleNamespace
) -> None:
    assert agendar((datetime.now() - timedelta(hours=1)).isoformat())["status"] == 422
    assert agendar(future(9), medico=999)["status"] == 404
    assert agendar(future(9), consultorio=999)["status"] == 404
    payload = {"paciente_id": 999, "medico_id": catalogo.nieto, "consultorio_id": catalogo.c302, "fecha_hora": future(9)}
    assert client.post(CITAS, json=payload, headers=recepcion).status_code == 404


def test_timezone_aware_dates_are_accepted(agendar: Callable[..., dict]) -> None:
    aware = (datetime.now().astimezone() + timedelta(days=2)).replace(microsecond=0)

    cita = agendar(aware.isoformat())

    assert cita["status"] == 201
    assert cita["fecha_hora"] == aware.replace(tzinfo=None).isoformat()


def test_overlapping_appointments_for_doctor_or_office_are_409(
    agendar: Callable[..., dict], catalogo: SimpleNamespace
) -> None:
    agendar(future(9))

    assert agendar(future(9, 29))["status"] == 409  # same doctor and office
    assert agendar(future(9, 15), medico=catalogo.ruiz)["status"] == 409  # same office
    assert agendar(future(8, 31), consultorio=catalogo.c105)["status"] == 409  # same doctor
    assert agendar(future(9, 30))["status"] == 201  # back-to-back is fine
    assert agendar(future(9), medico=catalogo.ruiz, consultorio=catalogo.c105)["status"] == 201


def test_cancelled_appointments_free_the_slot(
    agendar: Callable[..., dict], client: TestClient, recepcion: Headers
) -> None:
    cita = agendar(future(9))

    cancelada = client.post(f"{CITAS}/{cita['id']}/cancelar", json={"motivo": "Paciente enfermo"}, headers=recepcion)

    assert cancelada.json()["estado"] == "CANCELADA"
    assert cancelada.json()["motivo_cancelacion"] == "Paciente enfermo"
    assert agendar(future(9))["status"] == 201
    again = client.post(f"{CITAS}/{cita['id']}/cancelar", json={"motivo": "Otra vez"}, headers=recepcion)
    assert again.status_code == 409


def test_cancelling_requires_a_reason(agendar: Callable[..., dict], client: TestClient, recepcion: Headers) -> None:
    cita = agendar(future(9))

    assert client.post(f"{CITAS}/{cita['id']}/cancelar", json={"motivo": ""}, headers=recepcion).status_code == 422
    estado = client.patch(f"{CITAS}/{cita['id']}/estado", json={"estado": "CANCELADA"}, headers=recepcion)
    assert estado.status_code == 422


def test_lifecycle_follows_allowed_transitions(
    agendar: Callable[..., dict], client: TestClient, auth: Callable[..., Headers], catalogo: SimpleNamespace
) -> None:
    medico = auth(Rol.MEDICO, catalogo.nieto)
    cita = agendar(future(9))
    url = f"{CITAS}/{cita['id']}/estado"

    assert client.patch(url, json={"estado": "ATENDIDA"}, headers=medico).status_code == 409
    for estado in ("CONFIRMADA", "EN_CURSO", "ATENDIDA"):
        response = client.patch(url, json={"estado": estado}, headers=medico)
        assert response.status_code == 200
        assert response.json()["estado"] == estado


def test_reschedule_moves_the_appointment_and_requires_confirmation_again(
    agendar: Callable[..., dict], client: TestClient, recepcion: Headers
) -> None:
    cita = agendar(future(9))
    otra = agendar(future(11))
    client.patch(f"{CITAS}/{cita['id']}/estado", json={"estado": "CONFIRMADA"}, headers=recepcion)
    url = f"{CITAS}/{cita['id']}/reprogramar"

    assert client.post(url, json={"fecha_hora": future(11, 10)}, headers=recepcion).status_code == 409
    moved = client.post(url, json={"fecha_hora": future(9, 15)}, headers=recepcion)  # overlaps only itself

    assert moved.status_code == 200
    assert moved.json()["fecha_hora"] == future(9, 15)
    assert moved.json()["estado"] == "PROGRAMADA"
    client.post(f"{CITAS}/{otra['id']}/cancelar", json={"motivo": "No puede asistir"}, headers=recepcion)
    cancelled = client.post(f"{CITAS}/{otra['id']}/reprogramar", json={"fecha_hora": future(14)}, headers=recepcion)
    assert cancelled.status_code == 409


def test_doctors_only_see_their_own_appointments(
    agendar: Callable[..., dict], client: TestClient, auth: Callable[..., Headers], catalogo: SimpleNamespace
) -> None:
    propia = agendar(future(9))
    ajena = agendar(future(9), medico=catalogo.ruiz, consultorio=catalogo.c105)
    nieto = auth(Rol.MEDICO, catalogo.nieto)

    agenda = client.get(CITAS, params={"medico_id": catalogo.ruiz}, headers=nieto).json()

    assert [c["id"] for c in agenda] == [propia["id"]]  # the medico_id filter cannot be abused
    assert client.get(f"{CITAS}/{propia['id']}", headers=nieto).status_code == 200
    assert client.get(f"{CITAS}/{ajena['id']}", headers=nieto).status_code == 404
    patch = client.patch(f"{CITAS}/{ajena['id']}/estado", json={"estado": "CONFIRMADA"}, headers=nieto)
    assert patch.status_code == 404
    assert client.post(f"{CITAS}/{propia['id']}/cancelar", json={"motivo": "Prueba"}, headers=nieto).status_code == 403


def test_list_filters_by_doctor_date_and_status(
    agendar: Callable[..., dict], client: TestClient, recepcion: Headers, catalogo: SimpleNamespace
) -> None:
    hoy = agendar(future(9))
    agendar(future(9), medico=catalogo.ruiz, consultorio=catalogo.c105)
    manana = agendar(future(33))
    client.patch(f"{CITAS}/{manana['id']}/estado", json={"estado": "CONFIRMADA"}, headers=recepcion)
    dia = future(9)[:10]

    def ids(**params: object) -> list[int]:
        return [c["id"] for c in client.get(CITAS, params=params, headers=recepcion).json()]

    assert len(ids()) == 3
    assert ids(medico_id=catalogo.nieto, fecha=dia) == [hoy["id"]]
    assert ids(estado="CONFIRMADA") == [manana["id"]]
    assert client.get(f"{CITAS}/999", headers=recepcion).status_code == 404
