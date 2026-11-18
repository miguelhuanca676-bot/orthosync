from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..core.seguridad import requiere
from ..db.base import obtener_sesion
from ..db.modelos import Usuario
from ..esquemas import vistas
from ..esquemas.entradas import Respuesta, UsuarioCambio, UsuarioNuevo
from ..servicios import administracion, usuarios

r = APIRouter(prefix="/api", tags=["administrador"])
ADMIN = requiere("administrador")


@r.get("/usuarios")
def listar_usuarios(_: Usuario = Depends(ADMIN), bd: Session = Depends(obtener_sesion)):
    return [vistas.usuario(u) for u in usuarios.listar(bd)]


@r.post("/usuarios", status_code=201)
def crear_usuario(d: UsuarioNuevo, yo: Usuario = Depends(ADMIN), bd: Session = Depends(obtener_sesion)):
    return vistas.usuario(usuarios.crear(bd, yo, d.nombre, d.correo, d.rol, d.clave))


@r.patch("/usuarios/{uid}")
def cambiar_usuario(uid: int, d: UsuarioCambio, yo: Usuario = Depends(ADMIN), bd: Session = Depends(obtener_sesion)):
    return vistas.usuario(usuarios.cambiar(bd, yo, uid, **d.model_dump()))


@r.get("/admin/estadisticas")
def estadisticas(_: Usuario = Depends(ADMIN), bd: Session = Depends(obtener_sesion)):
    return administracion.estadisticas(bd)


@r.get("/admin/auditoria")
def auditoria(limite: int = 200, _: Usuario = Depends(ADMIN), bd: Session = Depends(obtener_sesion)):
    return administracion.auditoria(bd, limite)


@r.get("/admin/solicitudes")
def solicitudes(_: Usuario = Depends(ADMIN), bd: Session = Depends(obtener_sesion)):
    return administracion.solicitudes(bd)


@r.post("/admin/solicitudes/{uid}/ejecutar")
def ejecutar(uid: str, yo: Usuario = Depends(ADMIN), bd: Session = Depends(obtener_sesion)):
    administracion.ejecutar_solicitud(bd, yo, uid)
    return {"ok": True}


@r.post("/admin/solicitudes/{uid}/rechazar")
def rechazar(uid: str, d: Respuesta, yo: Usuario = Depends(ADMIN), bd: Session = Depends(obtener_sesion)):
    administracion.rechazar_solicitud(bd, yo, uid, d.respuesta)
    return {"ok": True}
