"""Convierte lo que sube el médico (JPG, PNG, DICOM o PDF) en la imagen de la radiografía.
En los PDF busca la radiografía dentro de la página y la recorta."""
import io

import warnings

import cv2
import numpy as np
from PIL import Image

# Protección contra "bombas" de descompresión: imágenes diminutas en disco que ocupan gigas al abrirse
Image.MAX_IMAGE_PIXELS = 80_000_000
warnings.simplefilter("error", Image.DecompressionBombWarning)

EXTENSIONES = (".jpg", ".jpeg", ".png", ".dcm", ".dicom", ".pdf")


class ArchivoNoValido(Exception):
    pass


def _de_dicom(datos: bytes) -> Image.Image:
    import pydicom
    ds = pydicom.dcmread(io.BytesIO(datos))
    a = ds.pixel_array.astype(np.float32)   # solo se usan los píxeles, ningún dato del paciente
    if a.ndim == 3:
        a = a[..., 0] if a.shape[-1] in (3, 4) else a[0]
    a = (a - a.min()) / max(float(a.max() - a.min()), 1e-6) * 255.0
    if str(getattr(ds, "PhotometricInterpretation", "")) == "MONOCHROME1":
        a = 255.0 - a
    return Image.fromarray(a.astype(np.uint8), mode="L")


def recortar_radiografia(img: Image.Image) -> Image.Image:
    """Dentro de una página (fondo claro, textos, logos) localiza el bloque oscuro más grande,
    que es la placa, y devuelve solo esa zona. Si no hay un bloque claro, devuelve la imagen entera."""
    gris = np.asarray(img.convert("L"))
    alto, ancho = gris.shape
    oscuro = (gris < 200).astype(np.uint8)
    k = max(3, min(alto, ancho) // 100)
    oscuro = cv2.morphologyEx(oscuro, cv2.MORPH_OPEN, np.ones((k, k), np.uint8))   # quita textos y líneas finas
    oscuro = cv2.morphologyEx(oscuro, cv2.MORPH_CLOSE, np.ones((k * 3, k * 3), np.uint8))
    n, _, stats, _ = cv2.connectedComponentsWithStats(oscuro, connectivity=8)
    if n <= 1:
        return img
    i = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    x, y, w, h, area = stats[i]
    if w * h < 0.08 * alto * ancho or w * h > 0.97 * alto * ancho or area < 0.5 * w * h:
        return img
    return img.crop((int(x), int(y), int(x + w), int(y + h)))


def _de_pdf(datos: bytes) -> Image.Image:
    import pymupdf
    try:
        doc = pymupdf.open(stream=datos, filetype="pdf")
    except Exception as e:
        raise ArchivoNoValido("No se pudo abrir el PDF") from e
    mejor, mejor_area = None, 0
    for pagina in list(doc)[:10]:
        # 1) imágenes incrustadas en el PDF (lo habitual en los informes de imagenología)
        for ref in pagina.get_images(full=True):
            try:
                pix = pymupdf.Pixmap(doc, ref[0])
                if pix.colorspace is None or pix.n - pix.alpha > 3:
                    pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
            except Exception:
                continue
            if img.width * img.height > mejor_area and min(img.size) >= 200:
                mejor, mejor_area = img, img.width * img.height
    if mejor is None:
        # 2) PDF escaneado o vectorial: se dibuja la página y se busca la placa
        for pagina in list(doc)[:10]:
            pix = pagina.get_pixmap(dpi=200)
            img = recortar_radiografia(Image.open(io.BytesIO(pix.tobytes("png"))))
            if img.width * img.height > mejor_area:
                mejor, mejor_area = img, img.width * img.height
    else:
        mejor = recortar_radiografia(mejor)
    if mejor is None:
        raise ArchivoNoValido("No se encontró ninguna radiografía dentro del PDF")
    return mejor


def extraer_radiografia(nombre: str, datos: bytes) -> Image.Image:
    """Devuelve la radiografía en escala de grises."""
    n = nombre.lower()
    if not n.endswith(EXTENSIONES):
        raise ArchivoNoValido("Formato no admitido. Usa JPG, PNG, DICOM o PDF.")
    try:
        if n.endswith(".pdf"):
            img = _de_pdf(datos)
        elif n.endswith((".dcm", ".dicom")):
            img = _de_dicom(datos)
        else:
            img = Image.open(io.BytesIO(datos)); img.load()
    except ArchivoNoValido:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as e:
        raise ArchivoNoValido("La imagen es demasiado grande") from e
    except Exception as e:
        raise ArchivoNoValido("El archivo está dañado o no es una imagen válida") from e
    img = img.convert("L")
    if min(img.size) < 100:
        raise ArchivoNoValido("La imagen es demasiado pequeña para analizarla")
    if max(img.size) > 3000:   # tamaño razonable para guardar y mostrar
        e = 3000 / max(img.size)
        img = img.resize((round(img.width * e), round(img.height * e)), Image.LANCZOS)
    return img
