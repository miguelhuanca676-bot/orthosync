"""Paso 2 y 3: entrena un clasificador ResNet18.

    python entrenar_clasificador.py --tarea tumor        (normal vs. lesión)
    python entrenar_clasificador.py --tarea malignidad   (benigno vs. maligno)
"""
import argparse, json, os, random, time

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from PIL import Image
from sklearn.metrics import confusion_matrix, roc_auc_score, roc_curve
from torch.utils.data import DataLoader, Dataset

from nucleo import (DIR_MODELOS, DIR_RESULTADOS, MODELO_MALIGNIDAD, MODELO_TUMOR, RUTA_DIVISION,
                    asegurar_cache, crear_modelo, dispositivo, transformacion)

TAREAS = {
    "tumor": {"clases": ["normal", "lesion"], "salida": MODELO_TUMOR},
    "malignidad": {"clases": ["benigno", "maligno"], "salida": MODELO_MALIGNIDAD},
}


class Radiografias(Dataset):
    def __init__(self, rutas, etiquetas, entrenamiento):
        self.rutas, self.etiquetas = list(rutas), [int(e) for e in etiquetas]
        self.t = transformacion(entrenamiento)

    def __len__(self):
        return len(self.rutas)

    def __getitem__(self, i):
        return self.t(Image.open(self.rutas[i]).convert("RGB")), self.etiquetas[i]


def metricas(reales, probs, umbral=None):
    reales, probs = np.asarray(reales), np.asarray(probs)
    if umbral is None:  # umbral que mejor separa las clases (índice de Youden)
        fpr, tpr, umbrales = roc_curve(reales, probs)
        umbral = float(np.clip(umbrales[np.argmax(tpr - fpr)], 0.01, 0.99))
    vn, fp, fn, vp = confusion_matrix(reales, probs >= umbral, labels=[0, 1]).ravel()
    return {
        "umbral": umbral,
        "auc": float(roc_auc_score(reales, probs)) if len(set(reales)) > 1 else float("nan"),
        "sensibilidad": float(vp / max(vp + fn, 1)),
        "especificidad": float(vn / max(vn + fp, 1)),
        "exactitud": float((vp + vn) / max(len(reales), 1)),
        "matriz": {"VN": int(vn), "FP": int(fp), "FN": int(fn), "VP": int(vp)},
    }


def predecir(red, cargador, disp):
    red.eval(); probs, reales = [], []
    with torch.no_grad():
        for x, y in cargador:
            probs += list(torch.softmax(red(x.to(disp)), 1)[:, 1].cpu().numpy())
            reales += list(y.numpy())
    return np.array(reales), np.array(probs)


