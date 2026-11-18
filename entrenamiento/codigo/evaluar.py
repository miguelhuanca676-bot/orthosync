"""Paso 5: evalúa el sistema completo en el conjunto de PRUEBA y genera
las métricas y figuras para la tesis (carpeta resultados/).

    python evaluar.py
"""
import json, os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, roc_auc_score, roc_curve

from nucleo import DIR_RESULTADOS, RUTA_DIVISION, Sistema, leer_imagen, leer_json


def intervalo_auc(y, p, n=1000):
    """Intervalo de confianza del 95 % del AUC por remuestreo (bootstrap)."""
    rng = np.random.default_rng(0); vals = []
    for _ in range(n):
        i = rng.integers(0, len(y), len(y))
        if len(set(y[i])) == 2:
            vals.append(roc_auc_score(y[i], p[i]))
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))] if vals else [None, None]


def binaria(y, p, umbral):
    vn, fp, fn, vp = confusion_matrix(y, p >= umbral, labels=[0, 1]).ravel()
    return {
        "n": int(len(y)), "positivos": int(y.sum()), "umbral": float(umbral),
        "auc": float(roc_auc_score(y, p)), "auc_ic95": intervalo_auc(y, p),
        "sensibilidad": float(vp / max(vp + fn, 1)), "especificidad": float(vn / max(vn + fp, 1)),
        "vpp": float(vp / max(vp + fp, 1)), "vpn": float(vn / max(vn + fn, 1)),
        "exactitud": float((vp + vn) / len(y)),
        "f1": float(2 * vp / max(2 * vp + fp + fn, 1)),
        "matriz": {"VN": int(vn), "FP": int(fp), "FN": int(fn), "VP": int(vp)},
    }


def dibujar_matriz(m, etiquetas, titulo, ruta):
    fig, ax = plt.subplots(figsize=(1.6 + 1.3 * len(etiquetas), 1.2 + 1.2 * len(etiquetas)))
    ax.imshow(m, cmap="Blues")
    for i in range(m.shape[0]):
        for j in range(m.shape[1]):
            ax.text(j, i, int(m[i, j]), ha="center", va="center",
                    color="white" if m[i, j] > m.max() / 2 else "black", fontsize=13)
    ax.set_xticks(range(len(etiquetas)), etiquetas); ax.set_yticks(range(len(etiquetas)), etiquetas)
    ax.set_xlabel("Predicción del sistema"); ax.set_ylabel("Clase real"); ax.set_title(titulo)
    fig.tight_layout(); fig.savefig(ruta, dpi=160); plt.close(fig)


