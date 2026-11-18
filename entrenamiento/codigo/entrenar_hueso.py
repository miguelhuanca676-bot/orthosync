"""Entrena el clasificador que reconoce qué hueso(s) aparecen en la radiografía.
Sirve para proponer el modelo 3D; el médico siempre confirma.

    python entrenar_hueso.py
"""
import argparse, json, os, random, time

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from PIL import Image
from sklearn.metrics import roc_auc_score
from torch.utils.data import DataLoader, Dataset

from nucleo import (DIR_MODELOS, DIR_RESULTADOS, MODELO_HUESO, RUTA_DIVISION, asegurar_cache,
                    crear_modelo, dispositivo, transformacion)

MIN_EJEMPLOS = 20  # un hueso con menos imágenes de entrenamiento que esto no se aprende


class Radiografias(Dataset):
    def __init__(self, rutas, etiquetas, entrenamiento):
        self.rutas, self.y = list(rutas), np.asarray(etiquetas, dtype=np.float32)
        self.t = transformacion(entrenamiento)

    def __len__(self):
        return len(self.rutas)

    def __getitem__(self, i):
        return self.t(Image.open(self.rutas[i]).convert("RGB")), torch.from_numpy(self.y[i])


def predecir(red, cargador, disp):
    red.eval(); probs, reales = [], []
    with torch.no_grad():
        for x, y in cargador:
            probs.append(torch.sigmoid(red(x.to(disp))).cpu().numpy()); reales.append(y.numpy())
    return np.concatenate(reales), np.concatenate(probs)


def metricas(reales, probs):
    aucs = [roc_auc_score(reales[:, j], probs[:, j]) for j in range(reales.shape[1])
            if 0 < reales[:, j].sum() < len(reales)]
    acierto = float(np.mean(reales[np.arange(len(reales)), probs.argmax(1)] == 1))
    return {"auc_promedio": float(np.mean(aucs)) if aucs else float("nan"), "acierto_hueso_principal": acierto}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epocas", type=int, default=0)
    ap.add_argument("--tam", type=int, default=0)
    ap.add_argument("--lote", type=int, default=32)
    ap.add_argument("--sin-preentrenar", action="store_true")
    a = ap.parse_args()

    disp = dispositivo(); gpu = disp == "cuda"
    epocas = a.epocas or (12 if gpu else 5)
    tam = a.tam or (384 if gpu else 224)
    random.seed(0); np.random.seed(0); torch.manual_seed(0)
    print(f"=== Clasificador de hueso | dispositivo={disp} | épocas={epocas} | imagen={tam}px ===")

    df = pd.read_csv(RUTA_DIVISION)
    cols = [c for c in df.columns if c.startswith("hueso_")]
    entr0 = df[df.conjunto == "entrenamiento"]
    cols = [c for c in cols if entr0[c].sum() >= MIN_EJEMPLOS]
    if len(cols) < 2:
        print("AVISO: el dataset no trae suficientes etiquetas de hueso; se omite este modelo.")
        return
    df = df[df[cols].sum(axis=1) > 0].reset_index(drop=True)
    clases = [c.replace("hueso_", "") for c in cols]
    print("Huesos:", {k: int(df[c].sum()) for k, c in zip(clases, cols)})

    df["cache"] = asegurar_cache(df["ruta"], tam)
    entr, val, prueba = (df[df.conjunto == c] for c in ("entrenamiento", "validacion", "prueba"))
    mk = lambda d, e: DataLoader(Radiografias(d.cache, d[cols].values, e), batch_size=a.lote, shuffle=e, num_workers=0)
    c_entr, c_val, c_prueba = mk(entr, True), mk(val, False), mk(prueba, False)

    red = crear_modelo(len(cols), preentrenado=not a.sin_preentrenar).to(disp)
    pos = entr[cols].sum().values.astype(np.float32)
    peso = torch.tensor(np.clip((len(entr) - pos) / np.maximum(pos, 1), 1, 20), device=disp)
    perdida = nn.BCEWithLogitsLoss(pos_weight=peso)
    opt = torch.optim.AdamW(red.parameters(), lr=3e-4, weight_decay=1e-4)
    plan = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=3e-4, total_steps=epocas * len(c_entr))

    os.makedirs(DIR_MODELOS, exist_ok=True); os.makedirs(DIR_RESULTADOS, exist_ok=True)
    mejor, historial = -1, []
    for ep in range(1, epocas + 1):
        red.train(); t0 = time.time(); suma = 0
        for x, y in c_entr:
            x, y = x.to(disp), y.to(disp)
            opt.zero_grad()
            l = perdida(red(x), y)
            l.backward(); opt.step(); plan.step(); suma += l.item()
        m = metricas(*predecir(red, c_val, disp))
        historial.append({"epoca": ep, "perdida": suma / len(c_entr), **m})
        print(f"Época {ep}/{epocas}  pérdida={suma / len(c_entr):.3f}  AUC val={m['auc_promedio']:.3f}  "
              f"acierto={m['acierto_hueso_principal']:.1%}  ({time.time() - t0:.0f}s)", flush=True)
        if m["acierto_hueso_principal"] > mejor:
            mejor = m["acierto_hueso_principal"]
            torch.save({"pesos": red.state_dict(), "clases": clases, "tam": tam, "tarea": "hueso"}, MODELO_HUESO)

    guardado = torch.load(MODELO_HUESO, map_location=disp, weights_only=False)
    red.load_state_dict(guardado["pesos"])
    final = metricas(*predecir(red, c_prueba, disp))
    guardado.update({"metricas_prueba": final, "historial": historial})
    torch.save(guardado, MODELO_HUESO)
    with open(os.path.join(DIR_RESULTADOS, "entrenamiento_hueso.json"), "w", encoding="utf-8") as f:
        json.dump({"prueba": final, "clases": clases, "historial": historial}, f, indent=2, ensure_ascii=False)
    print(f"\n----- Resultados en PRUEBA (hueso) -----\nAUC promedio={final['auc_promedio']:.3f}  "
          f"Acierto del hueso principal={final['acierto_hueso_principal']:.1%}")
    print("Modelo guardado en", MODELO_HUESO)


if __name__ == "__main__":
    main()
