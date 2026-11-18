"""Contraseñas, sesiones, permisos por rol y freno a la fuerza bruta.

La sesión viaja en una cookie httpOnly firmada: el navegador la envía sola y ningún código
de la página (ni la consola F12) puede leerla o cambiarla. El rol NUNCA se toma del navegador:
se lee de la base de datos en cada pedido.
"""
import hashlib, hmac, os, secrets, time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, Request, Response
from sqlalchemy.orm import Session

from . import config
from .errores import DatoInvalido, NoAutenticado, NoEncontrado, Prohibido
from ..db.base import obtener_sesion
from ..db.modelos import Usuario

COOKIE = "orthosync_sesion"
_ITERACIONES = 240_000


# ---------------------------------------------------------------- contraseñas
def cifrar_clave(clave: str) -> str:
    sal = os.urandom(16)
    h = hashlib.pbkdf2_hmac("sha256", clave.encode(), sal, _ITERACIONES)
    return f"pbkdf2${_ITERACIONES}${sal.hex()}${h.hex()}"


def verificar_clave(clave: str, guardada: str) -> bool:
    try:
        _, it, sal, h = guardada.split("$")
        nuevo = hashlib.pbkdf2_hmac("sha256", clave.encode(), bytes.fromhex(sal), int(it))
        return hmac.compare_digest(nuevo.hex(), h)
    except Exception:
        return False


_HASH_FICTICIO = cifrar_clave(secrets.token_hex(8))   # para tardar lo mismo aunque el correo no exista


def gastar_tiempo(clave: str):
    verificar_clave(clave, _HASH_FICTICIO)


def validar_politica(clave: str):
    if len(clave) < 8 or not any(c.isalpha() for c in clave) or not any(c.isdigit() for c in clave):
        raise DatoInvalido("La contraseña debe tener al menos 8 caracteres e incluir letras y números")


def clave_temporal() -> str:
    return secrets.token_urlsafe(8) + str(secrets.randbelow(10))


# ---------------------------------------------------------------- sesión (cookie firmada)
def crear_token(u: Usuario) -> str:
    vence = datetime.now(timezone.utc) + timedelta(hours=config.HORAS_SESION)
    return jwt.encode({"sub": str(u.id), "ver": u.version_sesion or 0, "exp": vence}, config.CLAVE_SECRETA, algorithm="HS256")


def poner_cookie(resp: Response, u: Usuario):
    resp.set_cookie(COOKIE, crear_token(u), max_age=config.HORAS_SESION * 3600, httponly=True,
                    secure=config.HTTPS, samesite="strict", path="/")


def quitar_cookie(resp: Response):
    resp.delete_cookie(COOKIE, path="/", httponly=True, secure=config.HTTPS, samesite="strict")


def _leer_token(request: Request) -> str | None:
    t = request.cookies.get(COOKIE)
    if t:
        return t
    cab = request.headers.get("authorization", "")       # para clientes de API y pruebas automáticas
    return cab[7:] if cab.lower().startswith("bearer ") else None


def usuario_sesion(request: Request, bd: Session = Depends(obtener_sesion)) -> Usuario:
    """Usuario de la sesión, aunque todavía deba cambiar su contraseña."""
    token = _leer_token(request)
    if not token:
        raise NoAutenticado("Debes iniciar sesión")
    try:
        datos = jwt.decode(token, config.CLAVE_SECRETA, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise NoAutenticado("La sesión no es válida o ya venció")
    u = bd.get(Usuario, int(datos.get("sub", 0)))
    if u is None or not u.activo or datos.get("ver") != (u.version_sesion or 0):
        raise NoAutenticado("La sesión ya no es válida")
    return u


def usuario_actual(u: Usuario = Depends(usuario_sesion)) -> Usuario:
    if u.debe_cambiar_clave:
        raise Prohibido("Debes cambiar tu contraseña antes de continuar")
    return u


def requiere(*roles: str, terminos: bool = True):
    """Solo deja pasar a los roles indicados. A cualquier otro le responde 'No encontrado',
    para no revelar siquiera que esa función existe."""
    def comprobar(u: Usuario = Depends(usuario_actual)) -> Usuario:
        if u.rol not in roles:
            raise NoEncontrado()
        if terminos and u.rol == "paciente" and not u.acepto_terminos_en:
            raise Prohibido("Debes aceptar los términos y la política de privacidad")
        return u
    return comprobar


# ---------------------------------------------------------------- freno a la fuerza bruta (por dirección IP)
_fallos_ip: dict[str, deque] = defaultdict(deque)
_VENTANA, _MAX_IP = 15 * 60, 20


def ip_de(request: Request) -> str:
    # Si el pedido llega por la función de Cloudflare Pages (trae el secreto compartido), la IP real
    # del visitante viene en X-Cliente-IP.
    if config.PROXY_SECRETO and hmac.compare_digest(request.headers.get("x-proxy-secreto", ""), config.PROXY_SECRETO):
        ip = request.headers.get("x-cliente-ip", "").strip()
        if ip:
            return ip[:64]
    # Detrás de un proxy propio (Caddy/Nginx) la IP real es la ÚLTIMA de X-Forwarded-For (la agrega el proxy).
    # Sin proxy se ignora esa cabecera, porque cualquiera podría inventarla.
    if config.PROXY:
        reenviada = [x.strip() for x in request.headers.get("x-forwarded-for", "").split(",") if x.strip()]
        if reenviada:
            return reenviada[-1][:64]
    return (request.client.host if request.client else "?")[:64]


def ip_bloqueada(ip: str) -> bool:
    q = _fallos_ip[ip]; limite = time.time() - _VENTANA
    while q and q[0] < limite:
        q.popleft()
    return len(q) >= _MAX_IP


def registrar_fallo_ip(ip: str):
    _fallos_ip[ip].append(time.time())
