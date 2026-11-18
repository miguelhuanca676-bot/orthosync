"""Entrena y evalúa el sistema completo con un solo comando.

    python entrenar_todo.py --datos "C:\\tesis\\BTXRD"            (completo)
    python entrenar_todo.py --datos "C:\\tesis\\BTXRD" --rapido   (prueba de pocos minutos)
"""
import argparse, os, subprocess, sys, time

AQUI = os.path.dirname(os.path.abspath(__file__))


def paso(titulo, *args):
    print(f"\n{'#' * 70}\n# {titulo}\n{'#' * 70}", flush=True)
    t0 = time.time()
    r = subprocess.run([sys.executable, *args], cwd=AQUI)
    if r.returncode != 0:
        raise SystemExit(f"\nERROR en el paso: {titulo}. Revisa el mensaje de arriba.")
    print(f"[{titulo}] listo en {(time.time() - t0) / 60:.1f} min", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datos", required=True, help="Carpeta donde descomprimiste BTXRD")
    ap.add_argument("--rapido", action="store_true", help="Prueba rápida con pocas imágenes y épocas")
    ap.add_argument("--sin-detector", action="store_true", help="No entrenar YOLO (es el paso más lento)")
    ap.add_argument("--extra", nargs="*", default=[], help="Carpetas con casos corregidos exportados desde Orthosync")
    a = ap.parse_args()

    prep = ["preparar_datos.py", "--datos", a.datos]
    c1 = ["entrenar_clasificador.py", "--tarea", "tumor"]
    c2 = ["entrenar_clasificador.py", "--tarea", "malignidad"]
    det = ["entrenar_detector.py"]
    hueso = ["entrenar_hueso.py"]
    aspecto = ["entrenar_aspecto.py"]
    if a.extra:
        prep += ["--extra", *a.extra]
    if a.rapido:
        prep += ["--max-imagenes", "450"]
        c1 += ["--epocas", "2"]; c2 += ["--epocas", "2"]
        det += ["--epocas", "3", "--tam", "320"]
        hueso += ["--epocas", "2"]; aspecto += ["--epocas", "2"]

    paso("1/7 Preparar y dividir los datos", *prep)
    paso("2/7 Clasificador normal vs. lesión", *c1)
    paso("3/7 Clasificador benigno vs. maligno", *c2)
    paso("4/7 Clasificador de hueso", *hueso)
    paso("4b/7 Aspecto de la lesión (para el 3D)", *aspecto)
    if not a.sin_detector:
        paso("5/7 Detector YOLO (localización)", *det)
    paso("6/7 Evaluación en el conjunto de prueba", "evaluar.py")
    paso("7/7 Exportar los modelos para el servidor (ONNX)", "exportar_onnx.py")
    print("\nTODO LISTO. Los modelos están en la carpeta modelos/ y las métricas en resultados/")


if __name__ == "__main__":
    main()
