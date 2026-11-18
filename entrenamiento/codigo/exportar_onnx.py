"""Convierte los modelos entrenados a ONNX, el formato ligero que usa el servidor web
(no necesita PyTorch instalado). Deja todo en modelos/servidor/.

    python exportar_onnx.py
"""
import json, os, shutil, warnings

import numpy as np
import torch
import torch.nn as nn

from nucleo import (DIR_MODELOS, DIR_RESULTADOS, MODELO_ASPECTO, MODELO_DETECTOR, MODELO_HUESO, MODELO_MALIGNIDAD,
                    MODELO_TUMOR, cargar_clasificador, leer_json)

DIR_SERVIDOR = os.path.join(DIR_MODELOS, "servidor")


class ConMapa(nn.Module):
    """Devuelve las probabilidades y, además, el mapa de activación de la clase positiva
    (equivalente a Grad-CAM en una ResNet), para dibujar el mapa de calor sin PyTorch."""

    def __init__(self, red):
        super().__init__(); self.red = red

    def forward(self, x):
        r = self.red
        f = r.layer4(r.layer3(r.layer2(r.layer1(r.maxpool(r.relu(r.bn1(r.conv1(x))))))))
        logits = r.fc(torch.flatten(r.avgpool(f), 1))
        mapa = torch.relu((f * r.fc.weight[1].view(1, -1, 1, 1)).sum(1))
        return torch.softmax(logits, 1), mapa


class Multiclase(nn.Module):
    def __init__(self, red):
        super().__init__(); self.red = red

    def forward(self, x):
        return torch.softmax(self.red(x), 1)


class Multietiqueta(nn.Module):
    def __init__(self, red):
        super().__init__(); self.red = red

    def forward(self, x):
        return torch.sigmoid(self.red(x))


def exportar(modulo, tam, destino, salidas):
    modulo.eval()
    x = torch.randn(1, 3, tam, tam)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            torch.onnx.export(modulo, (x,), destino, input_names=["imagen"], output_names=salidas,
                              opset_version=17, dynamo=False)
        except Exception:  # versiones de PyTorch con otro exportador por defecto
            torch.onnx.export(modulo, (x,), destino, input_names=["imagen"], output_names=salidas)
    import onnxruntime as ort
    s = ort.InferenceSession(destino, providers=["CPUExecutionProvider"])
    con_onnx = s.run(None, {"imagen": x.numpy()})
    with torch.no_grad():
        con_torch = modulo(x)
    con_torch = con_torch if isinstance(con_torch, tuple) else (con_torch,)
    dif = max(float(np.abs(a - b.numpy()).max()) for a, b in zip(con_onnx, con_torch))
    print(f"  {os.path.basename(destino)}: {os.path.getsize(destino) / 1e6:.1f} MB, diferencia máxima con PyTorch {dif:.2e}")
    if dif > 1e-3:
        raise SystemExit("La versión ONNX no coincide con el modelo original.")


def main():
    os.makedirs(DIR_SERVIDOR, exist_ok=True)
    info = {"modelos": {}}
    for clave, ruta in (("tumor", MODELO_TUMOR), ("malignidad", MODELO_MALIGNIDAD)):
        if os.path.exists(ruta):
            red, d = cargar_clasificador(ruta)
            exportar(ConMapa(red), d["tam"], os.path.join(DIR_SERVIDOR, f"{clave}.onnx"), ["probabilidades", "mapa"])
            info["modelos"][clave] = {"archivo": f"{clave}.onnx", "tam": d["tam"], "clases": d["clases"],
                                      "umbral": d.get("umbral", 0.5), "metricas_prueba": d.get("metricas_prueba")}
    if os.path.exists(MODELO_HUESO):
        red, d = cargar_clasificador(MODELO_HUESO)
        exportar(Multietiqueta(red), d["tam"], os.path.join(DIR_SERVIDOR, "hueso.onnx"), ["probabilidades"])
        info["modelos"]["hueso"] = {"archivo": "hueso.onnx", "tam": d["tam"], "clases": d["clases"],
                                    "metricas_prueba": d.get("metricas_prueba")}
    if os.path.exists(MODELO_ASPECTO):
        red, d = cargar_clasificador(MODELO_ASPECTO)
        exportar(Multiclase(red), d["tam"], os.path.join(DIR_SERVIDOR, "aspecto.onnx"), ["probabilidades"])
        info["modelos"]["aspecto"] = {"archivo": "aspecto.onnx", "tam": d["tam"], "clases": d["clases"],
                                      "metricas_prueba": d.get("metricas_prueba")}
    if os.path.exists(MODELO_DETECTOR):
        from ultralytics import YOLO
        tam = int((leer_json(os.path.join(DIR_RESULTADOS, "metricas_detector.json")) or {}).get("tam", 640))
        salida = YOLO(MODELO_DETECTOR).export(format="onnx", imgsz=tam, opset=17, simplify=False, verbose=False)
        shutil.move(str(salida), os.path.join(DIR_SERVIDOR, "detector.onnx"))
        print(f"  detector.onnx: {os.path.getsize(os.path.join(DIR_SERVIDOR, 'detector.onnx')) / 1e6:.1f} MB")
        info["modelos"]["detector"] = {"archivo": "detector.onnx", "tam": tam, "clases": ["lesion"],
                                       "metricas_prueba": leer_json(os.path.join(DIR_RESULTADOS, "metricas_detector.json"))}
    info["preprocesamiento"] = {"clahe": {"clip": 2.0, "rejilla": 8}, "media": [0.485, 0.456, 0.406],
                                "desviacion": [0.229, 0.224, 0.225],
                                "nota": "escala de grises -> CLAHE -> redimensionar con relleno negro -> RGB -> normalizar"}
    info["evaluacion"] = leer_json(os.path.join(DIR_RESULTADOS, "metricas.json"))
    with open(os.path.join(DIR_SERVIDOR, "info.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2, ensure_ascii=False)
    print("Modelos para el servidor en", DIR_SERVIDOR, "->", sorted(os.listdir(DIR_SERVIDOR)))


if __name__ == "__main__":
    main()
