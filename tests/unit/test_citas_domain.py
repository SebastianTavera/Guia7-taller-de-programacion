"""Appointment lifecycle rules."""

from datetime import datetime, timedelta

import pytest

from vitreo.domain.citas import (
    ESTADOS_LIBERAN_AGENDA,
    EstadoCita as E,
    puede_reprogramar,
    puede_transicionar,
    ventana_de_conflicto,
)

PERMITIDAS = {
    (E.PROGRAMADA, E.CONFIRMADA),
    (E.PROGRAMADA, E.CANCELADA),
    (E.PROGRAMADA, E.NO_ASISTIO),
    (E.CONFIRMADA, E.EN_CURSO),
    (E.CONFIRMADA, E.CANCELADA),
    (E.CONFIRMADA, E.NO_ASISTIO),
    (E.EN_CURSO, E.ATENDIDA),
}


@pytest.mark.parametrize("actual", list(E))
@pytest.mark.parametrize("nuevo", list(E))
def test_transitions_match_the_lifecycle(actual: E, nuevo: E) -> None:
    assert puede_transicionar(actual, nuevo) is ((actual, nuevo) in PERMITIDAS)


@pytest.mark.parametrize("estado", list(E))
def test_only_pending_appointments_can_be_rescheduled(estado: E) -> None:
    assert puede_reprogramar(estado) is (estado in {E.PROGRAMADA, E.CONFIRMADA})


def test_status_values_are_the_public_api_contract() -> None:
    assert [e.value for e in E] == ["PROGRAMADA", "CONFIRMADA", "EN_CURSO", "ATENDIDA", "CANCELADA", "NO_ASISTIO"]


def test_cancelled_and_no_show_free_the_agenda() -> None:
    assert ESTADOS_LIBERAN_AGENDA == {E.CANCELADA, E.NO_ASISTIO}


def test_conflict_window_is_30_minutes_each_side() -> None:
    inicio = datetime(2026, 11, 10, 9, 0)

    assert ventana_de_conflicto(inicio) == (inicio - timedelta(minutes=30), inicio + timedelta(minutes=30))
