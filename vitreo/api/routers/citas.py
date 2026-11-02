"""Appointments: schedule, list, change status, cancel and reschedule (RF2-RF4, RF6).

Object-level authorization: a MEDICO only sees and updates their own appointments.
"""

from datetime import date, datetime, time, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from vitreo.api.deps import CurrentUser, DbSession, get_or_404, require_roles
from vitreo.domain.citas import (
    ESTADOS_LIBERAN_AGENDA,
    EstadoCita,
    puede_reprogramar,
    puede_transicionar,
    ventana_de_conflicto,
)
from vitreo.models import Cita, Consultorio, Medico, Paciente, Rol, Usuario
from vitreo.schemas import CambioEstadoIn, CancelarCitaIn, CitaCreate, CitaOut, ErrorOut, ReprogramarCitaIn

router = APIRouter(
    prefix="/api/v1/citas",
    tags=["Citas"],
    responses={
        401: {"model": ErrorOut, "description": "Missing or invalid token."},
        403: {"model": ErrorOut, "description": "Role not allowed."},
    },
)

Agenda = Depends(require_roles(Rol.RECEPCION, Rol.ADMIN))
_NOT_FOUND = {404: {"model": ErrorOut, "description": "Appointment not found."}}
_CONFLICT = {409: {"model": ErrorOut, "description": "Slot taken or invalid status change."}}


def _verificar_disponibilidad(
    db: Session, medico_id: int, consultorio_id: int, fecha_hora: datetime, excluir_id: int | None = None
) -> None:
    inicio, fin = ventana_de_conflicto(fecha_hora)
    query = select(Cita.id).where(
        Cita.fecha_hora > inicio,
        Cita.fecha_hora < fin,
        Cita.estado.not_in(ESTADOS_LIBERAN_AGENDA),
        or_(Cita.medico_id == medico_id, Cita.consultorio_id == consultorio_id),
    )
    if excluir_id is not None:
        query = query.where(Cita.id != excluir_id)
    if db.scalar(query.limit(1)) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "The doctor or the office already has an appointment then.")


def _cita_visible(db: Session, cita_id: int, user: Usuario) -> Cita:
    cita = db.get(Cita, cita_id)
    # 404 instead of 403 for other doctors' appointments, so ids cannot be enumerated.
    if cita is None or (user.rol == Rol.MEDICO and cita.medico_id != user.medico_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Appointment {cita_id} was not found.")
    return cita


def _transicionar(cita: Cita, nuevo: EstadoCita) -> None:
    if not puede_transicionar(cita.estado, nuevo):
        raise HTTPException(status.HTTP_409_CONFLICT, f"Cannot change an appointment from {cita.estado} to {nuevo}.")
    cita.estado = nuevo


@router.post(
    "",
    response_model=CitaOut,
    status_code=status.HTTP_201_CREATED,
    summary="Schedule an appointment (RECEPCION, ADMIN)",
    dependencies=[Agenda],
    responses={404: {"model": ErrorOut, "description": "Patient, doctor or office not found."}, **_CONFLICT},
)
def agendar(payload: CitaCreate, db: DbSession) -> Cita:
    get_or_404(db, Paciente, payload.paciente_id, "Patient")
    get_or_404(db, Medico, payload.medico_id, "Doctor")
    get_or_404(db, Consultorio, payload.consultorio_id, "Office")
    _verificar_disponibilidad(db, payload.medico_id, payload.consultorio_id, payload.fecha_hora)
    cita = Cita(**payload.model_dump())
    db.add(cita)
    db.commit()
    return cita


@router.get("", response_model=list[CitaOut], summary="List appointments (a MEDICO only gets their own agenda)")
def listar(
    user: CurrentUser,
    db: DbSession,
    fecha: Annotated[date | None, Query()] = None,
    medico_id: Annotated[int | None, Query()] = None,
    estado: Annotated[EstadoCita | None, Query()] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[Cita]:
    query = select(Cita).order_by(Cita.fecha_hora)
    if user.rol == Rol.MEDICO:
        medico_id = user.medico_id
    if medico_id is not None:
        query = query.where(Cita.medico_id == medico_id)
    if fecha is not None:
        inicio_dia = datetime.combine(fecha, time.min)
        query = query.where(Cita.fecha_hora >= inicio_dia, Cita.fecha_hora < inicio_dia + timedelta(days=1))
    if estado is not None:
        query = query.where(Cita.estado == estado)
    return list(db.scalars(query.offset(skip).limit(limit)))


@router.get("/{cita_id}", response_model=CitaOut, summary="Get an appointment", responses=_NOT_FOUND)
def obtener(cita_id: int, user: CurrentUser, db: DbSession) -> Cita:
    return _cita_visible(db, cita_id, user)


@router.patch(
    "/{cita_id}/estado",
    response_model=CitaOut,
    summary="Confirm, start, finish or mark as no-show (MEDICO own, RECEPCION, ADMIN)",
    dependencies=[Depends(require_roles(Rol.MEDICO, Rol.RECEPCION, Rol.ADMIN))],
    responses={**_NOT_FOUND, **_CONFLICT},
)
def cambiar_estado(cita_id: int, payload: CambioEstadoIn, user: CurrentUser, db: DbSession) -> Cita:
    cita = _cita_visible(db, cita_id, user)
    _transicionar(cita, payload.estado)
    db.commit()
    return cita


@router.post(
    "/{cita_id}/cancelar",
    response_model=CitaOut,
    summary="Cancel with a reason (RECEPCION, ADMIN)",
    dependencies=[Agenda],
    responses={**_NOT_FOUND, **_CONFLICT},
)
def cancelar(cita_id: int, payload: CancelarCitaIn, user: CurrentUser, db: DbSession) -> Cita:
    cita = _cita_visible(db, cita_id, user)
    _transicionar(cita, EstadoCita.CANCELADA)
    cita.motivo_cancelacion = payload.motivo
    db.commit()
    return cita


@router.post(
    "/{cita_id}/reprogramar",
    response_model=CitaOut,
    summary="Move to a new date and time (RECEPCION, ADMIN)",
    dependencies=[Agenda],
    responses={**_NOT_FOUND, **_CONFLICT},
)
def reprogramar(cita_id: int, payload: ReprogramarCitaIn, user: CurrentUser, db: DbSession) -> Cita:
    cita = _cita_visible(db, cita_id, user)
    if not puede_reprogramar(cita.estado):
        raise HTTPException(status.HTTP_409_CONFLICT, f"An appointment in status {cita.estado} cannot be rescheduled.")
    _verificar_disponibilidad(db, cita.medico_id, cita.consultorio_id, payload.fecha_hora, excluir_id=cita.id)
    cita.fecha_hora = payload.fecha_hora
    cita.estado = EstadoCita.PROGRAMADA  # the new slot must be confirmed again
    db.commit()
    return cita
