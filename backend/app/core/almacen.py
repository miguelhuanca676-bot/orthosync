"""Las radiografías se guardan CIFRADAS en el disco (Fernet: AES + firma).
Aunque alguien copie la carpeta 'archivos', no puede ver las imágenes sin la clave de secretos/."""
import io

from cryptography.fernet import Fernet, InvalidToken
from PIL import Image

from . import config

_fernet = Fernet(config.CLAVE_ARCHIVOS.encode())


def guardar_imagen(img: Image.Image, ruta: str):
    b = io.BytesIO(); img.save(b, "PNG")
    with open(ruta, "wb") as f:
        f.write(_fernet.encrypt(b.getvalue()))


def leer_bytes(ruta: str) -> bytes:
    with open(ruta, "rb") as f:
        datos = f.read()
    try:
        return _fernet.decrypt(datos)
    except InvalidToken:
        if datos.startswith(b"\x89PNG"):   # archivo de una versión anterior, sin cifrar
            return datos
        raise


def abrir_imagen(ruta: str) -> Image.Image:
    img = Image.open(io.BytesIO(leer_bytes(ruta)))
    img.load()
    return img


def cifrar_existentes(carpeta: str) -> int:
    """Cifra las radiografías guardadas por versiones anteriores (que estaban sin cifrar). Se ejecuta al arrancar."""
    import os
    n = 0
    for raiz, _, archivos in os.walk(carpeta):
        for nombre in archivos:
            if not nombre.endswith(".png"):
                continue
            ruta = os.path.join(raiz, nombre)
            with open(ruta, "rb") as f:
                datos = f.read()
            if datos.startswith(b"\x89PNG"):
                with open(ruta + ".tmp", "wb") as f:
                    f.write(_fernet.encrypt(datos))
                os.replace(ruta + ".tmp", ruta)
                n += 1
    return n
