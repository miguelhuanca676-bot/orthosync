from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..core.seguridad import requiere
from ..db.base import obtener_sesion
from ..db.modelos import Usuario
from ..esquemas import vistas
from ..esquemas.entradas import PedidoEliminacion
from ..servicios import informes, portal
from .comun import archivo, sitio

r = APIRouter(prefix="/api/portal", tags=["portal del paciente"])
PACIENTE = requiere("paciente")


@r.post("/aceptar-terminos")
def aceptar_terminos(u: Usuario = Depends(requiere("paciente", terminos=False)), bd: Session = Depends(obtener_sesion)):
    return vistas.usuario(portal.aceptar_terminos(bd, u))


@r.get("/resumen")
def resumen(u: Usuario = Depends(PACIENTE), bd: Session = Depends(obtener_sesion)):
    return portal.resumen(bd, u)


@r.get("/estudios/{eid}/informe")
def informe(eid: str, request: Request, u: Usuario = Depends(PACIENTE), bd: Session = Depends(obtener_sesion)):
    pdf, nombre = informes.para_paciente(bd, u, eid, sitio(request))
    return archivo(pdf, nombre, "application/pdf")


@r.get("/mis-datos")
def mis_datos(u: Usuario = Depends(PACIENTE), bd: Session = Depends(obtener_sesion)):
    datos, nombre = portal.mis_datos(bd, u)
    return archivo(datos, nombre, "application/json")


@r.post("/solicitar-eliminacion", status_code=201)
def solicitar_eliminacion(d: PedidoEliminacion, u: Usuario = Depends(PACIENTE), bd: Session = Depends(obtener_sesion)):
    portal.solicitar_eliminacion(bd, u, d.motivo)
    return {"ok": True}
