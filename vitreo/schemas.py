"""Pydantic v2 schemas. Inputs forbid unknown fields (no mass assignment); outputs never expose secrets."""

from datetime import date, datetime
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, computed_field, model_validator

from vitreo.domain.citas import EstadoCita
from vitreo.domain.triage import es_critico
from vitreo.models import Rol

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
PHONE_PATTERN = r"^\+?[0-9 ]{7,20}$"

TipoSangre = Literal["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"]


def _to_naive_local(value: datetime) -> datetime:
    return value.astimezone().replace(tzinfo=None) if value.tzinfo else value


def _in_future(value: datetime) -> datetime:
    if value <= datetime.now():
        raise ValueError("must be in the future")
    return value


def _in_past(value: date) -> date:
    if value >= date.today():
        raise ValueError("must be in the past")
    return value


FutureDateTime = Annotated[datetime, AfterValidator(_to_naive_local), AfterValidator(_in_future)]
PastDate = Annotated[date, AfterValidator(_in_past)]
Email = Annotated[str, Field(max_length=120, pattern=EMAIL_PATTERN)]


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OutputModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Auth & users ----------

class LoginIn(InputModel):
    correo: Email
    # The upper bound avoids hashing arbitrarily large inputs.
    password: str = Field(min_length=1, max_length=128)


class TokenOut(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(description="Seconds until the token expires.")


class UsuarioCreate(InputModel):
    nombre: str = Field(min_length=2, max_length=100)
    correo: Email
    password: str = Field(min_length=12, max_length=128)
    rol: Rol
    medico_id: int | None = None

    @model_validator(mode="after")
    def _medico_vinculado(self) -> "UsuarioCreate":
        if (self.rol == Rol.MEDICO) != (self.medico_id is not None):
            raise ValueError("medico_id is required for MEDICO users and not allowed for other roles")
        return self


class UsuarioOut(OutputModel):
    id: int
    nombre: str
    correo: str
    rol: Rol
    activo: bool
    medico_id: int | None


# ---------- Patients & doctors ----------

class PacienteCreate(InputModel):
    documento: str = Field(min_length=5, max_length=20, pattern=r"^[0-9A-Za-z-]+$")
    nombres: str = Field(min_length=2, max_length=80)
    apellidos: str = Field(min_length=2, max_length=80)
    fecha_nacimiento: PastDate
    tipo_sangre: TipoSangre
    alergias: str | None = Field(default=None, max_length=255)
    telefono: str | None = Field(default=None, pattern=PHONE_PATTERN)


class PacienteOut(OutputModel):
    id: int
    documento: str
    nombres: str
    apellidos: str
    fecha_nacimiento: date
    tipo_sangre: str
    alergias: str | None
    telefono: str | None


class MedicoOut(OutputModel):
    id: int
    nombres: str
    apellidos: str
    especialidad: str = Field(validation_alias="especialidad_nombre")
    turno: str


# ---------- Triage ----------

class TriageCreate(InputModel):
    paciente_id: int
    sintomas: str = Field(min_length=3, max_length=1000)
    frecuencia_cardiaca: int = Field(ge=0, le=300, description="Beats per minute.")
    frecuencia_respiratoria: int = Field(ge=0, le=80, description="Breaths per minute.")
    saturacion_oxigeno: int = Field(ge=0, le=100, description="SpO2 %.")
    presion_sistolica: int = Field(ge=0, le=300, description="Systolic blood pressure, mmHg.")
    temperatura: float = Field(ge=25, le=45, description="°C.")
    dolor: int = Field(ge=0, le=10, description="Pain scale 0-10.")
    recursos_estimados: int = Field(ge=0, le=10, description="Expected resources (labs, imaging, IV...).")
    alto_riesgo: bool = Field(default=False, description="Nurse judgment: high-risk situation.")


class TriageOut(OutputModel):
    id: int
    paciente_id: int
    sintomas: str
    frecuencia_cardiaca: int
    frecuencia_respiratoria: int
    saturacion_oxigeno: int
    presion_sistolica: int
    temperatura: float
    dolor: int
    recursos_estimados: int
    alto_riesgo: bool
    nivel_esi: int
    fecha_hora: datetime
    atendido: bool

    @computed_field
    @property
    def critico(self) -> bool:
        return es_critico(self.nivel_esi)


# ---------- Appointments ----------

class CitaCreate(InputModel):
    paciente_id: int
    medico_id: int
    consultorio_id: int
    fecha_hora: FutureDateTime


class CitaOut(OutputModel):
    id: int
    paciente_id: int
    medico_id: int
    consultorio_id: int
    fecha_hora: datetime
    estado: EstadoCita
    motivo_cancelacion: str | None


class CambioEstadoIn(InputModel):
    # Cancelling requires a reason, so it has its own endpoint.
    estado: Literal[EstadoCita.CONFIRMADA, EstadoCita.EN_CURSO, EstadoCita.ATENDIDA, EstadoCita.NO_ASISTIO]


class CancelarCitaIn(InputModel):
    motivo: str = Field(min_length=5, max_length=255)


class ReprogramarCitaIn(InputModel):
    fecha_hora: FutureDateTime


# ---------- Reports & errors ----------

class ReporteOut(BaseModel):
    citas_por_estado: dict[str, int]
    triage_por_nivel: dict[int, int]
    pacientes_registrados: int


class ErrorOut(BaseModel):
    error: str = Field(description="Short HTTP error name.")
    detail: Any = Field(description="Human-readable message or list of validation problems.")
    status: int = Field(description="HTTP status code.")