def tabla_de_tarea(tarea):
    if not os.path.exists(RUTA_DIVISION):
        raise SystemExit("Falta la división de datos. Ejecuta primero preparar_datos.py")
    df = pd.read_csv(RUTA_DIVISION)
    if tarea == "tumor":
        df["y"] = (df["clase"] != "normal").astype(int)
    else:
        df = df[df["clase"].isin(["benigno", "maligno"])].copy()
        df["y"] = (df["clase"] == "maligno").astype(int)
    return df.reset_index(drop=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tarea", choices=list(TAREAS), required=True)
    ap.add_argument("--epocas", type=int, default=0)
    ap.add_argument("--tam", type=int, default=0)
    ap.add_argument("--lote", type=int, default=32)
    ap.add_argument("--sin-preentrenar", action="store_true")
    a = ap.parse_args()

    disp = dispositivo()
    gpu = disp == "cuda"
    epocas = a.epocas or ({"tumor": 15, "malignidad": 20} if gpu else {"tumor": 6, "malignidad": 10})[a.tarea]
    tam = a.tam or (384 if gpu else 224)
    random.seed(0); np.random.seed(0); torch.manual_seed(0)
    print(f"=== Clasificador '{a.tarea}' | dispositivo={disp} | épocas={epocas} | imagen={tam}px ===")

    df = tabla_de_tarea(a.tarea)
    df["cache"] = asegurar_cache(df["ruta"], tam)
    entr, val, prueba = (df[df.conjunto == c] for c in ("entrenamiento", "validacion", "prueba"))
    clases = TAREAS[a.tarea]["clases"]
    for nombre, d in (("Entrenamiento", entr), ("Validación", val), ("Prueba", prueba)):
        print(f"{nombre:14s}: {len(d):5d}  ({clases[0]}={sum(d.y == 0)}, {clases[1]}={sum(d.y == 1)})")
    if entr.y.nunique() < 2 or val.y.nunique() < 2:
        raise SystemExit("No hay imágenes de las dos clases; no se puede entrenar esta tarea.")

    mk = lambda d, e: DataLoader(Radiografias(d.cache, d.y, e), batch_size=a.lote, shuffle=e, num_workers=0)
    c_entr, c_val, c_prueba = mk(entr, True), mk(val, False), mk(prueba, False)

    red = crear_modelo(2, preentrenado=not a.sin_preentrenar).to(disp)
    conteo = np.bincount(entr.y, minlength=2)
    pesos = torch.tensor(len(entr) / (2 * conteo), dtype=torch.float32, device=disp)  # contra el desbalance
    perdida = nn.CrossEntropyLoss(weight=pesos)
    opt = torch.optim.AdamW(red.parameters(), lr=3e-4, weight_decay=1e-4)
    plan = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=3e-4, total_steps=epocas * len(c_entr))

    os.makedirs(DIR_MODELOS, exist_ok=True); os.makedirs(DIR_RESULTADOS, exist_ok=True)
    salida = TAREAS[a.tarea]["salida"]
    mejor, historial = -1, []
    for ep in range(1, epocas + 1):
        red.train(); t0 = time.time(); suma = 0
        for i, (x, y) in enumerate(c_entr):
            x, y = x.to(disp), y.to(disp)
            opt.zero_grad()
            l = perdida(red(x), y)
            l.backward(); opt.step(); plan.step()
            suma += l.item()
            if (i + 1) % 10 == 0:
                print(f"\r  época {ep}: lote {i + 1}/{len(c_entr)}", end="", flush=True)
        m = metricas(*predecir(red, c_val, disp))
        historial.append({"epoca": ep, "perdida": suma / len(c_entr), **m})
        print(f"\rÉpoca {ep}/{epocas}  pérdida={suma / len(c_entr):.3f}  AUC val={m['auc']:.3f}  "
              f"sens={m['sensibilidad']:.2f}  espec={m['especificidad']:.2f}  ({time.time() - t0:.0f}s)", flush=True)
        if m["auc"] > mejor:
            mejor = m["auc"]
            torch.save({"pesos": red.state_dict(), "clases": clases, "tam": tam, "tarea": a.tarea,
                        "umbral": m["umbral"]}, salida)

    guardado = torch.load(salida, map_location=disp, weights_only=False)
    red.load_state_dict(guardado["pesos"])
    final = metricas(*predecir(red, c_prueba, disp), umbral=guardado["umbral"])
    guardado.update({"metricas_prueba": final, "historial": historial,
                     "n": {"entrenamiento": len(entr), "validacion": len(val), "prueba": len(prueba)}})
    torch.save(guardado, salida)
    with open(os.path.join(DIR_RESULTADOS, f"entrenamiento_{a.tarea}.json"), "w", encoding="utf-8") as f:
        json.dump({"prueba": final, "historial": historial}, f, indent=2, ensure_ascii=False)

    print(f"\n----- Resultados en PRUEBA ({a.tarea}) -----")
    print(f"Umbral (elegido en validación): {guardado['umbral']:.2f}")
    print(f"AUC={final['auc']:.3f}  Sensibilidad={final['sensibilidad']:.1%}  "
          f"Especificidad={final['especificidad']:.1%}  Exactitud={final['exactitud']:.1%}")
    print("Matriz:", final["matriz"])
    print("Modelo guardado en", salida)


if __name__ == "__main__":
    main()
