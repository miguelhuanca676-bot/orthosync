"""Consultas sobre pacientes."""
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..db.modelos import Paciente


def por_uid(bd: Session, uid: str) -> Paciente | None:
    return bd.scalar(select(Paciente).where(Paciente.uid == uid)) if uid else None


def por_id(bd: Session, pid: int) -> Paciente | None:
    return bd.get(Paciente, pid)


def codigo_usado(bd: Session, codigo: str) -> bool:
    return bd.scalar(select(Paciente).where(Paciente.codigo == codigo)) is not None


def contar(bd: Session) -> int:
    return bd.scalar(select(func.count(Paciente.id)))


def buscar(bd: Session, texto: str = "", limite: int = 200) -> list[Paciente]:
    q = select(Paciente).order_by(Paciente.apellidos, Paciente.nombres)
    b = texto.strip()[:60].lower().replace("%", "").replace("_", "")
    if b:
        t = f"%{b}%"
        q = q.where(or_(func.lower(Paciente.nombres).like(t), func.lower(Paciente.apellidos).like(t),
                        func.lower(Paciente.codigo).like(t), Paciente.documento.like(t)))
    return list(bd.scalars(q.limit(limite)))


def todos(bd: Session) -> list[Paciente]:
    return list(bd.scalars(select(Paciente)))
