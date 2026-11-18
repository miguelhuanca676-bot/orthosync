"""Expedientes de pacientes (personal de la clínica) y su cuenta para el portal."""
import os, shutil

from sqlalchemy.orm import Session

from ..core import config
from ..core.errores import Conflicto, DatoInvalido, NoEncontrado
from ..core.seguridad import cifrar_clave, clave_temporal
from ..db.base import ahora
from ..db.modelos import Paciente, Usuario
from ..dominio.reglas import validar_datos_paciente
from ..esquemas import vistas
from ..repositorios import estudios, pacientes as repo, usuarios
from ..repositorios.registros import auditar, desvincular_usuario


def buscar(bd: Session, uid: str) -> Paciente:
    p = repo.por_uid(bd, uid)
    if p is None:
        raise NoEncontrado()
    return p


def vista(bd: Session, p: Paciente) -> dict:
    return vistas.paciente(p, usuarios.tiene_cuenta(bd, p.id))


def listar(bd: Session, actor: Usuario, texto: str) -> list[dict]:
    lista = repo.buscar(bd, texto)
    ids = [p.id for p in lista]
    # fecha y cantidad de estudios para todo el personal; lo clínico (por valorar) solo para el traumatólogo
    resumen = estudios.resumen_por_paciente(bd, ids)
    medico = actor.rol == "traumatologo"
    por_valorar = estudios.por_valorar_por_paciente(bd, ids) if medico else {}
    salida = []
    for p in lista:
        d = vistas.paciente(p); n, ult = resumen.get(p.id, (0, None))
        d.update(n_estudios=n, ultimo_estudio=ult)
        if medico:
            d["por_valorar"] = por_valorar.get(p.id, 0)
        salida.append(d)
    return salida


def crear(bd: Session, actor: Usuario, datos: dict, consentimiento: bool) -> Paciente:
    if not consentimiento:
        raise DatoInvalido("Falta el consentimiento informado firmado del paciente (o de su tutor)")
    validar_datos_paciente(datos["fecha_nacimiento"], datos.get("tutor_nombre"))
    p = Paciente(codigo="", creado_por=actor.id, consentimiento_en=ahora(), **datos)
    bd.add(p); bd.flush()
    p.codigo = f"P-{p.id:04d}"
    auditar(bd, actor, "crear_paciente", p.codigo, p.id); bd.commit()
    return p


def ver(bd: Session, actor: Usuario, uid: str) -> Paciente:
    p = buscar(bd, uid)
    auditar(bd, actor, "ver_paciente", p.codigo, p.id); bd.commit()
    return p


def cambiar(bd: Session, actor: Usuario, uid: str, datos: dict) -> Paciente:
    p = buscar(bd, uid)
    validar_datos_paciente(datos["fecha_nacimiento"], datos.get("tutor_nombre"))
    for k, v in datos.items():
        setattr(p, k, v)
    auditar(bd, actor, "cambiar_paciente", p.codigo, p.id); bd.commit()
    return p


def crear_cuenta(bd: Session, actor: Usuario, uid: str, correo: str) -> dict:
    """Crea el acceso al portal. La contraseña temporal se muestra una sola vez y debe cambiarse al entrar."""
    p = buscar(bd, uid)
    if usuarios.tiene_cuenta(bd, p.id):
        raise Conflicto("Este paciente ya tiene una cuenta")
    correo = correo.lower()
    if usuarios.por_correo(bd, correo):
        raise Conflicto("Ya existe un usuario con ese correo")
    clave = clave_temporal()
    bd.add(Usuario(nombre=f"{p.nombres} {p.apellidos}", correo=correo, rol="paciente", paciente_id=p.id,
                   clave_hash=cifrar_clave(clave), debe_cambiar_clave=True))
    auditar(bd, actor, "crear_cuenta_paciente", p.codigo, p.id); bd.commit()
    return {"correo": correo, "clave_temporal": clave}


def borrar_paciente(bd: Session, p: Paciente):
    """Elimina al paciente, sus estudios, sus radiografías y su cuenta del portal."""
    for u in usuarios.cuentas_de_paciente(bd, p.id):
        desvincular_usuario(bd, u.id)
        bd.delete(u)
    shutil.rmtree(os.path.join(config.DIR_ARCHIVOS, f"p{p.id}"), ignore_errors=True)
    bd.delete(p)
