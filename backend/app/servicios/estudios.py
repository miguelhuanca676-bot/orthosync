"""Estudios radiográficos: subir, analizar con la CNN, valorar, publicar y borrar (solo traumatólogo)."""
import os, shutil
from datetime import date

from PIL import Image
from sqlalchemy.orm import Session

from ..core import config
from ..core.almacen import abrir_imagen, guardar_imagen, leer_bytes
from ..core.errores import ArchivoGrande, DatoInvalido, NoEncontrado
from ..db.base import ahora
from ..db.modelos import Estudio, Usuario
from ..dominio.reglas import EVOLUCIONES, HUESOS, OPINIONES, normalizar_cajas, normalizar_zona_3d
from ..integraciones import inferencia
from ..integraciones.documentos import ArchivoNoValido, extraer_radiografia
from ..repositorios import estudios as repo
from ..repositorios.registros import auditar
from .pacientes import buscar as buscar_paciente


def buscar(bd: Session, uid: str) -> Estudio:
    e = repo.por_uid(bd, uid)
    if e is None:
        raise NoEncontrado()
    return e


def carpeta(e: Estudio) -> str:
    return os.path.join(config.DIR_ARCHIVOS, e.carpeta)


def analizar_y_guardar(e: Estudio, img: Image.Image):
    """Guarda la radiografía (cifrada), se la manda a la CNN y guarda lo que responde."""
    dir_e = carpeta(e)
    guardar_imagen(img, os.path.join(dir_e, "radiografia.png"))
    r = inferencia.analizar(img)
    e.estado_analisis = r.get("estado", "error")
    if e.estado_analisis != "listo":
        return
    e.p_tumor, e.p_maligno, e.sospechoso = r["p_tumor"], r["p_maligno"], r["sospechoso"]
    e.conclusion_sistema, e.cajas, e.area_lesion = r["conclusion"], r["cajas"], r["area_lesion"]
    e.hueso_sugerido = r["hueso_sugerido"]
    e.aspecto_sugerido = r.get("aspecto_sugerido")
    if e.zona_3d is None:
        e.zona_3d = r["zona_3d"]
    guardar_imagen(r["img_cajas"], os.path.join(dir_e, "cajas.png"))
    guardar_imagen(r["img_calor"], os.path.join(dir_e, "calor.png"))


def listar(bd: Session, actor: Usuario, pid: str) -> list[Estudio]:
    p = buscar_paciente(bd, pid)
    auditar(bd, actor, "ver_estudios", p.codigo, p.id); bd.commit()
    return list(p.estudios)


def subir(bd: Session, actor: Usuario, pid: str, nombre: str, datos: bytes, fecha: date | None) -> Estudio:
    p = buscar_paciente(bd, pid)
    if len(datos) > config.TAM_MAX_ARCHIVO_MB * 1024 * 1024:
        raise ArchivoGrande(f"El archivo supera los {config.TAM_MAX_ARCHIVO_MB} MB")
    nombre = os.path.basename(nombre or "archivo")[:120]
    try:
        img = extraer_radiografia(nombre, datos)
    except ArchivoNoValido as err:
        raise DatoInvalido(str(err))
    # el archivo original NO se guarda (puede traer nombre y datos del paciente incrustados)
    e = Estudio(paciente_id=p.id, medico_id=actor.id, fecha_estudio=fecha or date.today(),
                archivo_original=nombre, carpeta="")
    bd.add(e); bd.flush()
    e.carpeta = os.path.join(f"p{p.id}", f"e{e.id}")
    os.makedirs(carpeta(e), exist_ok=True)
    guardar_imagen(img, os.path.join(carpeta(e), "sin_recortar.png"))
    analizar_y_guardar(e, img)
    if not any(x.id != e.id for x in p.estudios):
        e.evolucion = "primera"
    auditar(bd, actor, "subir_estudio", p.codigo, p.id); bd.commit()
    return e


def ver(bd: Session, actor: Usuario, eid: str) -> Estudio:
    e = buscar(bd, eid)
    auditar(bd, actor, "ver_estudio", e.paciente.codigo, e.paciente_id); bd.commit()
    return e


def reanalizar(bd: Session, actor: Usuario, eid: str) -> Estudio:
    e = buscar(bd, eid)
    analizar_y_guardar(e, abrir_imagen(os.path.join(carpeta(e), "radiografia.png")))
    auditar(bd, actor, "reanalizar_estudio", e.paciente.codigo, e.paciente_id); bd.commit()
    return e


