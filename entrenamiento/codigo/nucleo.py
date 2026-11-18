"""Núcleo del sistema: preprocesamiento, modelos, Grad-CAM y análisis completo
de una radiografía. Lo usan los scripts de entrenamiento, la evaluación y la app."""
import json
import os

import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image, ImageDraw, ImageFont
from torchvision import models, transforms

RAIZ = os.path.dirname(os.path.abspath(__file__))
DIR_MODELOS = os.path.join(RAIZ, "modelos")
DIR_RESULTADOS = os.path.join(RAIZ, "resultados")
DIR_PREPARADOS = os.path.join(RAIZ, "datos_preparados")
RUTA_DIVISION = os.path.join(DIR_PREPARADOS, "division.csv")
RUTA_CONFIG = os.path.join(DIR_PREPARADOS, "config.json")

MODELO_TUMOR = os.path.join(DIR_MODELOS, "clasificador_tumor.pt")
MODELO_MALIGNIDAD = os.path.join(DIR_MODELOS, "clasificador_malignidad.pt")
MODELO_DETECTOR = os.path.join(DIR_MODELOS, "detector.pt")
MODELO_HUESO = os.path.join(DIR_MODELOS, "clasificador_hueso.pt")
MODELO_ASPECTO = os.path.join(DIR_MODELOS, "clasificador_aspecto.pt")

# Aspecto radiológico de la lesión según el tipo de tumor de BTXRD (columna -> aspecto). Se usa para dibujar el 3D:
#   crecimiento: la lesión sobresale del hueso (osteocondromas)
#   litica:      la lesión destruye hueso y se ve como un hueco (quiste óseo, tumor de células gigantes, osteofibroma)
#   mixta:       destruye hueso y forma masa (osteosarcoma)
# "other bt", "other mt" y el osteocondroma sinovial no se usan porque su aspecto es variable.
ASPECTOS = {"crecimiento": ["osteochondroma", "multiple osteochondromas"],
            "litica": ["simple bone cyst", "giant cell tumor", "osteofibroma"],
            "mixta": ["osteosarcoma"]}

# clave interna -> nombre de la columna en BTXRD
HUESOS = {"mano": "hand", "cubito": "ulna", "radio": "radius", "humero": "humerus", "pie": "foot",
          "tibia": "tibia", "perone": "fibula", "femur": "femur", "cadera": "hip bone"}

MEDIA, DESV = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]


# --------------------------------------------------------------------------
# Utilidades de archivos
# --------------------------------------------------------------------------
def buscar(raiz, nombre, carpeta=False):
    """Busca un archivo o carpeta por nombre dentro de raiz (sin importar mayúsculas)."""
    for d, carpetas, archivos in os.walk(raiz):
        for it in (carpetas if carpeta else archivos):
            if it.lower() == nombre.lower():
                return os.path.join(d, it)
    return None


def columna(df, nombre):
    limpio = lambda s: str(s).lower().replace(" ", "").replace("_", "").replace("-", "")
    for c in df.columns:
        if limpio(c) == limpio(nombre):
            return c
    return None


def dispositivo():
    return "cuda" if torch.cuda.is_available() else "cpu"


# --------------------------------------------------------------------------
# Lectura y preprocesamiento de imágenes
# --------------------------------------------------------------------------
def leer_imagen(origen, nombre=None) -> Image.Image:
    """Lee JPG/PNG o DICOM (.dcm) y devuelve una imagen en escala de grises.
    De un DICOM solo se usan los píxeles: no se lee ni se guarda ningún dato del paciente."""
    nombre = (nombre or (origen if isinstance(origen, str) else getattr(origen, "name", ""))).lower()
    if nombre.endswith((".dcm", ".dicom")):
        import pydicom
        ds = pydicom.dcmread(origen)
        a = ds.pixel_array.astype(np.float32)
        if a.ndim == 3:  # varias tramas o color: nos quedamos con un plano
            a = a[..., 0] if a.shape[-1] in (3, 4) else a[0]
        a = (a - a.min()) / max(float(a.max() - a.min()), 1e-6) * 255.0
        if str(getattr(ds, "PhotometricInterpretation", "")) == "MONOCHROME1":
            a = 255.0 - a
        return Image.fromarray(a.astype(np.uint8), mode="L")
    return Image.open(origen).convert("L")


