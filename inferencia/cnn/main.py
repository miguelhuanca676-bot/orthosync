"""Servicio de inferencia de Orthosync: recibe una radiografía y devuelve lo que ve la CNN.

Es un proceso aparte de la API para que la parte pesada (modelos, memoria, CPU) se pueda mover a otra
máquina o escalar sin tocar el resto del sistema. No guarda nada ni conoce a los pacientes: solo imágenes.

Ejecutar:  uvicorn cnn.main:app --port 8001
"""
import base64, hmac, io, warnings

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from PIL import Image

from . import config, motor

Image.MAX_IMAGE_PIXELS = 80_000_000
warnings.simplefilter("error", Image.DecompressionBombWarning)

app = FastAPI(title="Orthosync · inferencia", version="1.0", docs_url="/docs", redoc_url=None)


def _token(x_token_interno: str = Header(default="")):
    if config.TOKEN and not hmac.compare_digest(x_token_interno, config.TOKEN):
        raise HTTPException(401, "Token interno no válido")


def _png64(img: Image.Image) -> str:
    b = io.BytesIO(); img.save(b, "PNG", optimize=True)
    return base64.b64encode(b.getvalue()).decode()


@app.get("/salud")
def salud():
    """Para el monitor: responde sin cargar los modelos."""
    return {"servicio": "inferencia", "ok": True}


@app.get("/info", dependencies=[Depends(_token)])
def info():
    return {"disponibles": motor.disponibles(), "info": motor.info_modelos()}


@app.post("/recargar", dependencies=[Depends(_token)])
def recargar():
    """Vuelve a leer los modelos de la carpeta (después de copiar unos nuevos)."""
    motor.reiniciar()
    return {"disponibles": motor.disponibles()}


@app.post("/analizar", dependencies=[Depends(_token)])
async def analizar(imagen: UploadFile = File(...)):
    datos = await imagen.read(config.TAM_MAX_MB * 1024 * 1024 + 1)
    if len(datos) > config.TAM_MAX_MB * 1024 * 1024:
        raise HTTPException(413, "Imagen demasiado grande")
    try:
        img = Image.open(io.BytesIO(datos)); img.load()
    except Exception:
        raise HTTPException(400, "No es una imagen válida")
    r = motor.analizar(img)
    if r.get("estado") == "listo":
        r["img_cajas"] = _png64(r["img_cajas"])
        r["img_calor"] = _png64(r["img_calor"])
    return r
