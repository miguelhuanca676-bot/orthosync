"""Herramientas de la clínica: controles programados, validación del modelo y casos para reentrenar."""
import csv, io, os, zipfile
from datetime import date

from PIL import Image
from sqlalchemy.orm import Session

from ..core.almacen import leer_bytes
from ..core.errores import DatoInvalido
from ..db.modelos import Usuario
from ..dominio.reglas import tabla_concordancia
from ..integraciones import inferencia
from ..repositorios import estudios, pacientes
from ..repositorios.registros import auditar
from .estudios import carpeta


def controles(bd: Session, actor: Usuario) -> list[dict]:
    """Pacientes cuyo último estudio tiene un próximo control indicado por el médico."""
    hoy = date.today(); salida = []
    for p in pacientes.todos(bd):
        if not p.estudios:
            continue
        ult = max(p.estudios, key=lambda e: (e.fecha_estudio, e.id))
        if ult.proximo_control:
            salida.append({"paciente_id": p.uid, "codigo": p.codigo, "nombre": f"{p.nombres} {p.apellidos}",
                           "telefono": p.telefono, "ultimo_estudio": ult.fecha_estudio,
                           "fecha_control": ult.proximo_control, "dias": (ult.proximo_control - hoy).days})
    salida.sort(key=lambda x: x["fecha_control"])
    auditar(bd, actor, "ver_controles"); bd.commit()
    return salida


def validacion(bd: Session) -> dict:
    """Métricas del conjunto de prueba (Kaggle) y concordancia real sistema-médico en la clínica."""
    info = inferencia.info_modelos() or {}
    modelos = info.get("modelos", {})
    umbral_mal = (modelos.get("malignidad") or {}).get("umbral", 0.5)
    valorados = estudios.valorados_con_resultado(bd)
    lesion = tabla_concordancia([(e.opinion != "normal", bool(e.sospechoso)) for e in valorados])
    mal = tabla_concordancia([(e.opinion == "maligno", e.p_maligno >= umbral_mal) for e in valorados
                              if e.opinion in ("benigno", "maligno") and e.p_maligno is not None])
    por_mes: dict[str, list] = {}
    for e in valorados:
        por_mes.setdefault(e.fecha_estudio.strftime("%Y-%m"), []).append((e.opinion != "normal") == bool(e.sospechoso))
    return {"prueba": info.get("evaluacion"),
            "umbrales": {k: v.get("umbral") for k, v in modelos.items() if "umbral" in v},
            "modelos": sorted(modelos), "detector": (modelos.get("detector") or {}).get("metricas_prueba"),
            "uso_real": {"lesion": lesion, "malignidad": mal, "corregidos": estudios.contar_corregidos(bd),
                         "por_mes": [{"mes": k, "n": len(v), "acuerdo": round(sum(v) / len(v), 4)}
                                     for k, v in sorted(por_mes.items())]}}


def exportar_correcciones(bd: Session, actor: Usuario) -> bytes:
    """ZIP anonimizado con los estudios valorados: imagen, etiquetas del médico y recuadros en formato YOLO.
    Sirve para volver a entrenar los modelos en Kaggle con los casos corregidos."""
    lista = estudios.valorados(bd)
    if not lista:
        raise DatoInvalido("Todavía no hay estudios valorados para exportar")
    buf = io.BytesIO(); filas = []
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for e in lista:
            ruta = os.path.join(carpeta(e), "radiografia.png")
            if not os.path.exists(ruta):
                continue
            nombre = e.uid
            z.writestr(f"images/{nombre}.png", leer_bytes(ruta))
            cajas = e.cajas_medico if e.cajas_medico is not None else (
                [[c[0], c[1], c[2], c[3]] for c in (e.cajas or []) if c[4] > 0] if e.opinion != "normal" else [])
            origen = "medico" if e.cajas_medico is not None else ("sistema" if cajas else "ninguno")
            if e.cajas_medico is None and cajas and max(max(c) for c in cajas) > 1.0:
                with Image.open(io.BytesIO(leer_bytes(ruta))) as im:   # cajas del sistema en píxeles -> fracción
                    w, h = im.size
                cajas = [[c[0] / w, c[1] / h, c[2] / w, c[3] / h] for c in cajas]
            z.writestr(f"labels/{nombre}.txt", "".join(
                f"0 {(c[0] + c[2]) / 2:.6f} {(c[1] + c[3]) / 2:.6f} {c[2] - c[0]:.6f} {c[3] - c[1]:.6f}\n" for c in cajas)
                if e.opinion != "normal" else "")
            filas.append({"imagen": f"{nombre}.png", "tumor": int(e.opinion != "normal"),
                          "maligno": "" if e.opinion == "normal" else int(e.opinion == "maligno"),
                          "hueso": e.hueso or "", "lado": e.lado or "", "origen_recuadro": origen,
                          "sistema_sospechoso": "" if e.sospechoso is None else int(bool(e.sospechoso)),
                          "desacuerdo": "" if e.sospechoso is None else int(bool(e.sospechoso) != (e.opinion != "normal"))})
        t = io.StringIO(); w = csv.DictWriter(t, fieldnames=list(filas[0]) if filas else ["imagen"])
        w.writeheader(); w.writerows(filas); z.writestr("casos.csv", t.getvalue())
        z.writestr("LEEME.txt", "Casos valorados por el traumatólogo en Orthosync, sin datos personales.\n"
                   "images/: radiografías. labels/: recuadros de la lesión en formato YOLO (clase 0 = lesión).\n"
                   "casos.csv: etiquetas del médico (tumor, maligno), hueso y si el sistema coincidió con el médico.\n"
                   "Uso: súbelo a Kaggle como dataset y actívalo en el cuaderno de entrenamiento.\n")
    auditar(bd, actor, "exportar_correcciones", f"{len(filas)} casos"); bd.commit()
    return buf.getvalue()
