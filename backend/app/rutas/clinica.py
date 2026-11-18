from datetime import date

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..core import config
from ..core.seguridad import ip_de, requiere
from ..db.base import obtener_sesion
from ..db.modelos import Usuario
from ..servicios import clinica, informes
from .comun import PERSONAL, archivo

r = APIRouter(prefix="/api", tags=["clínica"])


@r.api_route("/salud", methods=["GET", "HEAD"])
def salud():
    """Para el monitor (UptimeRobot): no toca la base de datos, así Neon puede dormir."""
    return {"sistema": config.NOMBRE_SISTEMA, "clinica": config.NOMBRE_CLINICA, "aviso": config.AVISO}


@r.get("/verificar/{codigo}")
def verificar(codigo: str, request: Request, bd: Session = Depends(obtener_sesion)):
    return informes.verificar(bd, codigo, ip_de(request))


@r.get("/controles")
def controles(u: Usuario = Depends(requiere(*PERSONAL)), bd: Session = Depends(obtener_sesion)):
    return clinica.controles(bd, u)


@r.get("/validacion")
def validacion(_: Usuario = Depends(requiere("administrador", "traumatologo")), bd: Session = Depends(obtener_sesion)):
    return clinica.validacion(bd)


@r.get("/correcciones/exportar")
def exportar(u: Usuario = Depends(requiere("traumatologo")), bd: Session = Depends(obtener_sesion)):
    return archivo(clinica.exportar_correcciones(bd, u), f"orthosync_casos_{date.today()}.zip", "application/zip")