def main():
    os.makedirs(DIR_RESULTADOS, exist_ok=True)
    sistema = Sistema()
    df = pd.read_csv(RUTA_DIVISION)
    df = df[df.conjunto == "prueba"].reset_index(drop=True)
    print(f"Evaluando {len(df)} imágenes de prueba...")
    pt, pm = [], []
    for i, r in enumerate(df["ruta"]):
        a, b = sistema.probabilidades(leer_imagen(r))
        pt.append(a); pm.append(np.nan if b is None else b)
        if (i + 1) % 100 == 0:
            print(f"  {i + 1}/{len(df)}", flush=True)
    df["p_tumor"], df["p_maligno"] = pt, pm
    df.drop(columns=["ruta"]).to_csv(os.path.join(DIR_RESULTADOS, "predicciones_prueba.csv"), index=False)

    res, curvas = {}, []
    # Etapa 1: normal vs. lesión
    y = (df["clase"] != "normal").astype(int).values
    res["etapa1_normal_vs_lesion"] = binaria(y, df["p_tumor"].values, sistema.umbral_tumor)
    curvas.append(("Normal vs. lesión", y, df["p_tumor"].values))
    m = res["etapa1_normal_vs_lesion"]["matriz"]
    dibujar_matriz(np.array([[m["VN"], m["FP"]], [m["FN"], m["VP"]]]), ["normal", "lesión"],
                   "Etapa 1: normal vs. lesión", os.path.join(DIR_RESULTADOS, "matriz_etapa1.png"))

    # Etapa 3: benigno vs. maligno (sobre las lesiones reales)
    les = df[df["clase"].isin(["benigno", "maligno"])]
    if sistema.red_mal is not None and les["clase"].nunique() == 2:
        y3 = (les["clase"] == "maligno").astype(int).values
        res["etapa3_benigno_vs_maligno"] = binaria(y3, les["p_maligno"].values, sistema.umbral_malignidad)
        curvas.append(("Benigno vs. maligno", y3, les["p_maligno"].values))
        m = res["etapa3_benigno_vs_maligno"]["matriz"]
        dibujar_matriz(np.array([[m["VN"], m["FP"]], [m["FN"], m["VP"]]]), ["benigno", "maligno"],
                       "Etapa 3: benigno vs. maligno", os.path.join(DIR_RESULTADOS, "matriz_etapa3.png"))

        # Sistema completo: lo que vería el médico (3 clases)
        tres = df[df["clase"].isin(["normal", "benigno", "maligno"])]
        pred = np.where(tres["p_tumor"] < sistema.umbral_tumor, "normal",
                        np.where(tres["p_maligno"] >= sistema.umbral_malignidad, "maligno", "benigno"))
        orden = ["normal", "benigno", "maligno"]
        mc = confusion_matrix(tres["clase"], pred, labels=orden)
        res["sistema_completo_3_clases"] = {
            "exactitud": float(np.trace(mc) / mc.sum()),
            "sensibilidad_por_clase": {c: float(mc[i, i] / max(mc[i].sum(), 1)) for i, c in enumerate(orden)},
            "matriz": mc.tolist(), "orden": orden,
        }
        dibujar_matriz(mc, orden, "Sistema completo", os.path.join(DIR_RESULTADOS, "matriz_sistema.png"))

    det = leer_json(os.path.join(DIR_RESULTADOS, "metricas_detector.json"))
    if det:
        res["etapa2_detector"] = det

    fig, ax = plt.subplots(figsize=(5, 4.5))
    for nombre, yy, pp in curvas:
        fpr, tpr, _ = roc_curve(yy, pp)
        ax.plot(fpr, tpr, lw=2, label=f"{nombre} (AUC = {roc_auc_score(yy, pp):.3f})")
    ax.plot([0, 1], [0, 1], "--", color="gray", lw=1)
    ax.set_xlabel("1 - Especificidad"); ax.set_ylabel("Sensibilidad"); ax.set_title("Curvas ROC (conjunto de prueba)")
    ax.legend(loc="lower right"); fig.tight_layout()
    fig.savefig(os.path.join(DIR_RESULTADOS, "curvas_roc.png"), dpi=160); plt.close(fig)

    # puntos de las curvas ROC (reducidos) para dibujarlas en la página de validación
    res["curvas_roc"] = {}
    for nombre, yy, pp in curvas:
        fpr, tpr, _ = roc_curve(yy, pp)
        idx = np.unique(np.linspace(0, len(fpr) - 1, min(len(fpr), 60)).astype(int))
        res["curvas_roc"][nombre] = [[round(float(fpr[i]), 4), round(float(tpr[i]), 4)] for i in idx]

    with open(os.path.join(DIR_RESULTADOS, "metricas.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)

    lineas = ["RESULTADOS EN EL CONJUNTO DE PRUEBA", "=" * 36]
    for clave, titulo in (("etapa1_normal_vs_lesion", "Etapa 1: normal vs. lesión"),
                          ("etapa3_benigno_vs_maligno", "Etapa 3: benigno vs. maligno")):
        if clave in res:
            m = res[clave]
            lineas += ["", titulo, f"  Imágenes: {m['n']} (positivos: {m['positivos']})",
                       f"  AUC: {m['auc']:.3f}  (IC 95 %: {m['auc_ic95'][0]:.3f} - {m['auc_ic95'][1]:.3f})",
                       f"  Sensibilidad: {m['sensibilidad']:.1%}   Especificidad: {m['especificidad']:.1%}",
                       f"  VPP: {m['vpp']:.1%}   VPN: {m['vpn']:.1%}   F1: {m['f1']:.3f}   Exactitud: {m['exactitud']:.1%}",
                       f"  Umbral: {m['umbral']:.2f}   Matriz: {m['matriz']}"]
    if det:
        lineas += ["", "Etapa 2: detector (YOLO)",
                   f"  mAP50: {det['mAP50']:.3f}   mAP50-95: {det['mAP50_95']:.3f}",
                   f"  Precisión: {det['precision']:.1%}   Sensibilidad: {det['sensibilidad']:.1%}"]
    if "sistema_completo_3_clases" in res:
        s = res["sistema_completo_3_clases"]
        lineas += ["", "Sistema completo (normal / benigno / maligno)", f"  Exactitud: {s['exactitud']:.1%}",
                   "  Sensibilidad por clase: " + ", ".join(f"{k} {v:.1%}" for k, v in s["sensibilidad_por_clase"].items())]
    texto = "\n".join(lineas)
    with open(os.path.join(DIR_RESULTADOS, "informe_resultados.txt"), "w", encoding="utf-8") as f:
        f.write(texto + "\n")
    print("\n" + texto)
    print(f"\nFiguras y métricas guardadas en {DIR_RESULTADOS}")


if __name__ == "__main__":
    main()
