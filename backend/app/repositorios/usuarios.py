"""Consultas a la base de datos sobre usuarios. Solo leen/escriben: las reglas están en servicios/."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db.modelos import Usuario


def por_id(bd: Session, uid: int) -> Usuario | None:
    return bd.get(Usuario, uid)


def por_correo(bd: Session, correo: str) -> Usuario | None:
    return bd.scalar(select(Usuario).where(Usuario.correo == correo.strip().lower()))


def todos(bd: Session) -> list[Usuario]:
    return list(bd.scalars(select(Usuario).order_by(Usuario.rol, Usuario.nombre)))


def administradores(bd: Session) -> list[Usuario]:
    return list(bd.scalars(select(Usuario).where(Usuario.rol == "administrador")))


def cuentas_de_paciente(bd: Session, paciente_id: int) -> list[Usuario]:
    return list(bd.scalars(select(Usuario).where(Usuario.paciente_id == paciente_id)))


def tiene_cuenta(bd: Session, paciente_id: int) -> bool:
    return bd.scalar(select(func.count(Usuario.id)).where(Usuario.paciente_id == paciente_id)) > 0


def activos_por_rol(bd: Session) -> dict[str, int]:
    return dict(bd.execute(select(Usuario.rol, func.count()).where(Usuario.activo).group_by(Usuario.rol)).all())
