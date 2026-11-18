"""Motor de la CNN: análisis de la radiografía con los modelos entrenados (formato ONNX, sin PyTorch).

Etapa 1: normal vs. lesión + mapa de calor     Etapa 2: cuadros de la lesión (YOLO)
Etapa 3: benigno vs. maligno                   Extra: hueso sugerido (para el visor 3D)
"""
import json, os, threading

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import config

_candado = threading.Lock()
_estado = {"cargado": False, "info": None, "sesiones": {}}


def _cargar():
    with _candado:
        if _estado["cargado"]:
            return
        ruta_info = os.path.join(config.DIR_MODELOS, "info.json")
        if os.path.exists(ruta_info):
            import onnxruntime as ort
            with open(ruta_info, encoding="utf-8") as f:
                info = json.load(f)
            for clave, m in info.get("modelos", {}).items():
                ruta = os.path.join(config.DIR_MODELOS, m["archivo"])
                if os.path.exists(ruta):
                    _estado["sesiones"][clave] = ort.InferenceSession(ruta, sess_options=_opciones(ort), providers=["CPUExecutionProvider"])
            _estado["info"] = info
        _estado["cargado"] = True


def _opciones(ort):
    """En servidores chicos (ORTHOSYNC_POCA_MEMORIA=1) se usa un hilo y no se reserva memoria de más."""
    o = ort.SessionOptions()
    if os.environ.get("ORTHOSYNC_POCA_MEMORIA") == "1":
        o.intra_op_num_threads = 1; o.inter_op_num_threads = 1
        o.enable_cpu_mem_arena = False; o.enable_mem_pattern = False
    return o


def reiniciar():
    """Vuelve a leer los modelos (por ejemplo, después de copiar unos nuevos)."""
    with _candado:
        _estado.update({"cargado": False, "info": None, "sesiones": {}})


def disponibles() -> dict:
    _cargar()
    return {k: k in _estado["sesiones"] for k in ("tumor", "detector", "malignidad", "hueso", "aspecto")}


def info_modelos() -> dict | None:
    _cargar()
    return _estado["info"]


