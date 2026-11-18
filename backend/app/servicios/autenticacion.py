"""Inicio y cierre de sesión, cambio de contraseña y el primer administrador."""
from datetime import timedelta

from sqlalchemy.orm import Session

from ..core import config
from ..core.errores import DatoInvalido, DemasiadosIntentos, NoAutenticado
from ..core.seguridad import (cifrar_clave, gastar_tiempo, ip_bloqueada, registrar_fallo_ip, validar_politica,
                              verificar_clave)
from ..db.base import ahora
from ..db.modelos import Usuario
from ..repositorios import usuarios as repo
from ..repositorios.registros import auditar

CREDENCIALES_INVALIDAS = ("Correo o contraseña incorrectos. Tras varios intentos fallidos la cuenta se bloquea "
                          f"{config.MINUTOS_BLOQUEO} minutos.")


def preparar_administrador(bd: Session):
    """Crea el primer administrador si no hay ninguno. Si alguno sigue con la contraseña inicial, debe cambiarla."""
    admins = repo.administradores(bd)
    if not admins:
        bd.add(Usuario(nombre="Administrador", correo=config.ADMIN_CORREO, rol="administrador",
                       clave_hash=cifrar_clave(config.ADMIN_CLAVE), debe_cambiar_clave=True))
    for u in admins:
        if verificar_clave(config.ADMIN_CLAVE, u.clave_hash):
            u.debe_cambiar_clave = True
    bd.commit()


def iniciar_sesion(bd: Session, correo: str, clave: str, ip: str) -> Usuario:
    if ip_bloqueada(ip):
        raise DemasiadosIntentos("Demasiados intentos desde esta conexión. Espera unos minutos.")
    u = repo.por_correo(bd, correo)
    bloqueado = u is not None and u.bloqueado_hasta is not None and u.bloqueado_hasta > ahora()
    if u is None:
        gastar_tiempo(clave)          # tarda lo mismo exista o no el correo
    ok = u is not None and not bloqueado and u.activo and verificar_clave(clave, u.clave_hash)
    if not ok:
        registrar_fallo_ip(ip)
        if u is not None and not bloqueado:
            u.intentos_fallidos = (u.intentos_fallidos or 0) + 1
            if u.intentos_fallidos >= config.INTENTOS_MAXIMOS:
                u.bloqueado_hasta = ahora() + timedelta(minutes=config.MINUTOS_BLOQUEO); u.intentos_fallidos = 0
                auditar(bd, u, "cuenta_bloqueada", f"{config.INTENTOS_MAXIMOS} intentos fallidos", ip=ip)
        auditar(bd, None, "login_fallido", correo[:80], ip=ip); bd.commit()
        raise NoAutenticado(CREDENCIALES_INVALIDAS)
    u.intentos_fallidos = 0; u.bloqueado_hasta = None
    auditar(bd, u, "login", ip=ip); bd.commit()
    return u


def cerrar_sesion(bd: Session, u: Usuario):
    u.version_sesion = (u.version_sesion or 0) + 1      # invalida la sesión en todos los dispositivos
    auditar(bd, u, "logout"); bd.commit()


def cambiar_clave(bd: Session, u: Usuario, actual: str, nueva: str) -> Usuario:
    u = repo.por_id(bd, u.id)
    if not verificar_clave(actual, u.clave_hash):
        raise DatoInvalido("La contraseña actual no es correcta")
    validar_politica(nueva)
    if nueva == actual:
        raise DatoInvalido("La contraseña nueva debe ser distinta de la actual")
    u.clave_hash = cifrar_clave(nueva); u.debe_cambiar_clave = False
    u.version_sesion = (u.version_sesion or 0) + 1        # cierra las demás sesiones abiertas
    auditar(bd, u, "cambio_clave"); bd.commit()
    return u