def recortar(bd: Session, actor: Usuario, eid: str, x1: float, y1: float, x2: float, y2: float) -> Estudio:
    e = buscar(bd, eid)
    if x2 - x1 < 0.05 or y2 - y1 < 0.05:
        raise DatoInvalido("El recorte es demasiado pequeño")
    base = abrir_imagen(os.path.join(carpeta(e), "sin_recortar.png"))
    img = base.crop((round(x1 * base.width), round(y1 * base.height), round(x2 * base.width), round(y2 * base.height)))
    e.zona_3d = None
    analizar_y_guardar(e, img)
    auditar(bd, actor, "recortar_estudio", e.paciente.codigo, e.paciente_id); bd.commit()
    return e


def valorar(bd: Session, actor: Usuario, eid: str, d: dict) -> Estudio:
    """Guarda la valoración del médico. Con publicar=True, además la deja visible para el paciente."""
    e = buscar(bd, eid)
    publicar = d.pop("publicar", None)
    if d.get("hueso") and d["hueso"] not in HUESOS:
        raise DatoInvalido("Hueso no válido")
    if d.get("opinion") and d["opinion"] not in OPINIONES:
        raise DatoInvalido("Opinión no válida")
    if d.get("evolucion") and d["evolucion"] not in EVOLUCIONES:
        raise DatoInvalido("Evolución no válida")
    if d.get("cajas_medico") is not None:
        d["cajas_medico"] = normalizar_cajas(d["cajas_medico"])
        e.corregido_en = ahora()
    if d.get("proximo_control") and d["proximo_control"] < e.fecha_estudio:
        raise DatoInvalido("El próximo control no puede ser anterior al estudio")
    if d.get("zona_3d"):
        d["zona_3d"] = normalizar_zona_3d(d["zona_3d"])
    for k, val in d.items():
        setattr(e, k, val)
    if "opinion" in d:
        e.valorado_en = ahora()
    if publicar and not e.opinion:
        raise DatoInvalido("Indica tu opinión: el paciente solo ve estudios ya valorados")
    auditar(bd, actor, "valorar_estudio", e.paciente.codigo, e.paciente_id)
    if publicar and not e.publicado:
        e.publicado = True
        auditar(bd, actor, "publicar_estudio", e.paciente.codigo, e.paciente_id)
    bd.commit()
    return e


def publicar(bd: Session, actor: Usuario, eid: str, visible: bool) -> Estudio:
    e = buscar(bd, eid)
    if visible and not e.opinion:
        raise DatoInvalido("Primero registra tu valoración; el paciente solo ve estudios ya valorados")
    e.publicado = visible
    auditar(bd, actor, "publicar_estudio" if visible else "ocultar_estudio", e.paciente.codigo, e.paciente_id)
    bd.commit()
    return e


def borrar(bd: Session, actor: Usuario, eid: str):
    e = buscar(bd, eid)
    dir_e = carpeta(e)
    auditar(bd, actor, "borrar_estudio", e.paciente.codigo, e.paciente_id)
    bd.delete(e); bd.commit()
    shutil.rmtree(dir_e, ignore_errors=True)


def evolucion(bd: Session, pid: str) -> dict:
    p = buscar_paciente(bd, pid)
    puntos = [{"estudio_id": e.uid, "fecha": e.fecha_estudio, "area_lesion": e.area_lesion, "p_tumor": e.p_tumor,
               "p_maligno": e.p_maligno, "opinion": e.opinion, "evolucion": e.evolucion,
               "tratamiento": e.tratamiento} for e in p.estudios]
    con_area = [x for x in puntos if x["area_lesion"]]
    cambio = None
    if len(con_area) >= 2 and con_area[-2]["area_lesion"] > 0:
        cambio = (con_area[-1]["area_lesion"] - con_area[-2]["area_lesion"]) / con_area[-2]["area_lesion"]
    return {"puntos": puntos, "cambio_area_ultimo": cambio,
            "nota": "El área es la fracción de la imagen que ocupa la zona marcada; es una medida relativa "
                    "y depende del encuadre de cada radiografía."}


def imagen(bd: Session, actor: Usuario, eid: str, tipo: str) -> bytes:
    """Radiografía descifrada al vuelo. El paciente solo ve la suya y solo si el médico la publicó."""
    e = buscar(bd, eid)
    if actor.rol == "traumatologo":
        permitidos = ("radiografia", "cajas", "calor", "sin_recortar")
    elif (actor.rol == "paciente" and actor.acepto_terminos_en and actor.paciente_id == e.paciente_id
          and e.publicado):
        permitidos = ("radiografia",)
    else:
        raise NoEncontrado()
    ruta = os.path.join(carpeta(e), tipo + ".png")
    if tipo not in permitidos or not os.path.exists(ruta):
        raise NoEncontrado()
    return leer_bytes(ruta)
