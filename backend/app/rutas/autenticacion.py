from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from ..core.errores import ErrorSistema
from ..core.seguridad import ip_de, poner_cookie, quitar_cookie, usuario_sesion
from ..db.base import obtener_sesion
from ..db.modelos import Usuario
from ..esquemas import vistas
from ..esquemas.entradas import CambioClave, Credenciales
from ..servicios import autenticacion as servicio

r = APIRouter(prefix="/api/auth", tags=["sesión"])


@r.post("/login")
def login(c: Credenciales, request: Request, response: Response, bd: Session = Depends(obtener_sesion)):
    u = servicio.iniciar_sesion(bd, c.correo, c.clave, ip_de(request))
    poner_cookie(response, u)
    return vistas.usuario(u)


@r.post("/salir")
def salir(request: Request, response: Response, bd: Session = Depends(obtener_sesion)):
    try:
        servicio.cerrar_sesion(bd, usuario_sesion(request, bd))
    except ErrorSistema:
        pass
    quitar_cookie(response)
    return {"ok": True}


@r.get("/yo")
def yo(u: Usuario = Depends(usuario_sesion)):
    return vistas.usuario(u)


@r.post("/cambiar-clave")
def cambiar_clave(c: CambioClave, response: Response, u: Usuario = Depends(usuario_sesion),
                  bd: Session = Depends(obtener_sesion)):
    u = servicio.cambiar_clave(bd, u, c.clave_actual, c.clave_nueva)
    poner_cookie(response, u)
    return vistas.usuario(u)
