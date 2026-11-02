"""Doctors by specialty (RF14)."""

from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import select

from vitreo.api.deps import CurrentUser, DbSession
from vitreo.models import Medico
from vitreo.schemas import ErrorOut, MedicoOut

router = APIRouter(
    prefix="/api/v1/medicos",
    tags=["Medicos"],
    responses={401: {"model": ErrorOut, "description": "Missing or invalid token."}},
)


@router.get("", response_model=list[MedicoOut], summary="List doctors, optionally by specialty")
def listar_medicos(
    _user: CurrentUser, db: DbSession, especialidad_id: Annotated[int | None, Query()] = None
) -> list[Medico]:
    query = select(Medico).order_by(Medico.apellidos)
    if especialidad_id is not None:
        query = query.where(Medico.especialidad_id == especialidad_id)
    return list(db.scalars(query))
