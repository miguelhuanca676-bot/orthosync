"""Reglas del negocio clínico: valores permitidos y cálculos que no dependen de la base de datos ni de la web."""
from datetime import date

from ..core.errores import DatoInvalido

HUESOS = ("mano", "cubito", "radio", "humero", "pie", "tibia", "perone", "femur", "cadera")
OPINIONES = ("normal", "benigno", "maligno", "no_concluyente")
EVOLUCIONES = ("primera", "mejoria", "estable", "progresion")
TIPOS_3D = ("cavidad", "crecimiento", "mancha")
PERSONAL = ("administrador", "traumatologo", "recepcion")      # roles del personal de la clínica


def edad(nacimiento: date | None, hoy: date | None = None) -> int | None:
    if not nacimiento:
        return None
    h = hoy or date.today()
    return h.year - nacimiento.year - ((h.month, h.day) < (nacimiento.month, nacimiento.day))


def es_menor(nacimiento: date | None) -> bool:
    e = edad(nacimiento)
    return e is not None and e < 18      # un bebé de 0 años también es menor


def validar_datos_paciente(fecha_nacimiento: date, tutor_nombre: str | None):
    if fecha_nacimiento > date.today():
        raise DatoInvalido("La fecha de nacimiento no puede ser futura")
    if es_menor(fecha_nacimiento) and not (tutor_nombre and tutor_nombre.strip()):
        raise DatoInvalido("El paciente es menor de edad: registra el nombre de su padre, madre o tutor")


def normalizar_cajas(cajas: list) -> list[list[float]]:
    """Recuadros del médico en fracción de la imagen (0-1), ordenados y con tamaño mínimo. Máximo 5."""
    salida = []
    for c in cajas[:5]:
        if len(c) != 4:
            raise DatoInvalido("Recuadro no válido")
        x1, y1, x2, y2 = (min(max(float(v), 0), 1) for v in c)
        x1, x2 = sorted((x1, x2)); y1, y2 = sorted((y1, y2))
        if x2 - x1 < 0.005 or y2 - y1 < 0.005:
            raise DatoInvalido("El recuadro es demasiado pequeño")
        salida.append([round(x1, 4), round(y1, 4), round(x2, 4), round(y2, 4)])
    return salida


def normalizar_zona_3d(z: dict) -> dict:
    try:
        return {"posicion": min(max(float(z["posicion"]), 0), 1),
                "extension": min(max(float(z.get("extension", 0.15)), 0.02), 1),
                "angulo": float(z.get("angulo") or 0) % 360,
                "tipo": z.get("tipo") if z.get("tipo") in TIPOS_3D else None}
    except (KeyError, TypeError, ValueError):
        raise DatoInvalido("Zona 3D no válida")


# ---------------------------------------------------------------- estadística de concordancia
def kappa(a: int, b: int, c: int, d: int) -> float | None:
    """Kappa de Cohen para una tabla 2x2 [[a, b], [c, d]] (filas: médico; columnas: sistema)."""
    n = a + b + c + d
    if n == 0:
        return None
    po = (a + d) / n; pe = ((a + b) * (a + c) + (c + d) * (b + d)) / n ** 2
    return None if pe == 1 else round((po - pe) / (1 - pe), 4)


def tabla_concordancia(pares) -> dict:
    """pares: (referencia_del_medico, prediccion_del_sistema) booleanos."""
    vp = sum(1 for m, s in pares if m and s); fn = sum(1 for m, s in pares if m and not s)
    fp = sum(1 for m, s in pares if not m and s); vn = sum(1 for m, s in pares if not m and not s)
    n = vp + fn + fp + vn
    return {"n": n, "matriz": {"VP": vp, "FN": fn, "FP": fp, "VN": vn},
            "acuerdo": None if n == 0 else round((vp + vn) / n, 4), "kappa": kappa(vn, fp, fn, vp),
            "sensibilidad": None if vp + fn == 0 else round(vp / (vp + fn), 4),
            "especificidad": None if vn + fp == 0 else round(vn / (vn + fp), 4)}
