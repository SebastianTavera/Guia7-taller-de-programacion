"""Triage registration with automatic ESI classification and the prioritized ER queue (RF7-RF9)."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from vitreo.api.deps import DbSession, get_or_404, require_roles
from vitreo.domain.triage import SignosVitales, clasificar_esi, es_critico
from vitreo.models import Paciente, Rol, Triage
from vitreo.schemas import ErrorOut, TriageCreate, TriageOut

router = APIRouter(
    prefix="/api/v1/triage",
    tags=["Triage"],
    responses={
        401: {"model": ErrorOut, "description": "Missing or invalid token."},
        403: {"model": ErrorOut, "description": "Role not allowed."},
    },
)

alerts = logging.getLogger("vitreo.alerts")


@router.post(
    "",
    response_model=TriageOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a triage and classify its ESI level (ENFERMERIA, ADMIN)",
    dependencies=[Depends(require_roles(Rol.ENFERMERIA, Rol.ADMIN))],
    responses={404: {"model": ErrorOut, "description": "Patient not found."}},
)
def registrar_triage(payload: TriageCreate, db: DbSession) -> Triage:
    get_or_404(db, Paciente, payload.paciente_id, "Patient")
    vitales = SignosVitales(
        frecuencia_cardiaca=payload.frecuencia_cardiaca,
        frecuencia_respiratoria=payload.frecuencia_respiratoria,
        saturacion_oxigeno=payload.saturacion_oxigeno,
        presion_sistolica=payload.presion_sistolica,
        temperatura=payload.temperatura,
        dolor=payload.dolor,
    )
    triage = Triage(
        **payload.model_dump(),
        nivel_esi=clasificar_esi(vitales, payload.recursos_estimados, payload.alto_riesgo),
    )
    db.add(triage)
    db.commit()
    if es_critico(triage.nivel_esi):
        alerts.warning("critical_triage triage_id=%s esi=%s", triage.id, triage.nivel_esi)
    return triage


@router.get(
    "/cola",
    response_model=list[TriageOut],
    summary="ER queue: pending patients by ESI level, then arrival time",
    dependencies=[Depends(require_roles(Rol.ENFERMERIA, Rol.MEDICO, Rol.ADMIN))],
)
def cola_de_urgencias(db: DbSession) -> list[Triage]:
    query = select(Triage).where(Triage.atendido.is_(False)).order_by(Triage.nivel_esi, Triage.fecha_hora, Triage.id)
    return list(db.scalars(query))


@router.post(
    "/{triage_id}/atender",
    response_model=TriageOut,
    summary="Take a patient out of the queue (MEDICO, ENFERMERIA)",
    dependencies=[Depends(require_roles(Rol.MEDICO, Rol.ENFERMERIA))],
    responses={
        404: {"model": ErrorOut, "description": "Triage not found."},
        409: {"model": ErrorOut, "description": "Already attended."},
    },
)
def atender(triage_id: int, db: DbSession) -> Triage:
    triage = get_or_404(db, Triage, triage_id, "Triage")
    if triage.atendido:
        raise HTTPException(status.HTTP_409_CONFLICT, "This patient was already attended.")
    triage.atendido = True
    db.commit()
    return triage
