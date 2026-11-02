"""Patients directory (RF1)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select

from vitreo.api.deps import CurrentUser, DbSession, get_or_404, require_roles
from vitreo.models import Paciente, Rol
from vitreo.schemas import ErrorOut, PacienteCreate, PacienteOut

router = APIRouter(
    prefix="/api/v1/pacientes",
    tags=["Pacientes"],
    responses={401: {"model": ErrorOut, "description": "Missing or invalid token."}},
)


@router.post(
    "",
    response_model=PacienteOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a patient (RECEPCION, ADMIN)",
    dependencies=[Depends(require_roles(Rol.RECEPCION, Rol.ADMIN))],
    responses={409: {"model": ErrorOut, "description": "Document already registered."}},
)
def crear_paciente(payload: PacienteCreate, db: DbSession) -> Paciente:
    if db.scalar(select(Paciente.id).where(Paciente.documento == payload.documento)) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "A patient with this document already exists.")
    paciente = Paciente(**payload.model_dump())
    db.add(paciente)
    db.commit()
    return paciente


@router.get("", response_model=list[PacienteOut], summary="List or search patients")
def listar_pacientes(
    _user: CurrentUser,
    db: DbSession,
    q: Annotated[str | None, Query(min_length=2, max_length=50, description="Name or document.")] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[Paciente]:
    query = select(Paciente).order_by(Paciente.apellidos, Paciente.nombres)
    if q:
        pattern = f"%{q}%"
        query = query.where(
            or_(Paciente.nombres.ilike(pattern), Paciente.apellidos.ilike(pattern), Paciente.documento.ilike(pattern))
        )
    return list(db.scalars(query.offset(skip).limit(limit)))


@router.get(
    "/{paciente_id}",
    response_model=PacienteOut,
    summary="Get a patient",
    responses={404: {"model": ErrorOut, "description": "Patient not found."}},
)
def obtener_paciente(paciente_id: int, _user: CurrentUser, db: DbSession) -> Paciente:
    return get_or_404(db, Paciente, paciente_id, "Patient")
