"""Demo data: catalog, patients and one user per role.

Usage: set SEED_PASSWORD in .env (min. 12 characters) and run `python -m vitreo.seed`.
"""

import os
import sys
from datetime import date

from sqlalchemy import select

import vitreo.models  # noqa: F401
from vitreo.db import Base, SessionLocal, engine
from vitreo.models import Consultorio, Especialidad, Medico, Paciente, Rol, Usuario
from vitreo.security.passwords import hash_password

ESPECIALIDADES = ["Cardiología", "Pediatría", "Dermatología", "Traumatología", "Medicina general"]
MEDICOS = [
    ("Andrés", "Nieto", "Cardiología", "Mañana"),
    ("Valentina", "Ruiz", "Pediatría", "Mañana"),
    ("Manuela", "Ospina", "Dermatología", "Tarde"),
    ("Simón", "Duarte", "Traumatología", "Mañana"),
    ("Pablo", "Lozano", "Medicina general", "Noche"),
]
CONSULTORIOS = [("101", "Piso 1"), ("105", "Piso 1"), ("118", "Piso 1"), ("210", "Piso 2"), ("302", "Piso 3")]
PACIENTES = [
    ("1010101010", "Marcela", "Rincón", date(1958, 3, 14), "O+", "Penicilina"),
    ("1020202020", "Julián", "Torres", date(1992, 7, 2), "A-", None),
    ("1030303030", "Sara", "Franco", date(1985, 11, 23), "B+", "Mariscos"),
    ("1040404040", "Felipe", "Gómez", date(2015, 5, 9), "O-", None),
    ("1050505050", "Isabel", "Ortiz", date(1979, 1, 30), "AB+", "Polen, ibuprofeno"),
]


def main() -> None:
    password = os.getenv("SEED_PASSWORD", "")
    if len(password) < 12:
        sys.exit("Set SEED_PASSWORD (min. 12 characters) in .env before seeding.")

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if db.scalar(select(Usuario.id).limit(1)) is not None:
            sys.exit("The database already has users; nothing to do.")

        especialidades = {nombre: Especialidad(nombre=nombre) for nombre in ESPECIALIDADES}
        medicos = [Medico(nombres=n, apellidos=a, especialidad=especialidades[e], turno=t) for n, a, e, t in MEDICOS]
        db.add_all([*especialidades.values(), *medicos])
        db.add_all(Consultorio(numero=n, ubicacion=u) for n, u in CONSULTORIOS)
        db.add_all(
            Paciente(documento=d, nombres=n, apellidos=a, fecha_nacimiento=f, tipo_sangre=s, alergias=al)
            for d, n, a, f, s, al in PACIENTES
        )
        db.flush()

        password_hash = hash_password(password)
        db.add_all(
            [
                Usuario(nombre="Sebastian", correo="admin@vitreo.local", rol=Rol.ADMIN, contrasena_hash=password_hash),
                Usuario(
                    nombre="Andrés Nieto",
                    correo="anieto@vitreo.local",
                    rol=Rol.MEDICO,
                    medico_id=medicos[0].id,
                    contrasena_hash=password_hash,
                ),
                Usuario(
                    nombre="Elena Castaño",
                    correo="enfermeria@vitreo.local",
                    rol=Rol.ENFERMERIA,
                    contrasena_hash=password_hash,
                ),
                Usuario(
                    nombre="Recepción", correo="recepcion@vitreo.local", rol=Rol.RECEPCION, contrasena_hash=password_hash
                ),
            ]
        )
        db.commit()
    print("Demo data created: admin@, anieto@, enfermeria@ and recepcion@vitreo.local")


if __name__ == "__main__":
    main()
