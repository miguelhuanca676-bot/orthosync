from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..core.seguridad import requiere
from ..db.base import obtener_sesion
from ..db.modelos import Usuario
from ..esquemas.entradas import CuentaPaciente, PacienteDatos, PacienteNuevo
from ..servicios import pacientes as servicio
from .comun import PERSONAL

r = APIRouter(prefix="/api/pacientes", tags=["pacientes"])


@r.get("")
def listar(buscar: str = "", u: Usuario = Depends(requiere(*PERSONAL)), bd: Session = Depends(obtener_sesion)):
    return servicio.listar(bd, u, buscar)


@r.post("", status_code=201)
def crear(d: PacienteNuevo, u: Usuario = Depends(requiere(*PERSONAL)), bd: Session = Depends(obtener_sesion)):
    p = servicio.crear(bd, u, d.model_dump(exclude={"consentimiento"}), d.consentimiento)
    return servicio.vista(bd, p)


@r.get("/{pid}")
def ver(pid: str, u: Usuario = Depends(requiere(*PERSONAL)), bd: Session = Depends(obtener_sesion)):
    return servicio.vista(bd, servicio.ver(bd, u, pid))


@r.patch("/{pid}")
def cambiar(pid: str, d: PacienteDatos, u: Usuario = Depends(requiere(*PERSONAL)), bd: Session = Depends(obtener_sesion)):
    return servicio.vista(bd, servicio.cambiar(bd, u, pid, d.model_dump()))


@r.post("/{pid}/cuenta", status_code=201)
def crear_cuenta(pid: str, d: CuentaPaciente, u: Usuario = Depends(requiere(*PERSONAL)),
                 bd: Session = Depends(obtener_sesion)):
    return servicio.crear_cuenta(bd, u, pid, d.correo)
