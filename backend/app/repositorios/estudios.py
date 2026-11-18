"""Consultas sobre estudios (radiografías y sus resultados)."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db.modelos import Estudio


def por_uid(bd: Session, uid: str) -> Estudio | None:
    return bd.scalar(select(Estudio).where(Estudio.uid == uid)) if uid else None


def contar(bd: Session, *condiciones) -> int:
    return bd.scalar(select(func.count(Estudio.id)).where(*condiciones))


def valorados_con_resultado(bd: Session) -> list[Estudio]:
    return list(bd.scalars(select(Estudio).where(Estudio.opinion.in_(("normal", "benigno", "maligno")),
                                                Estudio.estado_analisis == "listo")))


def contar_corregidos(bd: Session) -> int:
    return bd.scalar(select(func.count(Estudio.id)).where(Estudio.cajas_medico.is_not(None))) or 0


def resumen_por_paciente(bd: Session, ids: list[int]) -> dict[int, tuple[int, object]]:
    """{paciente_id: (cantidad de estudios, fecha del último)}"""
    if not ids:
        return {}
    return {pid: (n, ult) for pid, n, ult in bd.execute(
        select(Estudio.paciente_id, func.count(Estudio.id), func.max(Estudio.fecha_estudio))
        .where(Estudio.paciente_id.in_(ids)).group_by(Estudio.paciente_id))}


def por_valorar_por_paciente(bd: Session, ids: list[int]) -> dict[int, int]:
    if not ids:
        return {}
    return dict(bd.execute(select(Estudio.paciente_id, func.count(Estudio.id))
                           .where(Estudio.paciente_id.in_(ids), Estudio.opinion.is_(None))
                           .group_by(Estudio.paciente_id)).all())


def valorados(bd: Session) -> list[Estudio]:
    return list(bd.scalars(select(Estudio).where(Estudio.opinion.in_(("normal", "benigno", "maligno")))))
