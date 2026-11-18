"""Piezas que comparten todas las rutas."""
from fastapi import Request, Response

from ..dominio.reglas import PERSONAL  # noqa: F401  (se reexporta para las rutas)


def archivo(datos: bytes, nombre: str, tipo: str) -> Response:
    return Response(datos, media_type=tipo, headers={"Content-Disposition": f'attachment; filename="{nombre}"',
                                                     "Cache-Control": "no-store"})


def sitio(request: Request) -> str:
    """Dirección pública con la que entró el usuario (para el QR, si no se configuró ORTHOSYNC_SITIO).
    Detrás de Cloudflare, la función del proxy envía la dirección original en X-Sitio-Original."""
    original = request.headers.get("x-sitio-original", "")
    if original.startswith("https://") and len(original) < 200 and "/" not in original[8:]:
        return original
    return str(request.base_url).rstrip("/")
