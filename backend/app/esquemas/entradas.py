"""Datos que llegan a la API (lo que envía el navegador). Pydantic valida tipos y tamaños antes de
que el pedido llegue a los servicios."""
from datetime import date

from pydantic import BaseModel, EmailStr, Field


class Credenciales(BaseModel):
    correo: str = Field(max_length=160)
    clave: str = Field(max_length=200)


class CambioClave(BaseModel):
    clave_actual: str = Field(max_length=200)
    clave_nueva: str = Field(min_length=8, max_length=200)


class UsuarioNuevo(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    correo: EmailStr
    rol: str
    clave: str = Field(min_length=8, max_length=200)


class UsuarioCambio(BaseModel):
    nombre: str | None = Field(default=None, max_length=120)
    rol: str | None = None
    activo: bool | None = None
    clave: str | None = Field(default=None, min_length=8, max_length=200)


class PacienteDatos(BaseModel):
    nombres: str = Field(min_length=1, max_length=120)
    apellidos: str = Field(min_length=1, max_length=120)
    documento: str | None = Field(default=None, max_length=40)
    fecha_nacimiento: date
    sexo: str | None = Field(default=None, pattern="^[MF]$")
    telefono: str | None = Field(default=None, max_length=40)
    tutor_nombre: str | None = Field(default=None, max_length=160)
    tutor_documento: str | None = Field(default=None, max_length=40)


class PacienteNuevo(PacienteDatos):
    consentimiento: bool = False


class CuentaPaciente(BaseModel):
    correo: EmailStr


class Valoracion(BaseModel):
    hueso: str | None = None
    lado: str | None = Field(default=None, pattern="^(izquierdo|derecho)$")
    zona_3d: dict | None = None
    opinion: str | None = None
    evolucion: str | None = None
    tratamiento: str | None = Field(default=None, max_length=4000)
    comentario: str | None = Field(default=None, max_length=4000)
    mensaje_paciente: str | None = Field(default=None, max_length=4000)
    proximo_control: date | None = None
    cajas_medico: list[list[float]] | None = None    # recuadros corregidos por el médico, en fracción de la imagen
    publicar: bool | None = None      # True: al guardar, el estudio queda visible en el portal del paciente


class Publicacion(BaseModel):
    publicado: bool


class PedidoInforme(BaseModel):
    imagen_3d: str | None = None   # captura del visor 3D (data:image/png;base64,...)


class Recorte(BaseModel):
    x1: float = Field(ge=0, le=1)
    y1: float = Field(ge=0, le=1)
    x2: float = Field(ge=0, le=1)
    y2: float = Field(ge=0, le=1)


class PedidoEliminacion(BaseModel):
    motivo: str | None = Field(default=None, max_length=1000)


class Respuesta(BaseModel):
    respuesta: str = Field(min_length=3, max_length=1000)
