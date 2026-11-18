"""Crea las tablas y agrega columnas nuevas a bases de datos de versiones anteriores, sin perder datos."""
from sqlalchemy import inspect, select, text

from .base import Base, Sesion, motor, nuevo_uid
from .modelos import Estudio, Paciente


def _agregar_columnas_nuevas():
    """Agrega las columnas nuevas a una base de datos creada con una versión anterior (sin perder datos)."""
    insp = inspect(motor)
    with motor.begin() as cx:
        for tabla in Base.metadata.tables.values():
            if not insp.has_table(tabla.name):
                continue
            existentes = {c["name"] for c in insp.get_columns(tabla.name)}
            for col in tabla.columns:
                if col.name not in existentes:
                    cx.execute(text(f'ALTER TABLE {tabla.name} ADD COLUMN {col.name} {col.type.compile(dialect=motor.dialect)}'))
        cx.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_pacientes_uid ON pacientes (uid)"))
        cx.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_estudios_uid ON estudios (uid)"))
    with Sesion() as s:
        for modelo in (Paciente, Estudio):
            for o in s.scalars(select(modelo).where(modelo.uid.is_(None))):
                o.uid = nuevo_uid()
        s.commit()


def crear_tablas():
    Base.metadata.create_all(motor)
    _agregar_columnas_nuevas()
