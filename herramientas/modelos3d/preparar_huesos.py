"""
Prepara los modelos 3D anatómicos (high poly) que usa el visor de Orthosync.

Toma las mallas reales de BodyParts3D (escaneos de un cuerpo humano, licencia CC BY-SA 2.1 Japón),
las orienta igual que el visor, las suaviza, les sube la resolución y las guarda como .glb en
frontend/public/modelos3d/.

Convención del visor (igual que frontend/src/hueso3d.ts):
  - el hueso mide ALTO = 10 unidades en el eje Y; y = 10 es el extremo superior y y = 0 el inferior;
  - huesos del lado DERECHO (el visor hace el espejo para el izquierdo);
  - eje +X hacia la línea media del cuerpo y +Z hacia el frente;
  - mano y pie con los dedos hacia arriba, como en la radiografía.

Uso (desde la raíz del repositorio):
    pip install trimesh pymeshlab numpy
    python herramientas/modelos3d/preparar_huesos.py              # descarga los STL de GitHub
    python herramientas/modelos3d/preparar_huesos.py --stl CARPETA # usa STL ya descargados
Luego, para comprimirlos (opcional, recomendado):
    npx gltfpack -i hueso.glb -o hueso.glb -cc -noq   (lo hace el script si encuentra npx)
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request

import numpy as np
import pymeshlab
import trimesh

ALTO = 10.0
RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SALIDA = os.path.join(RAIZ, "frontend", "public", "modelos3d")
URL = "https://raw.githubusercontent.com/Kevin-Mattheus-Moerman/BodyParts3D/main/assets/BodyParts3D_data/stl/FMA{}.stl"

# Huesos del lado derecho (identificadores FMA de BodyParts3D)
MANO = [
    24435, 24437, 24439, 24441, 24443, 23725, 24446, 24448,          # carpo
    24464, 24466, 24468, 24470, 24472,                                # metacarpianos
    24450, 24451, 24452, 24453, 24454,                                # falanges proximales
    24455, 24456, 24457, 24458,                                       # falanges medias
    24459, 24460, 24461, 24462, 24463,                                # falanges distales
]
PIE = [
    24482, 24497, 24500, 24528, 24521, 24523, 24525,                  # tarso
    24507, 24509, 24511, 24513, 24515,                                # metatarsianos
    43253, 32634, 32636, 32638, 32640,                                # falanges proximales
    32642, 32644, 32646, 230986,                                      # falanges medias
    32650, 32652, 32654, 32656, 32658,                                # falanges distales
]
HUESOS = {
    # nombre: (partes, orientación, longitud de arista objetivo en unidades del visor)
    "femur": ([24474], "largo", 0.035),
    "tibia": ([24477], "largo", 0.035),
    "perone": ([24480], "largo", 0.026),
    "humero": ([23130], "largo", 0.035),
    "radio": ([23464], "largo", 0.03),
    "cubito": ([23467], "largo", 0.03),
    "cadera": ([16586], "largo", 0.055),
    "mano": (MANO, "mano", 0.048),
    "pie": (PIE, "pie", 0.048),
}

# BodyParts3D usa: X hacia la izquierda del cuerpo, Y hacia atrás, Z hacia arriba (milímetros).
# Cada matriz convierte (x, y, z) de BodyParts3D a (x, y, z) del visor; todas son rotaciones puras.
ORIENTACION = {
    "largo": np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], float),   # arriba = arriba, frente = +Z
    "mano": np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], float),    # dedos arriba, dorso hacia el frente
    "pie": np.array([[-1, 0, 0], [0, -1, 0], [0, 0, 1]], float),    # dedos arriba, dorso hacia el frente
}


def leer_stl(fma: int, carpeta: str | None) -> trimesh.Trimesh:
    if carpeta:
        return trimesh.load(os.path.join(carpeta, f"FMA{fma}.stl"), force="mesh")
    with urllib.request.urlopen(URL.format(fma), timeout=60) as r:
        datos = r.read()
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as f:
        f.write(datos)
    try:
        return trimesh.load(f.name, force="mesh")
    finally:
        os.unlink(f.name)


def alta_resolucion(m: trimesh.Trimesh, arista: float) -> trimesh.Trimesh:
    """Superficie lisa y uniforme: remallado isotrópico + suavizado de Taubin (no encoge el hueso)."""
    ms = pymeshlab.MeshSet()
    ms.add_mesh(pymeshlab.Mesh(m.vertices, m.faces))
    ms.meshing_remove_duplicate_vertices()
    ms.meshing_repair_non_manifold_edges()
    ms.apply_coord_taubin_smoothing(lambda_=0.5, mu=-0.53, stepsmoothnum=12)   # quita el escalonado del escaneo
    ms.meshing_isotropic_explicit_remeshing(iterations=6, targetlen=getattr(pymeshlab, "PureValue", getattr(pymeshlab, "AbsoluteValue", None))(arista))
    ms.apply_coord_taubin_smoothing(lambda_=0.5, mu=-0.53, stepsmoothnum=6)
    s = ms.current_mesh()
    return trimesh.Trimesh(s.vertex_matrix(), s.face_matrix(), process=True)


def preparar(nombre: str, partes: list[int], orient: str, arista: float, carpeta: str | None) -> list[trimesh.Trimesh]:
    mallas = [leer_stl(f, carpeta) for f in partes]
    R = ORIENTACION[orient]
    for m in mallas:
        m.vertices = m.vertices @ R.T
    todo = trimesh.util.concatenate(mallas)
    mn, mx = todo.bounds
    escala = ALTO / (mx[1] - mn[1])
    centro = np.array([(mn[0] + mx[0]) / 2, mn[1], (mn[2] + mx[2]) / 2])
    salida = []
    for m in mallas:
        m.vertices = (m.vertices - centro) * escala
        salida.append(alta_resolucion(m, arista))
    for m in salida:
        m.fix_normals()
    return salida


def comprimir(ruta: str):
    npx = shutil.which("npx")
    if not npx:
        print("   (sin npx: el .glb queda sin comprimir)")
        return
    tmp = ruta + ".tmp.glb"
    r = subprocess.run([npx, "-y", "gltfpack", "-i", ruta, "-o", tmp, "-cc", "-noq", "-kn"],
                       capture_output=True, text=True)
    if r.returncode == 0 and os.path.exists(tmp):
        os.replace(tmp, ruta)
    else:
        print("   (gltfpack falló; queda sin comprimir)", r.stderr[-300:])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stl", help="carpeta con los FMA*.stl de BodyParts3D (si no, se descargan)")
    ap.add_argument("--solo", nargs="*", help="preparar solo estos huesos")
    ap.add_argument("--sin-comprimir", action="store_true")
    a = ap.parse_args()
    os.makedirs(SALIDA, exist_ok=True)
    for nombre, (partes, orient, arista) in HUESOS.items():
        if a.solo and nombre not in a.solo:
            continue
        piezas = preparar(nombre, partes, orient, arista, a.stl)
        ruta = os.path.join(SALIDA, f"{nombre}.glb")
        # una malla por hueso (la mano y el pie tienen varios); sin normales: el visor las calcula
        # después de unir vértices, así la lesión deforma sin costuras
        escena = trimesh.Scene()
        for fma, m in zip(partes, piezas):
            escena.add_geometry(trimesh.Trimesh(m.vertices.astype(np.float32), m.faces, process=False),
                                node_name=f"FMA{fma}", geom_name=f"FMA{fma}")
        escena.export(ruta)
        if not a.sin_comprimir:
            comprimir(ruta)
        print(f"{nombre:7s} {sum(len(m.faces) for m in piezas):7d} triángulos  {os.path.getsize(ruta) / 1e6:5.2f} MB  -> {os.path.relpath(ruta, RAIZ)}")


if __name__ == "__main__":
    sys.exit(main())
