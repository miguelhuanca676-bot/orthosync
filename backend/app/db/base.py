"""Conexión a la base de datos. Funciona con SQLite (en tu laptop) y PostgreSQL (Neon, en la nube)."""
import secrets
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool

from ..core import config

_sqlite = config.BASE_DATOS.startswith("sqlite")
# Neon apaga la base de datos tras 5 minutos sin consultas (así no gasta el plan gratuito). Para que pueda
# apagarse, no se dejan conexiones abiertas: cada petición abre la suya (NullPool).
_sin_pool = "neon.tech" in config.BASE_DATOS or config.BD_SIN_POOL
motor = create_engine(config.BASE_DATOS, pool_pre_ping=True,
                      connect_args={"check_same_thread": False} if _sqlite else {},
                      **({"poolclass": NullPool} if _sin_pool and not _sqlite else {}))
Sesion = sessionmaker(bind=motor, autoflush=False, expire_on_commit=False)


def ahora():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def nuevo_uid() -> str:
    """Identificador aleatorio que se muestra hacia afuera (no revela cuántos registros hay ni su orden)."""
    return secrets.token_urlsafe(12)


class Base(DeclarativeBase):
    pass


def obtener_sesion():
    """Dependencia de FastAPI: una sesión de base de datos por petición."""
    s = Sesion()
    try:
        yield s
    finally:
        s.close()
