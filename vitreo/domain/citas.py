"""Appointment lifecycle: allowed state transitions and the scheduling window."""

from datetime import datetime, timedelta
from enum import StrEnum

DURACION_CITA = timedelta(minutes=30)


class EstadoCita(StrEnum):
    PROGRAMADA = "PROGRAMADA"
    CONFIRMADA = "CONFIRMADA"
    EN_CURSO = "EN_CURSO"
    ATENDIDA = "ATENDIDA"
    CANCELADA = "CANCELADA"
    NO_ASISTIO = "NO_ASISTIO"


# Appointments in these states free their slot in the agenda.
ESTADOS_LIBERAN_AGENDA = frozenset({EstadoCita.CANCELADA, EstadoCita.NO_ASISTIO})

_TRANSICIONES: dict[EstadoCita, frozenset[EstadoCita]] = {
    EstadoCita.PROGRAMADA: frozenset({EstadoCita.CONFIRMADA, EstadoCita.CANCELADA, EstadoCita.NO_ASISTIO}),
    EstadoCita.CONFIRMADA: frozenset({EstadoCita.EN_CURSO, EstadoCita.CANCELADA, EstadoCita.NO_ASISTIO}),
    EstadoCita.EN_CURSO: frozenset({EstadoCita.ATENDIDA}),
    EstadoCita.ATENDIDA: frozenset(),
    EstadoCita.CANCELADA: frozenset(),
    EstadoCita.NO_ASISTIO: frozenset(),
}


def puede_transicionar(actual: EstadoCita, nuevo: EstadoCita) -> bool:
    return nuevo in _TRANSICIONES[actual]


def puede_reprogramar(estado: EstadoCita) -> bool:
    return estado in (EstadoCita.PROGRAMADA, EstadoCita.CONFIRMADA)


def ventana_de_conflicto(fecha_hora: datetime) -> tuple[datetime, datetime]:
    """Open interval of start times that would overlap an appointment starting at fecha_hora."""
    return fecha_hora - DURACION_CITA, fecha_hora + DURACION_CITA