def cuadrar(img: Image.Image, tam: int) -> Image.Image:
    """Escala de grises -> mejora de contraste (CLAHE) -> redimensionar con relleno."""
    gris = np.asarray(img.convert("L"))
    gris = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gris)
    img = Image.fromarray(gris)
    w, h = img.size
    escala = tam / max(w, h)
    img = img.resize((max(1, round(w * escala)), max(1, round(h * escala))), Image.BILINEAR)
    lienzo = Image.new("L", (tam, tam), 0)
    lienzo.paste(img, ((tam - img.width) // 2, (tam - img.height) // 2))
    return lienzo.convert("RGB")


def transformacion(entrenamiento: bool):
    pasos = []
    if entrenamiento:  # aumento de datos
        pasos += [
            transforms.RandomHorizontalFlip(),
            transforms.RandomAffine(degrees=12, translate=(0.05, 0.05), scale=(0.9, 1.1)),
            transforms.ColorJitter(brightness=0.2, contrast=0.2),
        ]
    pasos += [transforms.ToTensor(), transforms.Normalize(MEDIA, DESV)]
    return transforms.Compose(pasos)


def asegurar_cache(rutas, tam):
    """Guarda una copia ya preprocesada de cada imagen (acelera mucho el entrenamiento)."""
    carpeta = os.path.join(DIR_PREPARADOS, f"cache_{tam}")
    os.makedirs(carpeta, exist_ok=True)
    salida = []
    for i, r in enumerate(rutas):
        destino = os.path.join(carpeta, os.path.splitext(os.path.basename(r))[0] + ".png")
        if not os.path.exists(destino):
            cuadrar(leer_imagen(r), tam).save(destino)
        salida.append(destino)
        if (i + 1) % 500 == 0:
            print(f"  preparando imágenes {i + 1}/{len(rutas)}", flush=True)
    return salida


# --------------------------------------------------------------------------
# Clasificadores (ResNet18 con transfer learning)
# --------------------------------------------------------------------------
def crear_modelo(n_clases=2, preentrenado=True) -> nn.Module:
    red = None
    if preentrenado:
        try:
            red = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)
        except Exception as e:
            print(f"AVISO: no se pudieron descargar los pesos preentrenados ({e}).\n"
                  "       Se entrena desde cero; los resultados serán peores. Revisa tu internet.")
    if red is None:
        red = models.resnet18(weights=None)
    red.fc = nn.Linear(red.fc.in_features, n_clases)
    return red


def cargar_clasificador(ruta):
    datos = torch.load(ruta, map_location="cpu", weights_only=False)
    red = crear_modelo(len(datos["clases"]), preentrenado=False)
    red.load_state_dict(datos["pesos"])
    red.eval()
    return red, datos


def predecir_con_gradcam(red, x):
    """Devuelve (probabilidad de la clase positiva, mapa Grad-CAM normalizado 0-1)."""
    guardado = {}
    h1 = red.layer4.register_forward_hook(lambda m, i, o: guardado.__setitem__("act", o))
    h2 = red.layer4.register_full_backward_hook(lambda m, gi, go: guardado.__setitem__("grad", go[0]))
    try:
        red.zero_grad()
        salida = red(x)
        prob = float(F.softmax(salida, dim=1)[0, 1].detach())
        salida[0, 1].backward()
    finally:
        h1.remove(); h2.remove()
    pesos = guardado["grad"].mean(dim=(2, 3), keepdim=True)
    cam = F.relu((pesos * guardado["act"]).sum(dim=1, keepdim=True))
    cam = F.interpolate(cam, size=x.shape[-2:], mode="bilinear", align_corners=False)[0, 0]
    cam = cam.detach().numpy()
    cam = (cam - cam.min()) / (cam.max() - cam.min() + 1e-8)
    return prob, cam


def superponer_calor(base: Image.Image, cam: np.ndarray) -> Image.Image:
    gris = np.asarray(base.convert("RGB")).astype(np.float32) / 255.0
    calor = np.stack([np.ones_like(cam), cam ** 2, np.zeros_like(cam)], axis=-1)
    alfa = (cam ** 1.5 * 0.6)[..., None]
    return Image.fromarray(((gris * (1 - alfa) + calor * alfa) * 255).astype(np.uint8))


# --------------------------------------------------------------------------
# Sistema completo: las tres etapas sobre una radiografía
# --------------------------------------------------------------------------
class Sistema:
    """Etapa 1: ¿normal o lesión?   Etapa 2: ¿dónde?   Etapa 3: ¿benigna o maligna?"""

    def __init__(self):
        if not os.path.exists(MODELO_TUMOR):
            raise FileNotFoundError("Falta modelos/clasificador_tumor.pt. Entrena primero el sistema.")
        self.red_tumor, self.info_tumor = cargar_clasificador(MODELO_TUMOR)
        self.red_mal = self.info_mal = self.detector = None
        if os.path.exists(MODELO_MALIGNIDAD):
            self.red_mal, self.info_mal = cargar_clasificador(MODELO_MALIGNIDAD)
        if os.path.exists(MODELO_DETECTOR):
            from ultralytics import YOLO
            self.detector = YOLO(MODELO_DETECTOR)

    @property
    def umbral_tumor(self):
        return float(self.info_tumor.get("umbral", 0.5))

    @property
    def umbral_malignidad(self):
        return float(self.info_mal.get("umbral", 0.5)) if self.info_mal else 0.5

    def probabilidades(self, imagen: Image.Image):
        """Solo las dos probabilidades (rápido; lo usa la evaluación)."""
        with torch.no_grad():
            x = transformacion(False)(cuadrar(imagen, self.info_tumor["tam"])).unsqueeze(0)
            p_tumor = float(F.softmax(self.red_tumor(x), 1)[0, 1])
            p_mal = None
            if self.red_mal is not None:
                x = transformacion(False)(cuadrar(imagen, self.info_mal["tam"])).unsqueeze(0)
                p_mal = float(F.softmax(self.red_mal(x), 1)[0, 1])
        return p_tumor, p_mal

    def detectar(self, imagen: Image.Image, confianza=0.25):
        if self.detector is None:
            return []
        r = self.detector.predict(imagen.convert("RGB"), conf=confianza, verbose=False)[0]
        return [(*[float(v) for v in caja], float(c))
                for caja, c in zip(r.boxes.xyxy.cpu().numpy(), r.boxes.conf.cpu().numpy())]

    def analizar(self, imagen: Image.Image, umbral_tumor=None, umbral_malignidad=None, confianza_cajas=0.25):
        umbral_tumor = self.umbral_tumor if umbral_tumor is None else umbral_tumor
        umbral_malignidad = self.umbral_malignidad if umbral_malignidad is None else umbral_malignidad
        imagen = imagen.convert("L")

        # Etapa 1: clasificación + mapa de calor
        base = cuadrar(imagen, self.info_tumor["tam"])
        p_tumor, cam = predecir_con_gradcam(self.red_tumor, transformacion(False)(base).unsqueeze(0))
        sospechoso = p_tumor >= umbral_tumor

        # Etapa 2: localización
        cajas = self.detectar(imagen, confianza_cajas)
        con_cajas = imagen.convert("RGB")
        dibujo = ImageDraw.Draw(con_cajas)
        grosor = max(2, round(max(con_cajas.size) / 300))
        tam_letra = max(12, round(max(con_cajas.size) / 40))
        try:
            letra = ImageFont.load_default(size=tam_letra)
        except TypeError:  # versiones antiguas de Pillow
            letra = ImageFont.load_default()
        for x1, y1, x2, y2, c in cajas:
            dibujo.rectangle([x1, y1, x2, y2], outline=(0, 255, 0), width=grosor)
            dibujo.text((x1 + grosor, max(0, y1 - tam_letra - 2)), f"{c:.0%}", fill=(0, 255, 0), font=letra)

        # Etapa 3: benigno vs. maligno (solo si hay sospecha)
        p_mal = None
        if sospechoso and self.red_mal is not None:
            with torch.no_grad():
                x = transformacion(False)(cuadrar(imagen, self.info_mal["tam"])).unsqueeze(0)
                p_mal = float(F.softmax(self.red_mal(x), 1)[0, 1])

        if not sospechoso:
            conclusion = "Sin hallazgos sospechosos"
        elif p_mal is None:
            conclusion = "Lesión sospechosa"
        elif p_mal >= umbral_malignidad:
            conclusion = "Lesión sospechosa con características de malignidad"
        else:
            conclusion = "Lesión sospechosa con características de benignidad"

        return {
            "p_tumor": p_tumor, "umbral_tumor": umbral_tumor, "sospechoso": bool(sospechoso),
            "p_maligno": p_mal, "umbral_malignidad": umbral_malignidad,
            "cajas": cajas, "discordancia": bool(cajas) != bool(sospechoso) and self.detector is not None,
            "conclusion": conclusion,
            "img_original": imagen.convert("RGB"), "img_cajas": con_cajas,
            "img_calor": superponer_calor(base, cam),
        }


def leer_json(ruta, defecto=None):
    if os.path.exists(ruta):
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    return defecto
