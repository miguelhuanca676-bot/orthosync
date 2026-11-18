"""Tablas del sistema (modelo de datos). Cada clase es una tabla."""
from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, ahora, nuevo_uid

ROLES = ("administrador", "traumatologo", "recepcion", "paciente")


class Usuario(Base):
    __tablename__ = "usuarios"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    correo: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    clave_hash: Mapped[str] = mapped_column(String(255))
    rol: Mapped[str] = mapped_column(String(20), index=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    paciente_id: Mapped[int | None] = mapped_column(ForeignKey("pacientes.id"), nullable=True)
    creado: Mapped[datetime] = mapped_column(DateTime, default=ahora)
    # seguridad
    version_sesion: Mapped[int | None] = mapped_column(Integer, default=0, nullable=True)   # cambia => cierra sesiones
    debe_cambiar_clave: Mapped[bool | None] = mapped_column(Boolean, default=False, nullable=True)
    intentos_fallidos: Mapped[int | None] = mapped_column(Integer, default=0, nullable=True)
    bloqueado_hasta: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    acepto_terminos_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Paciente(Base):
    __tablename__ = "pacientes"
    id: Mapped[int] = mapped_column(primary_key=True)
    uid: Mapped[str | None] = mapped_column(String(32), default=nuevo_uid, nullable=True)
    codigo: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    nombres: Mapped[str] = mapped_column(String(120))
    apellidos: Mapped[str] = mapped_column(String(120))
    documento: Mapped[str | None] = mapped_column(String(40), nullable=True)
    fecha_nacimiento: Mapped[date | None] = mapped_column(Date, nullable=True)
    sexo: Mapped[str | None] = mapped_column(String(1), nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(40), nullable=True)
    creado_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", use_alter=True), nullable=True)
    creado: Mapped[datetime] = mapped_column(DateTime, default=ahora)
    # consentimiento informado (y tutor si es menor de edad)
    consentimiento_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    tutor_nombre: Mapped[str | None] = mapped_column(String(160), nullable=True)
    tutor_documento: Mapped[str | None] = mapped_column(String(40), nullable=True)
    estudios: Mapped[list["Estudio"]] = relationship(back_populates="paciente", order_by="Estudio.fecha_estudio",
                                                     cascade="all, delete-orphan")


class Estudio(Base):
    """Una radiografía de un paciente: el archivo, el resultado del sistema y la valoración del médico."""
    __tablename__ = "estudios"
    id: Mapped[int] = mapped_column(primary_key=True)
    uid: Mapped[str | None] = mapped_column(String(32), default=nuevo_uid, nullable=True)
    paciente_id: Mapped[int] = mapped_column(ForeignKey("pacientes.id"), index=True)
    medico_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    fecha_estudio: Mapped[date] = mapped_column(Date)
    archivo_original: Mapped[str] = mapped_column(String(255))
    carpeta: Mapped[str] = mapped_column(String(255))          # dentro de DIR_ARCHIVOS
    creado: Mapped[datetime] = mapped_column(DateTime, default=ahora)

    # --- resultado del sistema ---
    estado_analisis: Mapped[str] = mapped_column(String(20), default="pendiente")  # listo | sin_modelos | error
    p_tumor: Mapped[float | None] = mapped_column(Float, nullable=True)
    p_maligno: Mapped[float | None] = mapped_column(Float, nullable=True)
    sospechoso: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    conclusion_sistema: Mapped[str | None] = mapped_column(String(160), nullable=True)
    cajas: Mapped[list | None] = mapped_column(JSON, nullable=True)            # [[x1,y1,x2,y2,confianza], ...]
    area_lesion: Mapped[float | None] = mapped_column(Float, nullable=True)    # fracción de la imagen (0-1)
    hueso_sugerido: Mapped[dict | None] = mapped_column(JSON, nullable=True)   # {"femur": 0.91, ...}
    aspecto_sugerido: Mapped[dict | None] = mapped_column(JSON, nullable=True) # {"litica": 0.8, "crecimiento": 0.2, ...}

    # --- valoración del médico ---
    hueso: Mapped[str | None] = mapped_column(String(20), nullable=True)
    lado: Mapped[str | None] = mapped_column(String(10), nullable=True)
    zona_3d: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    opinion: Mapped[str | None] = mapped_column(String(20), nullable=True)
    evolucion: Mapped[str | None] = mapped_column(String(20), nullable=True)
    tratamiento: Mapped[str | None] = mapped_column(Text, nullable=True)
    comentario: Mapped[str | None] = mapped_column(Text, nullable=True)
    valorado_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # --- lo que ve el paciente (solo si el médico lo publica) ---
    publicado: Mapped[bool] = mapped_column(Boolean, default=False)
    mensaje_paciente: Mapped[str | None] = mapped_column(Text, nullable=True)
    proximo_control: Mapped[date | None] = mapped_column(Date, nullable=True)

    # --- corrección del médico (sirve para reentrenar el modelo) ---
    cajas_medico: Mapped[list | None] = mapped_column(JSON, nullable=True)     # [[x1,y1,x2,y2], ...] en fracción de la imagen
    corregido_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    paciente: Mapped[Paciente] = relationship(back_populates="estudios")


class SolicitudEliminacion(Base):
    """Pedido del paciente para borrar sus datos. Lo revisa y ejecuta el administrador."""
    __tablename__ = "solicitudes_eliminacion"
    id: Mapped[int] = mapped_column(primary_key=True)
    uid: Mapped[str] = mapped_column(String(32), default=nuevo_uid, unique=True)
    paciente_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    codigo_paciente: Mapped[str] = mapped_column(String(20))
    fecha: Mapped[datetime] = mapped_column(DateTime, default=ahora)
    motivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    estado: Mapped[str] = mapped_column(String(20), default="pendiente")   # pendiente | completada | rechazada
    respuesta: Mapped[str | None] = mapped_column(Text, nullable=True)
    resuelta_por: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resuelta_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class InformeEmitido(Base):
    """Cada PDF emitido queda registrado con su huella (SHA-256) para poder verificar que es auténtico."""
    __tablename__ = "informes_emitidos"
    id: Mapped[int] = mapped_column(primary_key=True)
    uid: Mapped[str] = mapped_column(String(32), default=nuevo_uid, unique=True)
    estudio_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    codigo_paciente: Mapped[str] = mapped_column(String(20))
    fecha_estudio: Mapped[date | None] = mapped_column(Date, nullable=True)
    tipo: Mapped[str] = mapped_column(String(20))          # medico | paciente
    emitido_en: Mapped[datetime] = mapped_column(DateTime, default=ahora)
    huella: Mapped[str | None] = mapped_column(String(64), nullable=True)


class Auditoria(Base):
    __tablename__ = "auditoria"
    id: Mapped[int] = mapped_column(primary_key=True)
    fecha: Mapped[datetime] = mapped_column(DateTime, default=ahora, index=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    accion: Mapped[str] = mapped_column(String(60))
    detalle: Mapped[str | None] = mapped_column(String(255), nullable=True)
    paciente_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
