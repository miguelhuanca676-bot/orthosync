"""Entrena el clasificador del ASPECTO radiológico de la lesión, que decide cómo se dibuja en el 3D:
    crecimiento (sobresale del hueso), litica (hueco) o mixta (destruye hueso y forma masa).
Las etiquetas salen del tipo de tumor de BTXRD (ver ASPECTOS en nucleo.py). El médico siempre confirma.

    python entrenar_aspecto.py
"""
import argparse, json, os, random, time

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from PIL import Image
from sklearn.metrics import balanced_accuracy_score, confusion_matrix
from torch.utils.data import DataLoader, Dataset

from nucleo import (ASPECTOS, DIR_MODELOS, DIR_RESULTADOS, MODELO_ASPECTO, RUTA_DIVISION, asegurar_cache,
                    crear_modelo, dispositivo, transformacion)

MIN_EJEMPLOS = 15


class Radiografias(Dataset):
    def __init__(self, rutas, etiquetas, entrenamiento):
        self.rutas, self.y = list(rutas), np.asarray(etiquetas, dtype=np.int64)
        self.t = transformacion(entrenamiento)

    def __len__(self):
        return len(self.rutas)

    def __getitem__(self, i):
        return self.t(Image.open(self.rutas[i]).convert("RGB")), int(self.y[i])


def predecir(red, cargador, disp):
    red.eval(); probs, reales = [], []
    with torch.no_grad():
        for x, y in cargador:
            probs.append(torch.softmax(red(x.to(disp)), 1).cpu().numpy()); reales.append(y.numpy())
    return np.concatenate(reales), np.concatenate(probs)


def metricas(reales, probs, clases):
    pred = probs.argmax(1)
    mc = confusion_matrix(reales, pred, labels=list(range(len(clases))))
    return {"exactitud": float((pred == reales).mean()), "exactitud_balanceada": float(balanced_accuracy_score(reales, pred)),
            "sensibilidad_por_clase": {c: float(mc[i, i] / max(mc[i].sum(), 1)) for i, c in enumerate(clases)},
            "matriz": mc.tolist(), "orden": clases}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epocas", type=int, default=0)
    ap.add_argument("--tam", type=int, default=0)
    ap.add_argument("--lote", type=int, default=32)
    ap.add_argument("--sin-preentrenar", action="store_true")
    a = ap.parse_args()

    disp = dispositivo(); gpu = disp == "cuda"
    epocas = a.epocas or (20 if gpu else 6)
    tam = a.tam or (384 if gpu else 224)
    random.seed(0); np.random.seed(0); torch.manual_seed(0)
    print(f"=== Aspecto de la lesión | dispositivo={disp} | épocas={epocas} | imagen={tam}px ===")

    df = pd.read_csv(RUTA_DIVISION)
    if "aspecto" not in df.columns:
        print("AVISO: vuelve a ejecutar preparar_datos.py (falta la columna 'aspecto'); se omite este modelo."); return
    df = df[df["aspecto"].fillna("").isin(ASPECTOS)].reset_index(drop=True)
    entr0 = df[df.conjunto == "entrenamiento"]
    clases = [c for c in ASPECTOS if (entr0["aspecto"] == c).sum() >= MIN_EJEMPLOS]
    if len(clases) < 2:
        print("AVISO: no hay suficientes lesiones con tipo conocido; se omite este modelo."); return
    df = df[df["aspecto"].isin(clases)].reset_index(drop=True)
    df["y"] = df["aspecto"].map({c: i for i, c in enumerate(clases)})
    print("Imágenes por aspecto:", df.groupby(["aspecto", "conjunto"]).size().unstack(fill_value=0).to_dict("index"))

    df["cache"] = asegurar_cache(df["ruta"], tam)
    entr, val, prueba = (df[df.conjunto == c] for c in ("entrenamiento", "validacion", "prueba"))
    mk = lambda d, e: DataLoader(Radiografias(d.cache, d.y, e), batch_size=a.lote, shuffle=e, num_workers=0)
    c_entr, c_val, c_prueba = mk(entr, True), mk(val, False), mk(prueba, False)

    red = crear_modelo(len(clases), preentrenado=not a.sin_preentrenar).to(disp)
    cuenta = np.bincount(entr.y, minlength=len(clases)).astype(np.float32)
    peso = torch.tensor(cuenta.sum() / (len(clases) * np.maximum(cuenta, 1)), device=disp)   # clases raras pesan más
    perdida = nn.CrossEntropyLoss(weight=peso, label_smoothing=0.05)
    opt = torch.optim.AdamW(red.parameters(), lr=3e-4, weight_decay=1e-4)
    plan = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=3e-4, total_steps=epocas * len(c_entr))

    os.makedirs(DIR_MODELOS, exist_ok=True); os.makedirs(DIR_RESULTADOS, exist_ok=True)
    mejor, historial = -1, []
    for ep in range(1, epocas + 1):
        red.train(); t0 = time.time(); suma = 0
        for x, y in c_entr:
            x, y = x.to(disp), y.to(disp)
            opt.zero_grad(); l = perdida(red(x), y); l.backward(); opt.step(); plan.step(); suma += l.item()
        m = metricas(*predecir(red, c_val, disp), clases)
        historial.append({"epoca": ep, "perdida": suma / len(c_entr), "exactitud_balanceada": m["exactitud_balanceada"]})
        print(f"Época {ep}/{epocas}  pérdida={suma / len(c_entr):.3f}  exactitud balanceada val={m['exactitud_balanceada']:.1%}  "
              f"({time.time() - t0:.0f}s)", flush=True)
        if m["exactitud_balanceada"] > mejor:
            mejor = m["exactitud_balanceada"]
            torch.save({"pesos": red.state_dict(), "clases": clases, "tam": tam, "tarea": "aspecto"}, MODELO_ASPECTO)

    guardado = torch.load(MODELO_ASPECTO, map_location=disp, weights_only=False)
    red.load_state_dict(guardado["pesos"])
    final = metricas(*predecir(red, c_prueba, disp), clases)
    guardado.update({"metricas_prueba": final, "historial": historial}); torch.save(guardado, MODELO_ASPECTO)
    with open(os.path.join(DIR_RESULTADOS, "entrenamiento_aspecto.json"), "w", encoding="utf-8") as f:
        json.dump({"prueba": final, "clases": clases, "historial": historial}, f, indent=2, ensure_ascii=False)
    print(f"\n----- Resultados en PRUEBA (aspecto) -----\nExactitud={final['exactitud']:.1%}  "
          f"Exactitud balanceada={final['exactitud_balanceada']:.1%}  Por clase={final['sensibilidad_por_clase']}")
    print("Modelo guardado en", MODELO_ASPECTO)


if __name__ == "__main__":
    main()
