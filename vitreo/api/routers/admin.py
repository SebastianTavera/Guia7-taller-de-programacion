"""ADMIN-only endpoints: user management and management reports."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from vitreo.api.deps import DbSession, get_or_404, require_roles
from vitreo.models import Cita, Medico, Paciente, Rol, Triage, Usuario
from vitreo.schemas import ErrorOut, ReporteOut, UsuarioCreate, UsuarioOut
from vitreo.security.passwords import hash_password

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["Admin"],
    dependencies=[Depends(require_roles(Rol.ADMIN))],
    responses={
        401: {"model": ErrorOut, "description": "Missing or invalid token."},
        403: {"model": ErrorOut, "description": "Only ADMIN users can access this resource."},
    },
)


@router.post("/usuarios", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED, summary="Create a user")
def crear_usuario(payload: UsuarioCreate, db: DbSession) -> Usuario:
    correo = payload.correo.lower()
    if db.scalar(select(Usuario.id).where(Usuario.correo == correo)) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "A user with this email already exists.")
    if payload.medico_id is not None:
        get_or_404(db, Medico, payload.medico_id, "Doctor")
    user = Usuario(
        nombre=payload.nombre,
        correo=correo,
        contrasena_hash=hash_password(payload.password),
        rol=payload.rol,
        medico_id=payload.medico_id,
    )
    db.add(user)
    db.commit()
    return user


@router.get("/usuarios", response_model=list[UsuarioOut], summary="List users")
def listar_usuarios(
    db: DbSession,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[Usuario]:
    return list(db.scalars(select(Usuario).order_by(Usuario.id).offset(skip).limit(limit)))


@router.get("/reportes", response_model=ReporteOut, summary="Appointments by status and triage by ESI level")
def reportes(db: DbSession) -> ReporteOut:
    citas = db.execute(select(Cita.estado, func.count()).group_by(Cita.estado)).all()
    triages = db.execute(select(Triage.nivel_esi, func.count()).group_by(Triage.nivel_esi)).all()
    return ReporteOut(
        citas_por_estado={estado: total for estado, total in citas},
        triage_por_nivel={nivel: total for nivel, total in triages},
        pacientes_registrados=db.scalar(select(func.count()).select_from(Paciente)) or 0,
    )
