"""Paso 4: entrena el detector YOLO que dibuja el cuadro sobre la lesión.

    python entrenar_detector.py
"""
import argparse, json, os, shutil

import pandas as pd
from PIL import Image

from nucleo import (DIR_MODELOS, DIR_PREPARADOS, DIR_RESULTADOS, MODELO_DETECTOR, RUTA_CONFIG,
                    RUTA_DIVISION, dispositivo, leer_json)

DIR_YOLO = os.path.join(DIR_PREPARADOS, "yolo")
PARTES = {"entrenamiento": "train", "validacion": "val", "prueba": "test"}


def cajas_de_anotacion(ruta_json):
    """Lee una anotación tipo LabelMe y devuelve los cuadros (x1, y1, x2, y2) en píxeles.
    Si hay rectángulos se usan esos; si solo hay contornos, se usa el cuadro que los encierra."""
    if not ruta_json or not os.path.exists(ruta_json):
        return []
    with open(ruta_json, encoding="utf-8") as f:
        formas = json.load(f).get("shapes", [])
    rect, poli = [], []
    for s in formas:
        pts = s.get("points") or []
        if len(pts) < 2:
            continue
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        caja = (min(xs), min(ys), max(xs), max(ys))
        (rect if s.get("shape_type") == "rectangle" or len(pts) == 2 else poli).append(caja)
    return rect or poli


def cajas_yolo(ruta_txt, w, h):
    """Lee recuadros en formato YOLO (fracciones) y los devuelve en píxeles."""
    cajas = []
    if ruta_txt and isinstance(ruta_txt, str) and os.path.exists(ruta_txt):
        for linea in open(ruta_txt, encoding="utf-8"):
            p = linea.split()
            if len(p) == 5:
                cx, cy, bw, bh = (float(v) for v in p[1:])
                cajas.append(((cx - bw / 2) * w, (cy - bh / 2) * h, (cx + bw / 2) * w, (cy + bh / 2) * h))
    return cajas


def construir_dataset(lado_max=640):
    df = pd.read_csv(RUTA_DIVISION)
    dir_anot = (leer_json(RUTA_CONFIG) or {}).get("dir_anot")
    if not dir_anot:
        raise SystemExit("El dataset no trae la carpeta Annotations; no se puede entrenar el detector.")
    shutil.rmtree(DIR_YOLO, ignore_errors=True)
    con_lesion = df[df["clase"] != "normal"]
    # también algunas radiografías normales como "fondo", para reducir falsas alarmas
    normales = df[df["clase"] == "normal"]
    normales = normales.sample(min(len(normales), max(1, len(con_lesion) // 3)), random_state=0)
    usadas = {p: 0 for p in PARTES.values()}
    for _, f in pd.concat([con_lesion, normales]).iterrows():
        parte = PARTES[f["conjunto"]]
        base = os.path.splitext(f["imagen"])[0]
        img = Image.open(f["ruta"]).convert("RGB")
        w, h = img.size
        cajas = []
        if f["clase"] != "normal":
            if f.get("origen") == "clinica":          # caso corregido por el médico en Orthosync
                cajas = cajas_yolo(f.get("etiquetas_yolo"), w, h)
            else:
                cajas = cajas_de_anotacion(os.path.join(dir_anot, base + ".json"))
            if not cajas:
                continue
        d_img = os.path.join(DIR_YOLO, "images", parte); d_lab = os.path.join(DIR_YOLO, "labels", parte)
        os.makedirs(d_img, exist_ok=True); os.makedirs(d_lab, exist_ok=True)
        if max(w, h) > lado_max:
            e = lado_max / max(w, h)
            img = img.resize((round(w * e), round(h * e)), Image.BILINEAR)
        img.save(os.path.join(d_img, base + ".jpg"), quality=92)
        with open(os.path.join(d_lab, base + ".txt"), "w") as t:
            for x1, y1, x2, y2 in cajas:
                x1, x2 = max(0, min(x1, w)), max(0, min(x2, w)); y1, y2 = max(0, min(y1, h)), max(0, min(y2, h))
                if x2 - x1 < 2 or y2 - y1 < 2:
                    continue
                t.write(f"0 {(x1 + x2) / 2 / w:.6f} {(y1 + y2) / 2 / h:.6f} {(x2 - x1) / w:.6f} {(y2 - y1) / h:.6f}\n")
        usadas[parte] += 1
    for p in PARTES.values():
        os.makedirs(os.path.join(DIR_YOLO, "images", p), exist_ok=True)
    ruta_yaml = os.path.join(DIR_YOLO, "datos.yaml")
    with open(ruta_yaml, "w", encoding="utf-8") as f:
        f.write(f"path: {DIR_YOLO.replace(os.sep, '/')}\ntrain: images/train\nval: images/val\ntest: images/test\n"
                "names:\n  0: lesion\n")
    print("Imágenes para el detector:", usadas)
    if usadas["train"] == 0 or usadas["val"] == 0:
        raise SystemExit("No se encontraron anotaciones de cuadros; no se puede entrenar el detector.")
    return ruta_yaml


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epocas", type=int, default=0)
    ap.add_argument("--tam", type=int, default=0)
    ap.add_argument("--lote", type=int, default=16)
    ap.add_argument("--base", default="", help="Modelo YOLO de partida (por defecto: yolo11s con GPU, yolo11n sin GPU)")
    a = ap.parse_args()

    from ultralytics import YOLO
    disp = dispositivo(); gpu = disp == "cuda"
    # Con GPU: modelo más grande, imágenes más grandes y más épocas (las lesiones pequeñas se ven mejor)
    epocas = a.epocas or (150 if gpu else 30)
    tam = a.tam or (1024 if gpu else 512)
    base = a.base or ("yolo11s.pt" if gpu else "yolo11n.pt")
    lote = a.lote if a.lote != 16 or not gpu else 8
    print(f"=== Detector YOLO ({base}) | dispositivo={disp} | épocas={epocas} | imagen={tam}px ===")

    ruta_yaml = construir_dataset(lado_max=tam)
    modelo = YOLO(base)
    modelo.train(data=ruta_yaml, epochs=epocas, imgsz=tam, batch=lote, device=0 if gpu else "cpu",
                 project=DIR_RESULTADOS, name="detector", exist_ok=True, patience=30, cos_lr=True,
                 workers=0 if os.name == "nt" else 2, seed=0, fliplr=0.5, mosaic=0.5, verbose=False)
    mejor = str(modelo.trainer.best)
    os.makedirs(DIR_MODELOS, exist_ok=True)
    shutil.copy(mejor, MODELO_DETECTOR)

    r = YOLO(MODELO_DETECTOR).val(data=ruta_yaml, split="test", imgsz=tam, device=0 if gpu else "cpu",
                                  project=DIR_RESULTADOS, name="detector_prueba", exist_ok=True,
                                  workers=0, verbose=False)
    m = {"precision": float(r.box.mp), "sensibilidad": float(r.box.mr),
         "mAP50": float(r.box.map50), "mAP50_95": float(r.box.map), "tam": tam, "base": base}
    with open(os.path.join(DIR_RESULTADOS, "metricas_detector.json"), "w", encoding="utf-8") as f:
        json.dump(m, f, indent=2)
    print("\n----- Resultados del detector en PRUEBA -----")
    print(f"mAP50={m['mAP50']:.3f}  mAP50-95={m['mAP50_95']:.3f}  "
          f"Precisión={m['precision']:.1%}  Sensibilidad={m['sensibilidad']:.1%}")
    print("Modelo guardado en", MODELO_DETECTOR)


if __name__ == "__main__":
    main()
