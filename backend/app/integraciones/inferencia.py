"""Cliente del servicio de inferencia (la CNN). La API nunca carga los modelos: se los pide a ese servicio.

Si el servicio no responde, el estudio se guarda igual con estado 'sin_servicio' y el médico puede volver a
analizarlo después con el botón «Analizar de nuevo»."""
import base64, io, time

import httpx
from PIL import Image

from ..core import config

_cliente: httpx.Client | None = None
_cache_info = {"t": 0.0, "datos": None}
_SEG_CACHE = 60


def _http() -> httpx.Client:
    global _cliente
    if _cliente is None:
        _cliente = httpx.Client(base_url=config.INFERENCIA_URL, timeout=config.INFERENCIA_ESPERA_S,
                                headers={"X-Token-Interno": config.INFERENCIA_TOKEN})
    return _cliente


def usar_cliente(cliente):
    """Para pruebas: permite conectar el servicio de inferencia en memoria, sin red."""
    global _cliente
    _cliente = cliente
    _cache_info.update(t=0.0, datos=None)


def analizar(img: Image.Image) -> dict:
    b = io.BytesIO(); img.save(b, "PNG")
    try:
        r = _http().post("/analizar", files={"imagen": ("radiografia.png", b.getvalue(), "image/png")})
        r.raise_for_status()
        datos = r.json()
    except (httpx.HTTPError, ValueError):
        return {"estado": "sin_servicio"}
    if datos.get("estado") == "listo":
        for clave in ("img_cajas", "img_calor"):
            datos[clave] = Image.open(io.BytesIO(base64.b64decode(datos[clave])))
    return datos


def _info() -> dict:
    if time.time() - _cache_info["t"] < _SEG_CACHE and _cache_info["datos"] is not None:
        return _cache_info["datos"]
    try:
        r = _http().get("/info", timeout=10); r.raise_for_status(); datos = r.json()
    except (httpx.HTTPError, ValueError):
        datos = {"disponibles": None, "info": None}
    _cache_info.update(t=time.time(), datos=datos)
    return datos


def disponibles() -> dict:
    """{'tumor': True, ...} o {'servicio': False} si la CNN no responde."""
    d = _info()["disponibles"]
    return d if d is not None else {"servicio": False}


def info_modelos() -> dict | None:
    return _info()["info"]