# ---------------------------------------------------------------- preprocesamiento (igual que al entrenar)
def _cuadrar(img: Image.Image, tam: int) -> Image.Image:
    gris = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(np.asarray(img.convert("L")))
    img = Image.fromarray(gris)
    e = tam / max(img.size)
    img = img.resize((max(1, round(img.width * e)), max(1, round(img.height * e))), Image.BILINEAR)
    lienzo = Image.new("L", (tam, tam), 0)
    lienzo.paste(img, ((tam - img.width) // 2, (tam - img.height) // 2))
    return lienzo.convert("RGB")


def _tensor(img_rgb: Image.Image) -> np.ndarray:
    a = np.asarray(img_rgb).astype(np.float32) / 255.0
    a = (a - np.array([0.485, 0.456, 0.406], np.float32)) / np.array([0.229, 0.224, 0.225], np.float32)
    return a.transpose(2, 0, 1)[None].astype(np.float32)


def _clasificar(clave: str, img: Image.Image):
    m = _estado["info"]["modelos"][clave]
    base = _cuadrar(img, m["tam"])
    return base, _estado["sesiones"][clave].run(None, {"imagen": _tensor(base)}), m


def _mapa_de_calor(base: Image.Image, mapa: np.ndarray) -> Image.Image:
    cam = cv2.resize(mapa.astype(np.float32), base.size, interpolation=cv2.INTER_LINEAR)
    cam = (cam - cam.min()) / (cam.max() - cam.min() + 1e-8)
    gris = np.asarray(base).astype(np.float32) / 255.0
    calor = np.stack([np.ones_like(cam), cam ** 2, np.zeros_like(cam)], axis=-1)
    alfa = (cam ** 1.5 * 0.6)[..., None]
    return Image.fromarray(((gris * (1 - alfa) + calor * alfa) * 255).astype(np.uint8))


# ---------------------------------------------------------------- detector YOLO
def _detectar(img: Image.Image, confianza: float) -> list[list[float]]:
    m = _estado["info"]["modelos"]["detector"]; tam = m["tam"]
    rgb = np.asarray(img.convert("RGB"))
    alto, ancho = rgb.shape[:2]
    e = min(tam / alto, tam / ancho)
    nw, nh = round(ancho * e), round(alto * e)
    lienzo = np.full((tam, tam, 3), 114, np.uint8)
    dx, dy = (tam - nw) // 2, (tam - nh) // 2
    lienzo[dy:dy + nh, dx:dx + nw] = cv2.resize(rgb, (nw, nh), interpolation=cv2.INTER_LINEAR)
    x = (lienzo.astype(np.float32) / 255.0).transpose(2, 0, 1)[None]
    s = _estado["sesiones"]["detector"]
    salida = s.run(None, {s.get_inputs()[0].name: x})[0][0]      # (4 + clases, N)
    cajas, puntajes = salida[:4].T, salida[4:].max(axis=0)
    ok = puntajes >= confianza
    cajas, puntajes = cajas[ok], puntajes[ok]
    if len(cajas) == 0:
        return []
    xywh = np.stack([cajas[:, 0] - cajas[:, 2] / 2, cajas[:, 1] - cajas[:, 3] / 2, cajas[:, 2], cajas[:, 3]], 1)
    quedan = cv2.dnn.NMSBoxes(xywh.tolist(), puntajes.tolist(), confianza, 0.5)
    res = []
    for i in np.array(quedan).flatten():
        x1, y1, w, h = xywh[i]
        x1, y1, x2, y2 = (x1 - dx) / e, (y1 - dy) / e, (x1 + w - dx) / e, (y1 + h - dy) / e
        res.append([float(np.clip(x1, 0, ancho)), float(np.clip(y1, 0, alto)),
                    float(np.clip(x2, 0, ancho)), float(np.clip(y2, 0, alto)), float(puntajes[i])])
    return sorted(res, key=lambda c: -c[4])


def _dibujar_cajas(img: Image.Image, cajas) -> Image.Image:
    salida = img.convert("RGB"); d = ImageDraw.Draw(salida)
    grosor = max(2, round(max(salida.size) / 300)); letra_px = max(12, round(max(salida.size) / 40))
    try:
        letra = ImageFont.load_default(size=letra_px)
    except TypeError:
        letra = ImageFont.load_default()
    for x1, y1, x2, y2, c in cajas:
        color = (0, 200, 255) if c > 0 else (255, 190, 0)     # celeste: detector · ámbar: zona aproximada
        d.rectangle([x1, y1, x2, y2], outline=color, width=grosor)
        d.text((x1 + grosor, max(0, y1 - letra_px - 2)), f"{c:.0%}" if c > 0 else "aprox.", fill=color, font=letra)
    return salida


def _caja_desde_mapa(mapa: np.ndarray, img: Image.Image, tam: int):
    """Respaldo cuando el detector no marca nada: cuadro que encierra la zona más activa del mapa de calor.
    Devuelve la caja en píxeles de la imagen original, con confianza 0 (= aproximada)."""
    cam = cv2.resize(mapa.astype(np.float32), (tam, tam), interpolation=cv2.INTER_LINEAR)
    cam = (cam - cam.min()) / (cam.max() - cam.min() + 1e-8)
    n, etiquetas, stats, _ = cv2.connectedComponentsWithStats((cam >= 0.6).astype(np.uint8), connectivity=8)
    if n <= 1:
        return None
    py, px = np.unravel_index(int(cam.argmax()), cam.shape)
    x, y, w, h, _ = stats[etiquetas[py, px]] if etiquetas[py, px] > 0 else stats[1 + int(np.argmax(stats[1:, 4]))]
    e = tam / max(img.size)                       # deshacer el redimensionado con relleno
    dx, dy = (tam - round(img.width * e)) / 2, (tam - round(img.height * e)) / 2
    x1, y1, x2, y2 = (x - dx) / e, (y - dy) / e, (x + w - dx) / e, (y + h - dy) / e
    x1, x2 = float(np.clip(x1, 0, img.width)), float(np.clip(x2, 0, img.width))
    y1, y2 = float(np.clip(y1, 0, img.height)), float(np.clip(y2, 0, img.height))
    if x2 - x1 < 4 or y2 - y1 < 4:
        return None
    return [x1, y1, x2, y2, 0.0]


# ---------------------------------------------------------------- análisis completo
# aspecto que predice el modelo -> forma de la lesión en el visor 3D
TIPO_3D = {"crecimiento": "crecimiento", "litica": "cavidad", "mixta": "cavidad"}


def analizar(img: Image.Image) -> dict:
    """Devuelve el resultado del sistema para una radiografía. Si aún no hay modelos
    entrenados, devuelve estado 'sin_modelos' y el estudio se guarda igual."""
    _cargar()
    if "tumor" not in _estado["sesiones"]:
        return {"estado": "sin_modelos"}
    img = img.convert("L")
    base, (probs, mapa), m = _clasificar("tumor", img)
    p_tumor = float(probs[0, 1]); umbral = float(m.get("umbral", 0.5))
    sospechoso = p_tumor >= umbral

    # Localización. Si el clasificador ya ve una lesión, el detector trabaja con un umbral más bajo
    # (marca más lesiones); si no, con uno alto (evita cuadros falsos en radiografías normales).
    cajas = _detectar(img, 0.10 if sospechoso else 0.35) if "detector" in _estado["sesiones"] else []
    if sospechoso and not cajas:
        aprox = _caja_desde_mapa(mapa[0], img, m["tam"])
        if aprox:
            cajas = [aprox]
    area = float(sum((c[2] - c[0]) * (c[3] - c[1]) for c in cajas) / (img.width * img.height)) if cajas else 0.0

    p_mal, umbral_mal = None, None
    if sospechoso and "malignidad" in _estado["sesiones"]:
        _, (probs_m, _), mm = _clasificar("malignidad", img)
        p_mal, umbral_mal = float(probs_m[0, 1]), float(mm.get("umbral", 0.5))

    hueso = None
    if "hueso" in _estado["sesiones"]:
        _, (probs_h,), mh = _clasificar("hueso", img)
        hueso = {c: round(float(p), 4) for c, p in sorted(zip(mh["clases"], probs_h[0]), key=lambda t: -t[1])}

    # aspecto radiológico (decide cómo se dibuja la lesión en el 3D); solo si hay una lesión sospechosa
    aspecto = None
    if sospechoso and "aspecto" in _estado["sesiones"]:
        _, (probs_a,), ma = _clasificar("aspecto", img)
        aspecto = {c: round(float(p), 4) for c, p in sorted(zip(ma["clases"], probs_a[0]), key=lambda t: -t[1])}

    if not sospechoso:
        conclusion = "Sin hallazgos sospechosos"
    elif p_mal is None:
        conclusion = "Lesión sospechosa"
    elif p_mal >= umbral_mal:
        conclusion = "Lesión sospechosa con características de malignidad"
    else:
        conclusion = "Lesión sospechosa con características de benignidad"

    # zona para el visor 3D: posición de la lesión a lo largo de la imagen (0 = arriba, 1 = abajo)
    zona = None
    if cajas:
        x1, y1, x2, y2, _ = cajas[0]
        zona = {"posicion": round((y1 + y2) / 2 / img.height, 3), "extension": round((y2 - y1) / img.height, 3)}
        if aspecto:
            zona["tipo"] = TIPO_3D.get(next(iter(aspecto)))

    return {"estado": "listo", "p_tumor": p_tumor, "umbral_tumor": umbral, "sospechoso": bool(sospechoso),
            "p_maligno": p_mal, "umbral_malignidad": umbral_mal, "cajas": [[round(v, 2) for v in c] for c in cajas],
            "area_lesion": round(area, 5), "hueso_sugerido": hueso, "aspecto_sugerido": aspecto,
            "conclusion": conclusion, "zona_3d": zona,
            "img_cajas": _dibujar_cajas(img, cajas), "img_calor": _mapa_de_calor(base, mapa[0])}
