"""Informes PDF con código QR y verificación pública de su autenticidad."""
import base64, hashlib, io

from PIL import Image
from sqlalchemy.orm import Session

from ..core import config
from ..core.errores import DemasiadosIntentos, NoEncontrado
from ..core.seguridad import ip_bloqueada, registrar_fallo_ip
from ..db.base import nuevo_uid
from ..db.modelos import Estudio, InformeEmitido, Usuario
from ..integraciones.pdf import informe_medico, informe_paciente
from ..repositorios import registros, usuarios
from .estudios import buscar, carpeta


def _registro(e: Estudio, tipo: str) -> InformeEmitido:
    return InformeEmitido(uid=nuevo_uid(), estudio_id=e.id, codigo_paciente=e.paciente.codigo,
                          fecha_estudio=e.fecha_estudio, tipo=tipo)


def _verificacion(sitio: str, reg: InformeEmitido) -> tuple[str, str]:
    """Dirección del código QR. El código va después de '#', así no queda en registros de servidores."""
    return f"{config.SITIO or sitio}/verificar.html#{reg.uid}", reg.uid


def _imagen_3d(dato: str | None) -> Image.Image | None:
    if not dato or not dato.startswith("data:image/png;base64,"):
        return None
    try:
        crudo = base64.b64decode(dato.split(",", 1)[1], validate=True)
        if len(crudo) >= 15 * 1024 * 1024:
            return None
        img = Image.open(io.BytesIO(crudo)); img.load()
        return None if img.width * img.height > 20_000_000 else img
    except Exception:
        return None


def para_medico(bd: Session, actor: Usuario, eid: str, sitio: str, imagen_3d: str | None) -> tuple[bytes, str]:
    e = buscar(bd, eid)
    reg = _registro(e, "medico")
    pdf = informe_medico(e, e.paciente, usuarios.por_id(bd, e.medico_id), carpeta(e), _imagen_3d(imagen_3d),
                         _verificacion(sitio, reg))
    reg.huella = hashlib.sha256(pdf).hexdigest(); bd.add(reg)
    registros.auditar(bd, actor, "informe_estudio", e.paciente.codigo, e.paciente_id); bd.commit()
    return pdf, f"informe_{e.paciente.codigo}_{e.fecha_estudio}.pdf"


def para_paciente(bd: Session, actor: Usuario, eid: str, sitio: str) -> tuple[bytes, str]:
    e = buscar(bd, eid)
    if e.paciente_id != actor.paciente_id or not e.publicado:
        raise NoEncontrado()
    reg = _registro(e, "paciente")
    pdf = informe_paciente(e, e.paciente, carpeta(e), _verificacion(sitio, reg))
    reg.huella = hashlib.sha256(pdf).hexdigest(); bd.add(reg)
    registros.auditar(bd, actor, "informe_portal", e.paciente.codigo, e.paciente_id); bd.commit()
    return pdf, f"mi_estudio_{e.fecha_estudio}.pdf"


def verificar(bd: Session, codigo: str, ip: str) -> dict:
    """Público: confirma que un informe fue emitido por Orthosync. No devuelve datos personales."""
    if ip_bloqueada(ip):
        raise DemasiadosIntentos()
    r = registros.informe(bd, codigo[:40]) if codigo else None
    if r is None:
        registrar_fallo_ip(ip)
        raise NoEncontrado("No existe un informe con ese código")
    return {"valido": True, "tipo": "Informe para el médico" if r.tipo == "medico" else "Resumen para el paciente",
            "emitido_en": r.emitido_en, "expediente": r.codigo_paciente, "fecha_estudio": r.fecha_estudio,
            "huella": r.huella, "sistema": config.NOMBRE_SISTEMA, "clinica": config.NOMBRE_CLINICA}
