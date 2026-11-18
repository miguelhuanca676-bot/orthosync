"""Cuentas del personal de la clínica (las gestiona el administrador)."""
from sqlalchemy.orm import Session

from ..core.errores import Conflicto, DatoInvalido, NoEncontrado
from ..core.seguridad import cifrar_clave, validar_politica
from ..db.modelos import Usuario
from ..dominio.reglas import PERSONAL
from ..repositorios import usuarios as repo
from ..repositorios.registros import auditar


def listar(bd: Session) -> list[Usuario]:
    return repo.todos(bd)


def crear(bd: Session, admin: Usuario, nombre: str, correo: str, rol: str, clave: str) -> Usuario:
    if rol not in PERSONAL:
        raise DatoInvalido("Rol no válido. Las cuentas de paciente se crean desde su expediente.")
    validar_politica(clave)
    correo = correo.lower()
    if repo.por_correo(bd, correo):
        raise Conflicto("Ya existe un usuario con ese correo")
    u = Usuario(nombre=nombre.strip(), correo=correo, rol=rol, clave_hash=cifrar_clave(clave), debe_cambiar_clave=True)
    bd.add(u); auditar(bd, admin, "crear_usuario", f"{correo} ({rol})"); bd.commit()
    return u


def cambiar(bd: Session, admin: Usuario, uid: int, nombre=None, rol=None, activo=None, clave=None) -> Usuario:
    u = repo.por_id(bd, uid)
    if u is None:
        raise NoEncontrado()
    if u.id == admin.id and (activo is False or (rol and rol != "administrador")):
        raise DatoInvalido("No puedes desactivarte ni quitarte el rol de administrador")
    if rol is not None:
        if rol not in PERSONAL or u.rol == "paciente":
            raise DatoInvalido("Rol no válido")
        u.rol = rol; u.version_sesion = (u.version_sesion or 0) + 1
    if nombre is not None:
        u.nombre = nombre.strip()
    if activo is not None:
        u.activo = activo; u.version_sesion = (u.version_sesion or 0) + 1
        if activo:
            u.bloqueado_hasta = None; u.intentos_fallidos = 0
    if clave is not None:
        validar_politica(clave)
        u.clave_hash = cifrar_clave(clave); u.debe_cambiar_clave = True; u.version_sesion = (u.version_sesion or 0) + 1
    auditar(bd, admin, "cambiar_usuario", u.correo); bd.commit()
    return u
