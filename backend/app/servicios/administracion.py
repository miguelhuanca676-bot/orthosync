"""Panel del administrador: estadísticas, auditoría y solicitudes de eliminación de datos."""
from sqlalchemy.orm import Session

from ..core.errores import DatoInvalido, NoEncontrado
from ..db.base import ahora
from ..db.modelos import ROLES, Estudio, SolicitudEliminacion, Usuario
from ..integraciones import inferencia
from ..repositorios import estudios, pacientes, registros, usuarios
from .pacientes import borrar_paciente


def estadisticas(bd: Session) -> dict:
    por_rol = usuarios.activos_por_rol(bd)
    acuerdos = [e.sospechoso == (e.opinion != "normal") for e in estudios.valorados_con_resultado(bd)]
    return {
        "usuarios_por_rol": {r: por_rol.get(r, 0) for r in ROLES},
        "pacientes": pacientes.contar(bd),
        "estudios": estudios.contar(bd),
        "estudios_sospechosos": estudios.contar(bd, Estudio.sospechoso),
        "estudios_valorados": estudios.contar(bd, Estudio.opinion.is_not(None)),
        "acuerdo_sistema_medico": (sum(acuerdos) / len(acuerdos)) if acuerdos else None,
        "casos_para_acuerdo": len(acuerdos),
        "solicitudes_pendientes": registros.solicitudes_pendientes(bd),
        "modelos": inferencia.disponibles(),
    }


def auditoria(bd: Session, limite: int) -> list[dict]:
    return [{"fecha": a.fecha, "usuario": n, "accion": a.accion, "detalle": a.detalle, "ip": a.ip}
            for a, n in registros.ultimas_acciones(bd, limite)]


def solicitudes(bd: Session) -> list[dict]:
    return [{"id": s.uid, "codigo_paciente": s.codigo_paciente, "fecha": s.fecha, "motivo": s.motivo,
             "estado": s.estado, "respuesta": s.respuesta, "resuelta_en": s.resuelta_en}
            for s in registros.solicitudes(bd)]


def _pendiente(bd: Session, uid: str) -> SolicitudEliminacion:
    s = registros.solicitud(bd, uid)
    if s is None:
        raise NoEncontrado()
    if s.estado != "pendiente":
        raise DatoInvalido("Esta solicitud ya fue resuelta")
    return s


def ejecutar_solicitud(bd: Session, admin: Usuario, uid: str):
    s = _pendiente(bd, uid)
    p = pacientes.por_id(bd, s.paciente_id) if s.paciente_id else None
    if p is not None:
        borrar_paciente(bd, p)
    s.estado, s.resuelta_por, s.resuelta_en, s.paciente_id = "completada", admin.id, ahora(), None
    s.respuesta = "Datos eliminados"
    registros.auditar(bd, admin, "eliminar_datos_paciente", s.codigo_paciente); bd.commit()


def rechazar_solicitud(bd: Session, admin: Usuario, uid: str, respuesta: str):
    s = _pendiente(bd, uid)
    s.estado, s.respuesta, s.resuelta_por, s.resuelta_en = "rechazada", respuesta, admin.id, ahora()
    registros.auditar(bd, admin, "rechazar_eliminacion", s.codigo_paciente); bd.commit()
