"""ORM models (first iteration of the Vitreo ER model)."""

from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import Boolean, Date, DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vitreo.db import Base
from vitreo.domain.citas import EstadoCita


class Rol(StrEnum):
    ADMIN = "ADMIN"
    MEDICO = "MEDICO"
    ENFERMERIA = "ENFERMERIA"
    RECEPCION = "RECEPCION"


class Especialidad(Base):
    __tablename__ = "especialidades"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80), unique=True)


class Medico(Base):
    __tablename__ = "medicos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombres: Mapped[str] = mapped_column(String(80))
    apellidos: Mapped[str] = mapped_column(String(80))
    especialidad_id: Mapped[int] = mapped_column(ForeignKey("especialidades.id"), index=True)
    turno: Mapped[str] = mapped_column(String(20))

    especialidad: Mapped[Especialidad] = relationship(lazy="joined")

    @property
    def especialidad_nombre(self) -> str:
        return self.especialidad.nombre


class Consultorio(Base):
    __tablename__ = "consultorios"

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[str] = mapped_column(String(10), unique=True)
    ubicacion: Mapped[str] = mapped_column(String(100))


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    correo: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    contrasena_hash: Mapped[str] = mapped_column(String(255))
    rol: Mapped[Rol] = mapped_column(Enum(Rol, native_enum=False, length=20))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    # Links a MEDICO user to their doctor record (object-level authorization).
    medico_id: Mapped[int | None] = mapped_column(ForeignKey("medicos.id"), default=None)


class Paciente(Base):
    __tablename__ = "pacientes"

    id: Mapped[int] = mapped_column(primary_key=True)
    documento: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    nombres: Mapped[str] = mapped_column(String(80))
    apellidos: Mapped[str] = mapped_column(String(80))
    fecha_nacimiento: Mapped[date] = mapped_column(Date)
    tipo_sangre: Mapped[str] = mapped_column(String(3))
    alergias: Mapped[str | None] = mapped_column(String(255), default=None)
    telefono: Mapped[str | None] = mapped_column(String(20), default=None)


class Cita(Base):
    __tablename__ = "citas"

    id: Mapped[int] = mapped_column(primary_key=True)
    paciente_id: Mapped[int] = mapped_column(ForeignKey("pacientes.id"), index=True)
    medico_id: Mapped[int] = mapped_column(ForeignKey("medicos.id"), index=True)
    consultorio_id: Mapped[int] = mapped_column(ForeignKey("consultorios.id"))
    fecha_hora: Mapped[datetime] = mapped_column(DateTime, index=True)
    estado: Mapped[EstadoCita] = mapped_column(
        Enum(EstadoCita, native_enum=False, length=20), default=EstadoCita.PROGRAMADA
    )
    motivo_cancelacion: Mapped[str | None] = mapped_column(String(255), default=None)


class Triage(Base):
    __tablename__ = "triages"

    id: Mapped[int] = mapped_column(primary_key=True)
    paciente_id: Mapped[int] = mapped_column(ForeignKey("pacientes.id"), index=True)
    sintomas: Mapped[str] = mapped_column(Text)
    frecuencia_cardiaca: Mapped[int]
    frecuencia_respiratoria: Mapped[int]
    saturacion_oxigeno: Mapped[int]
    presion_sistolica: Mapped[int]
    temperatura: Mapped[float] = mapped_column(Float)
    dolor: Mapped[int]
    recursos_estimados: Mapped[int]
    alto_riesgo: Mapped[bool] = mapped_column(Boolean, default=False)
    nivel_esi: Mapped[int] = mapped_column(index=True)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    atendido: Mapped[bool] = mapped_column(Boolean, default=False)
