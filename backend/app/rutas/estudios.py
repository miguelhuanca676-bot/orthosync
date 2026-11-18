from datetime import date

from fastapi import APIRouter, Depends, File, Form, Request, Response, UploadFile
from sqlalchemy.orm import Session

from ..core import config
from ..core.seguridad import requiere, usuario_actual
from ..db.base import obtener_sesion
from ..db.modelos import Usuario
from ..esquemas import vistas
from ..esquemas.entradas import PedidoInforme, Publicacion, Recorte, Valoracion
from ..servicios import estudios as servicio, informes
from .comun import archivo as descarga, sitio

r = APIRouter(prefix="/api", tags=["estudios"])
MEDICO = requiere("traumatologo")


@r.get("/pacientes/{pid}/estudios")
def listar(pid: str, u: Usuario = Depends(MEDICO), bd: Session = Depends(obtener_sesion)):
    return [vistas.estudio(e) for e in servicio.listar(bd, u, pid)]


@r.post("/pacientes/{pid}/estudios", status_code=201)
async def subir(pid: str, archivo: UploadFile = File(...), fecha_estudio: date | None = Form(None),
                u: Usuario = Depends(MEDICO), bd: Session = Depends(obtener_sesion)):
    datos = await archivo.read(config.TAM_MAX_ARCHIVO_MB * 1024 * 1024 + 1)
    return vistas.estudio(servicio.subir(bd, u, pid, archivo.filename, datos, fecha_estudio))


@r.get("/pacientes/{pid}/evolucion")
def evolucion(pid: str, _: Usuario = Depends(MEDICO), bd: Session = Depends(obtener_sesion)):
    return servicio.evolucion(bd, pid)


@r.get("/estudios/{eid}")
def ver(eid: str, u: Usuario = Depends(MEDICO), bd: Session = Depends(obtener_sesion)):
    return vistas.estudio(servicio.ver(bd, u, eid))


@r.post("/estudios/{eid}/analizar")
def reanalizar(eid: str, u: Usuario = Depends(MEDICO), bd: Session = Depends(obtener_sesion)):
    return vistas.estudio(servicio.reanalizar(bd, u, eid))


@r.post("/estudios/{eid}/recortar")
def recortar(eid: str, d: Recorte, u: Usuario = Depends(MEDICO), bd: Session = Depends(obtener_sesion)):
    return vistas.estudio(servicio.recortar(bd, u, eid, d.x1, d.y1, d.x2, d.y2))


@r.patch("/estudios/{eid}/valoracion")
def valorar(eid: str, d: Valoracion, u: Usuario = Depends(MEDICO), bd: Session = Depends(obtener_sesion)):
    return vistas.estudio(servicio.valorar(bd, u, eid, d.model_dump(exclude_unset=True)))


@r.post("/estudios/{eid}/publicar")
def publicar(eid: str, d: Publicacion, u: Usuario = Depends(MEDICO), bd: Session = Depends(obtener_sesion)):
    return vistas.estudio(servicio.publicar(bd, u, eid, d.publicado))


@r.delete("/estudios/{eid}", status_code=204)
def borrar(eid: str, u: Usuario = Depends(MEDICO), bd: Session = Depends(obtener_sesion)):
    servicio.borrar(bd, u, eid)


@r.post("/estudios/{eid}/informe")
def informe(eid: str, request: Request, pedido: PedidoInforme | None = None, u: Usuario = Depends(MEDICO),
            bd: Session = Depends(obtener_sesion)):
    pdf, nombre = informes.para_medico(bd, u, eid, sitio(request), pedido.imagen_3d if pedido else None)
    return descarga(pdf, nombre, "application/pdf")


@r.get("/estudios/{eid}/imagen/{tipo}")
def imagen(eid: str, tipo: str, u: Usuario = Depends(usuario_actual), bd: Session = Depends(obtener_sesion)):
    return Response(servicio.imagen(bd, u, eid, tipo), media_type="image/png",
                    headers={"Cache-Control": "private, no-store"})
