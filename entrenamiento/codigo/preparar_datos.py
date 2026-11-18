"""Paso 1: lee BTXRD, aplica el alcance del proyecto y divide en
entrenamiento / validación / prueba (la misma división para todos los modelos).

Uso:  python preparar_datos.py --datos "C:\\tesis\\BTXRD"
      python preparar_datos.py --datos ... --extra casos_clinica   (suma los casos corregidos exportados desde Orthosync)
"""
import argparse, glob, json, os, shutil

import pandas as pd
from sklearn.model_selection import train_test_split

from nucleo import ASPECTOS, DIR_PREPARADOS, HUESOS, RAIZ, RUTA_CONFIG, RUTA_DIVISION, buscar, columna


def casos_clinica(carpetas):
    """Casos valorados por el traumatólogo y exportados desde Orthosync (casos.csv + images/ + labels/).
    Se usan SOLO para entrenar: la prueba sigue siendo BTXRD, para que los resultados sean comparables."""
    filas = []
    for raiz in carpetas:
        for csv in glob.glob(os.path.join(raiz, "**", "casos.csv"), recursive=True):
            base = os.path.dirname(csv)
            for _, f in pd.read_csv(csv).iterrows():
                ruta = os.path.join(base, "images", f["imagen"])
                if not os.path.exists(ruta):
                    continue
                maligno = str(f.get("maligno", "")).strip()
                clase = "normal" if int(f["tumor"]) == 0 else ("maligno" if maligno in ("1", "1.0") else "benigno")
                lab = os.path.join(base, "labels", os.path.splitext(f["imagen"])[0] + ".txt")
                fila = {"imagen": "clinica_" + f["imagen"], "ruta": ruta, "clase": clase, "conjunto": "entrenamiento",
                        "etiquetas_yolo": lab if os.path.exists(lab) else "", "origen": "clinica"}
                h = str(f.get("hueso", "") or "")
                for clave in HUESOS:
                    fila["hueso_" + clave] = int(h == clave)
                filas.append(fila)
    if filas:
        print(f"Se suman {len(filas)} casos corregidos por el médico (solo para entrenamiento)")
    return pd.DataFrame(filas)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datos", required=True, help="Carpeta donde descomprimiste BTXRD")
    ap.add_argument("--max-imagenes", type=int, default=0, help="Usar solo N imágenes (prueba rápida)")
    ap.add_argument("--incluir-pelvis", action="store_true")
    ap.add_argument("--extra", nargs="*", default=[], help="Carpetas con casos exportados desde Orthosync")
    a = ap.parse_args()

    tabla = buscar(a.datos, "dataset.xlsx") or buscar(a.datos, "dataset.csv")
    dir_img = buscar(a.datos, "images", carpeta=True)
    dir_anot = buscar(a.datos, "Annotations", carpeta=True)
    if not tabla or not dir_img:
        raise SystemExit(f"No encuentro dataset.xlsx/csv o la carpeta images dentro de {a.datos}")
    df = pd.read_excel(tabla) if tabla.endswith(".xlsx") else pd.read_csv(tabla)

    c_img = columna(df, "image_id") or df.columns[0]
    c_tumor, c_ben, c_mal = columna(df, "tumor"), columna(df, "benign"), columna(df, "malignant")
    if c_tumor is None:
        raise SystemExit(f"No hay columna 'tumor'. Columnas: {list(df.columns)}")

    c_pelvis = columna(df, "pelvis")
    if c_pelvis and not a.incluir_pelvis:
        antes = len(df); df = df[df[c_pelvis] != 1]
        print(f"Se excluyen {antes - len(df)} imágenes de pelvis (fuera del alcance)")

    def clase(f):
        if c_mal and f[c_mal] == 1: return "maligno"
        if c_ben and f[c_ben] == 1: return "benigno"
        if f[c_tumor] == 1: return "tumor_sin_tipo"
        return "normal"

    df = df.copy()
    df["imagen"] = df[c_img].astype(str)
    df["ruta"] = df["imagen"].map(lambda n: os.path.join(dir_img, n))
    df = df[df["ruta"].map(os.path.exists)]
    df["clase"] = df.apply(clase, axis=1)
    if len(df) == 0:
        raise SystemExit("No se encontró ninguna imagen de la tabla dentro de la carpeta images.")

    if a.max_imagenes:
        n = max(a.max_imagenes // df["clase"].nunique(), 6)
        df = pd.concat([g.sample(min(len(g), n), random_state=0) for _, g in df.groupby("clase")])

    # 70 % entrenamiento / 15 % validación / 15 % prueba, manteniendo la proporción de clases
    entr, resto = train_test_split(df, test_size=0.30, stratify=df["clase"], random_state=0)
    val, prueba = train_test_split(resto, test_size=0.50, stratify=resto["clase"], random_state=0)
    df["conjunto"] = "entrenamiento"
    df.loc[val.index, "conjunto"] = "validacion"
    df.loc[prueba.index, "conjunto"] = "prueba"

    # aspecto radiológico de la lesión según el tipo de tumor (para el visor 3D)
    df["aspecto"] = ""
    for aspecto, tipos in ASPECTOS.items():
        for t in tipos:
            c = columna(df, t)
            if c:
                df.loc[pd.to_numeric(df[c], errors="coerce").fillna(0) == 1, "aspecto"] = aspecto
    df.loc[df["clase"] == "normal", "aspecto"] = ""
    df["origen"] = "btxrd"; df["etiquetas_yolo"] = ""

    extras = ["aspecto", "origen", "etiquetas_yolo"] + [c for c in (columna(df, "age"), columna(df, "gender"), columna(df, "center")) if c]
    # hueso(s) que aparecen en cada radiografía (para el clasificador de hueso y el visor 3D)
    for clave, nombre in HUESOS.items():
        c = columna(df, nombre)
        if c:
            df["hueso_" + clave] = (pd.to_numeric(df[c], errors="coerce").fillna(0) == 1).astype(int)
            extras.append("hueso_" + clave)
    os.makedirs(DIR_PREPARADOS, exist_ok=True)
    salida = df[["imagen", "ruta", "clase", "conjunto"] + extras]
    clinica = casos_clinica(a.extra)
    if len(clinica):
        salida = pd.concat([salida, clinica], ignore_index=True)
        for c in salida.columns:
            if c.startswith("hueso_"):
                salida[c] = salida[c].fillna(0).astype(int)
        salida["aspecto"] = salida["aspecto"].fillna("")
    salida.to_csv(RUTA_DIVISION, index=False)
    with open(RUTA_CONFIG, "w", encoding="utf-8") as f:
        json.dump({"datos": os.path.abspath(a.datos), "dir_img": dir_img, "dir_anot": dir_anot}, f, indent=2)

    # imágenes de PRUEBA (los modelos nunca las ven) para probar la aplicación
    ejemplos = os.path.join(RAIZ, "ejemplos_prueba")
    shutil.rmtree(ejemplos, ignore_errors=True); os.makedirs(ejemplos)
    pr = df[df.conjunto == "prueba"]   # solo BTXRD
    for nombre, g in pr.groupby("clase"):
        for r in g["ruta"].sample(min(8, len(g)), random_state=0):
            shutil.copy(r, os.path.join(ejemplos, f"{nombre}_{os.path.basename(r)}"))

    print("\nImágenes por clase y conjunto:")
    print(pd.crosstab(salida["clase"], salida["conjunto"], margins=True).to_string())
    if (salida["aspecto"] != "").any():
        print("\nAspecto de la lesión (para el 3D):", salida[salida["aspecto"] != ""]["aspecto"].value_counts().to_dict())
    print(f"\nDivisión guardada en {RUTA_DIVISION}")


if __name__ == "__main__":
    main()
