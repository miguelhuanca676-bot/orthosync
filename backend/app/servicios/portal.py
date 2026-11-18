"""Portal del paciente: ve lo que su médico publicó, descarga sus datos y puede pedir que se borren."""
import json

from sqlalchemy.orm import Session

from ..core.errores import Conflicto, NoEncontrado
from ..db.base import ahora
from ..db.modelos import Paciente, SolicitudEliminacion, Usuario
from ..esquemas import vistas
from ..repositorios import pacientes, registros, usuarios


def _paciente(bd: Session, u: Usuario) -> Paciente:
    p = pacientes.por_id(bd, u.paciente_id) if u.paciente_id else None
    if p is None:
        raise NoEncontrado()
    return p


def aceptar_terminos(bd: Session, u: Usuario) -> Usuario:
    u = usuarios.por_id(bd, u.id)
    u.acepto_terminos_en = ahora()
    registros.auditar(bd, u, "aceptar_terminos", paciente_id=u.paciente_id); bd.commit()
    return u


def resumen(bd: Session, u: Usuario) -> dict:
    p = _paciente(bd, u)
    publicados = [e for e in p.estudios if e.publicado]
    sol = registros.ultima_solicitud_de(bd, p.id)
    registros.auditar(bd, u, "portal_paciente", p.codigo, p.id); bd.commit()
    ultimo = max(publicados, key=lambda e: (e.fecha_estudio, e.id), default=None)
    return {"paciente": {"codigo": p.codigo, "nombres": p.nombres, "apellidos": p.apellidos},
            "estudios": [vistas.estudio_para_paciente(e) for e in publicados],
            "proximo_control": ultimo.proximo_control if ultimo else None,
            "solicitud_eliminacion": None if sol is None else {"estado": sol.estado, "fecha": sol.fecha,
                                                                "respuesta": sol.respuesta},
            "aviso": "Esta información fue revisada por tu médico. Ante cualquier duda, consúltalo en tu próxima cita."}


def mis_datos(bd: Session, u: Usuario) -> tuple[bytes, str]:
    """Derecho de acceso: el paciente descarga todos sus datos personales en un archivo."""
    p = _paciente(bd, u)
    datos = {
        "generado": str(ahora()) + " UTC",
        "cuenta": {"correo": u.correo, "creada": str(u.creado), "terminos_aceptados": str(u.acepto_terminos_en)},
        "datos_personales": {"codigo": p.codigo, "nombres": p.nombres, "apellidos": p.apellidos,
                             "documento": p.documento, "fecha_nacimiento": str(p.fecha_nacimiento), "sexo": p.sexo,
                             "telefono": p.telefono, "tutor": p.tutor_nombre, "documento_tutor": p.tutor_documento,
                             "consentimiento_registrado": str(p.consentimiento_en)},
        "estudios_publicados_por_tu_medico": [{**vistas.estudio_para_paciente(e), "fecha_estudio": str(e.fecha_estudio),
                                               "proximo_control": str(e.proximo_control) if e.proximo_control else None}
                                              for e in p.estudios if e.publicado],
        "estudios_en_revision": sum(1 for e in p.estudios if not e.publicado),
        "nota": "Los estudios en revisión aparecerán cuando tu médico los valide. Las radiografías se pueden "
                "descargar desde el portal.",
    }
    registros.auditar(bd, u, "exportar_datos", p.codigo, p.id); bd.commit()
    return json.dumps(datos, ensure_ascii=False, indent=2, default=str).encode(), f"mis_datos_{p.codigo}.json"


def solicitar_eliminacion(bd: Session, u: Usuario, motivo: str | None):
    p = _paciente(bd, u)
    if registros.solicitud_pendiente_de(bd, p.id):
        raise Conflicto("Ya tienes una solicitud pendiente")
    bd.add(SolicitudEliminacion(paciente_id=p.id, codigo_paciente=p.codigo, motivo=motivo))
    registros.auditar(bd, u, "solicitar_eliminacion", p.codigo, p.id); bd.commit()
