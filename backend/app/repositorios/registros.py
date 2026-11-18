"""Auditoría, solicitudes de eliminación e informes emitidos."""
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from ..db.modelos import Auditoria, InformeEmitido, SolicitudEliminacion, Usuario


def auditar(bd: Session, usuario: Usuario | None, accion: str, detalle: str = "", paciente_id: int | None = None,
            ip: str | None = None):
    bd.add(Auditoria(usuario_id=usuario.id if usuario else None, accion=accion, detalle=(detalle or "")[:255],
                     paciente_id=paciente_id, ip=ip))


def ultimas_acciones(bd: Session, limite: int):
    return bd.execute(select(Auditoria, Usuario.nombre).outerjoin(Usuario, Usuario.id == Auditoria.usuario_id)
                      .order_by(Auditoria.id.desc()).limit(min(max(limite, 1), 1000))).all()


def solicitudes(bd: Session) -> list[SolicitudEliminacion]:
    return list(bd.scalars(select(SolicitudEliminacion).order_by(SolicitudEliminacion.estado != "pendiente",
                                                                 SolicitudEliminacion.id.desc())))


def solicitud(bd: Session, uid: str) -> SolicitudEliminacion | None:
    return bd.scalar(select(SolicitudEliminacion).where(SolicitudEliminacion.uid == uid))


def solicitud_pendiente_de(bd: Session, paciente_id: int) -> SolicitudEliminacion | None:
    return bd.scalar(select(SolicitudEliminacion).where(SolicitudEliminacion.paciente_id == paciente_id,
                                                        SolicitudEliminacion.estado == "pendiente"))


def solicitudes_pendientes(bd: Session) -> int:
    return bd.scalar(select(func.count(SolicitudEliminacion.id)).where(SolicitudEliminacion.estado == "pendiente"))


def informe(bd: Session, uid: str) -> InformeEmitido | None:
    return bd.scalar(select(InformeEmitido).where(InformeEmitido.uid == uid))


def ultima_solicitud_de(bd: Session, paciente_id: int) -> SolicitudEliminacion | None:
    return bd.scalar(select(SolicitudEliminacion).where(SolicitudEliminacion.paciente_id == paciente_id)
                     .order_by(SolicitudEliminacion.id.desc()))


def desvincular_usuario(bd: Session, usuario_id: int):
    """La auditoría se conserva, pero deja de apuntar a una cuenta que se elimina."""
    bd.execute(update(Auditoria).where(Auditoria.usuario_id == usuario_id).values(usuario_id=None))
