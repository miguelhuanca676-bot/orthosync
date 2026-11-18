"""Informes en PDF: uno completo para el médico y uno sencillo para el paciente."""
import io, os
from datetime import date, datetime, timedelta, timezone

from fpdf import FPDF
from PIL import Image

from ..core import config

AZUL, AZUL_OSCURO, CIELO, GRIS, TINTA = (11, 61, 145), (8, 43, 104), (232, 241, 252), (100, 116, 139), (15, 31, 61)
OPINIONES = {"normal": "Normal", "benigno": "Lesión de aspecto benigno", "maligno": "Lesión de aspecto maligno",
             "no_concluyente": "No concluyente"}
EVOLUCIONES = {"primera": "Primer estudio", "mejoria": "Mejoría", "estable": "Estable", "progresion": "Progresión"}
HUESOS = {"femur": "Fémur", "tibia": "Tibia", "perone": "Peroné", "humero": "Húmero", "radio": "Radio",
          "cubito": "Cúbito", "mano": "Mano", "pie": "Pie", "cadera": "Cadera"}
TIPOS = {"cavidad": "lítica (hueco)", "crecimiento": "crece hacia afuera", "mancha": "zona marcada"}


def _t(s) -> str:
    """Las fuentes básicas del PDF usan Latin-1: se reemplazan los pocos signos que no entran."""
    s = "" if s is None else str(s)
    for a, b in (("–", "-"), ("—", "-"), ("“", '"'), ("”", '"'), ("‘", "'"), ("’", "'"), ("…", "..."), ("≥", ">="), ("≤", "<=")):
        s = s.replace(a, b)
    return s.encode("latin-1", "replace").decode("latin-1")


def _local(d: datetime) -> datetime:
    """Las fechas se guardan en UTC; se muestran en la hora local de la clínica."""
    return d + timedelta(hours=config.HORAS_UTC)


def _ahora() -> datetime:
    return _local(datetime.now(timezone.utc).replace(tzinfo=None))


def _f(d) -> str:
    if not d:
        return "-"
    if isinstance(d, datetime):
        return _local(d).strftime("%d/%m/%Y %H:%M")
    return d.strftime("%d/%m/%Y") if isinstance(d, date) else str(d)


def _pct(v) -> str:
    return "-" if v is None else f"{v * 100:.1f} %"


def _edad(nac, ref):
    if not nac:
        return None
    return ref.year - nac.year - ((ref.month, ref.day) < (nac.month, nac.day))


def _logo(blanco=False):
    for nombre in (("logo-blanco.png",) if blanco else ()) + ("logo.png",):
        ruta = os.path.join(os.path.dirname(os.path.dirname(__file__)), "recursos", nombre)
        if os.path.exists(ruta):
            return ruta
    return None


class _Informe(FPDF):
    def __init__(self, titulo: str, subtitulo: str):
        super().__init__(format="A4")
        self.titulo, self.subtitulo = titulo, subtitulo
        self.set_auto_page_break(True, 22)
        self.set_margins(15, 15, 15)
        self.alias_nb_pages()

    def header(self):
        self.set_fill_color(*AZUL_OSCURO); self.rect(0, 0, self.w, 30, "F")
        for i, color in enumerate(((56, 189, 248), (30, 111, 217), (79, 70, 229), (124, 58, 237))):   # franja celeste → violeta
            self.set_fill_color(*color); self.rect(i * self.w / 4, 30, self.w / 4 + 0.2, 1.4, "F")
        logo = _logo(blanco=True)
        if logo:
            self.image(logo, x=14, y=6, h=18)
        self.set_text_color(255, 255, 255)
        self.set_xy(36, 7); self.set_font("Helvetica", "B", 15); self.cell(0, 7, _t(self.titulo))
        self.set_xy(36, 15); self.set_font("Helvetica", "", 9.5)
        self.cell(0, 5, _t(f"{config.NOMBRE_SISTEMA} · {config.NOMBRE_CLINICA} · {self.subtitulo}"))
        self.set_text_color(*TINTA); self.set_y(37)

    def footer(self):
        self.set_y(-17); self.set_draw_color(203, 213, 225); self.line(15, self.get_y(), self.w - 15, self.get_y())
        self.set_y(-15); self.set_font("Helvetica", "", 7.5); self.set_text_color(*GRIS)
        self.multi_cell(self.w - 50, 3.6, _t(config.AVISO), new_x="RIGHT", new_y="TOP")
        self.set_xy(self.w - 35, -15); self.cell(20, 4, f"Página {self.page_no()}/{{nb}}", align="R")
        self.set_text_color(*TINTA)

    # --- piezas
    def seccion(self, texto):
        if self.get_y() > self.h - 50:
            self.add_page()
        self.ln(3); self.set_font("Helvetica", "B", 11.5); self.set_text_color(*AZUL)
        self.cell(0, 7, _t(texto), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*AZUL); self.set_line_width(0.4); self.line(15, self.get_y(), self.w - 15, self.get_y())
        self.set_line_width(0.2); self.set_text_color(*TINTA); self.ln(2.5)

    def datos(self, filas, columnas=2):
        """Pares etiqueta/valor en columnas."""
        ancho = (self.w - 30) / columnas
        for i in range(0, len(filas), columnas):
            y = self.get_y(); fondo = y + 10
            for j, (k, v) in enumerate(filas[i:i + columnas]):
                self.set_xy(15 + j * ancho, y)
                self.set_font("Helvetica", "", 8); self.set_text_color(*GRIS); self.cell(ancho - 3, 4, _t(k))
                self.set_xy(15 + j * ancho, y + 4)
                self.set_font("Helvetica", "B", 10); self.set_text_color(*TINTA)
                self.multi_cell(ancho - 3, 5, _t(v), new_x="LMARGIN", new_y="NEXT")
                fondo = max(fondo, self.get_y())
            self.set_y(fondo + 1.5)

    def parrafo(self, texto, tam=10, estilo=""):
        self.set_font("Helvetica", estilo, tam); self.set_x(15)
        self.multi_cell(self.w - 30, 5.2, _t(texto), new_x="LMARGIN", new_y="NEXT")

    def caja(self, texto, color_fondo=CIELO, color_texto=AZUL_OSCURO):
        self.set_fill_color(*color_fondo); self.set_text_color(*color_texto); self.set_font("Helvetica", "B", 10.5)
        self.set_x(15); self.multi_cell(self.w - 30, 7, _t(texto), fill=True, new_x="LMARGIN", new_y="NEXT", padding=(1, 3))
        self.set_text_color(*TINTA); self.ln(2)

    def imagenes(self, lista, alto_max=88):
        """Varias imágenes lado a lado, con su pie."""
        lista = [(im, pie) for im, pie in lista if im is not None]
        if not lista:
            return
        n = len(lista); sep = 5; ancho = (self.w - 30 - sep * (n - 1)) / n
        alto = min(alto_max, max(ancho * im.height / im.width for im, _ in lista))
        if self.get_y() + alto + 10 > self.h - 22:
            self.add_page()
        y = self.get_y()
        for i, (im, pie) in enumerate(lista):
            x = 15 + i * (ancho + sep)
            self.set_fill_color(15, 31, 61); self.rect(x, y, ancho, alto, "F")
            e = min(ancho / im.width, alto / im.height); w, h = im.width * e, im.height * e
            self.image(im.convert("RGB"), x=x + (ancho - w) / 2, y=y + (alto - h) / 2, w=w, h=h)
            self.set_xy(x, y + alto + 1); self.set_font("Helvetica", "I", 8); self.set_text_color(*GRIS)
            self.cell(ancho, 4, _t(pie), align="C")
        self.set_text_color(*TINTA); self.set_y(y + alto + 7)

    def tabla(self, encabezados, filas, anchos, resaltar=None):
        self.set_font("Helvetica", "B", 8.5); self.set_fill_color(*CIELO); self.set_text_color(*AZUL_OSCURO)
        for h, w in zip(encabezados, anchos):
            self.cell(w, 7, _t(h), border=0, fill=True)
        self.ln(); self.set_text_color(*TINTA)
        for i, fila in enumerate(filas):
            self.set_font("Helvetica", "B" if i == resaltar else "", 8.5)
            for v, w in zip(fila, anchos):
                self.cell(w, 6.5, _t(v))
            self.ln(); self.set_draw_color(226, 232, 240); self.line(15, self.get_y(), self.w - 15, self.get_y())
        self.ln(2)


def _bloque_verificacion(pdf: "_Informe", verificacion):
    """Código QR para comprobar que el informe es auténtico (lo emitió Orthosync y no fue alterado)."""
    if not verificacion:
        return
    import qrcode
    url, codigo = verificacion
    qr = qrcode.QRCode(border=1, box_size=8, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(url); qr.make(fit=True)
    img = qr.make_image(fill_color=(11, 43, 104), back_color="white").convert("RGB")
    lado = 26
    if pdf.get_y() + lado + 6 > pdf.h - 22:
        pdf.add_page()
    y = pdf.get_y() + 4
    pdf.set_draw_color(220, 227, 240); pdf.rect(15, y - 2, pdf.w - 30, lado + 4)
    pdf.image(img, x=17, y=y, w=lado, h=lado)
    pdf.set_xy(17 + lado + 4, y + 2); pdf.set_font("Helvetica", "B", 9.5); pdf.set_text_color(*AZUL_OSCURO)
    pdf.cell(0, 5, _t("Verificación de autenticidad"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(17 + lado + 4); pdf.set_font("Helvetica", "", 8.5); pdf.set_text_color(*TINTA)
    pdf.multi_cell(pdf.w - 30 - lado - 10, 4.3, _t(
        "Escanea el código para confirmar que este informe fue emitido por Orthosync. En la página de verificación "
        "también puedes subir este PDF para comprobar que no fue modificado."), new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(17 + lado + 4); pdf.set_font("Courier", "B", 9); pdf.set_text_color(*AZUL)
    pdf.cell(0, 5, _t(f"Código: {codigo}"))
    pdf.set_text_color(*TINTA); pdf.set_y(y + lado + 4)


def _corto(e) -> str:
    """Resultado del sistema en pocas palabras, para la tabla de evolución."""
    if e.estado_analisis != "listo":
        return "Sin análisis"
    if not e.sospechoso:
        return "Sin hallazgos"
    if e.p_maligno is None:
        return "Lesión sospechosa"
    return "Sospecha de malignidad" if "malign" in (e.conclusion_sistema or "") else "Sospecha de benignidad"


def _abrir(carpeta, nombre):
    from ..core.almacen import abrir_imagen
    ruta = os.path.join(carpeta, nombre + ".png")
    return abrir_imagen(ruta) if os.path.exists(ruta) else None


def _datos_paciente(pdf, paciente, estudio):
    edad = _edad(paciente.fecha_nacimiento, estudio.fecha_estudio)
    pdf.datos([("Paciente", f"{paciente.nombres} {paciente.apellidos}"), ("Expediente", paciente.codigo),
               ("Documento", paciente.documento or "-"),
               ("Edad al estudio", f"{edad} años" if edad is not None else "-"),
               ("Sexo", {"F": "Femenino", "M": "Masculino"}.get(paciente.sexo or "", "-")),
               ("Fecha del estudio", _f(estudio.fecha_estudio))], columnas=3)


def informe_medico(estudio, paciente, medico, carpeta, imagen_3d: Image.Image | None = None, verificacion=None) -> bytes:
    e = estudio
    pdf = _Informe("Informe de apoyo diagnóstico", f"emitido el {_ahora():%d/%m/%Y %H:%M}")
    pdf.add_page()
    pdf.seccion("Datos del estudio"); _datos_paciente(pdf, paciente, e)
    pdf.datos([("Archivo", e.archivo_original), ("Estudio n.º", str(e.id))], columnas=3)

    pdf.seccion("Resultado del sistema")
    if e.estado_analisis != "listo":
        pdf.parrafo("Este estudio no fue analizado por el sistema (modelos no disponibles o imagen no válida).")
    else:
        maligno = e.p_maligno is not None and "maligno" in (e.conclusion_sistema or "").lower()
        pdf.caja(e.conclusion_sistema, (254, 226, 226) if maligno else ((254, 243, 199) if e.sospechoso else (220, 252, 231)),
                 (153, 27, 27) if maligno else ((146, 64, 14) if e.sospechoso else (22, 101, 52)))
        sugerido = ", ".join(f"{HUESOS.get(h, h)} ({p * 100:.0f} %)" for h, p in list((e.hueso_sugerido or {}).items())[:2])
        pdf.datos([("Confianza de lesión tumoral", _pct(e.p_tumor)), ("Confianza de malignidad", _pct(e.p_maligno)),
                   ("Zonas marcadas por el detector", str(sum(1 for c in (e.cajas or []) if c[4] > 0)) if e.cajas is not None else "-"),
                   ("Hueso sugerido", sugerido or "-")], columnas=2)
        pdf.imagenes([(_abrir(carpeta, "cajas"), "Radiografía y zona detectada"),
                      (_abrir(carpeta, "calor"), "Mapa de calor (Grad-CAM)")])
        pdf.set_font("Helvetica", "I", 8); pdf.set_text_color(*GRIS)
        pdf.parrafo("El mapa de calor muestra la región que más influyó en la clasificación; no delimita la lesión. "
                    "Un recuadro ámbar indica una ubicación aproximada tomada del mapa de calor.", tam=8, estilo="I")
        pdf.set_text_color(*TINTA)

    pdf.seccion("Valoración del médico")
    if not e.opinion:
        pdf.parrafo("Pendiente de valoración.")
    else:
        z = e.zona_3d or {}
        tipo = z.get("tipo") or ({"maligno": "cavidad", "benigno": "crecimiento"}.get(e.opinion) if z else None)
        pdf.datos([("Opinión", OPINIONES.get(e.opinion, e.opinion)), ("Evolución", EVOLUCIONES.get(e.evolucion or "", "-")),
                   ("Hueso", HUESOS.get(e.hueso or "", "-") + (f" {e.lado}" if e.lado else "")),
                   ("Aspecto de la lesión (3D)", TIPOS.get(tipo or "", "-"))], columnas=2)
        if e.proximo_control:
            pdf.datos([("Próximo control", _f(e.proximo_control))], columnas=2)
        for titulo, texto in (("Tratamiento indicado", e.tratamiento), ("Notas clínicas", e.comentario),
                              ("Mensaje para el paciente", e.mensaje_paciente)):
            if texto:
                pdf.set_font("Helvetica", "", 8); pdf.set_text_color(*GRIS); pdf.cell(0, 4, _t(titulo), new_x="LMARGIN", new_y="NEXT")
                pdf.set_text_color(*TINTA); pdf.parrafo(texto); pdf.ln(1.5)
    if imagen_3d is not None:
        pdf.imagenes([(imagen_3d, "Ilustración 3D de la zona afectada (no es una reconstrucción del hueso real)")], alto_max=75)

    anteriores = [x for x in paciente.estudios]
    if len(anteriores) > 1:
        pdf.seccion("Evolución del paciente")
        filas = [(_f(x.fecha_estudio), _corto(x), OPINIONES.get(x.opinion or "", "Sin valorar"),
                  EVOLUCIONES.get(x.evolucion or "", "-"), "-" if x.area_lesion is None else f"{x.area_lesion * 100:.2f} %")
                 for x in anteriores]
        pdf.tabla(["Fecha", "Resultado del sistema", "Opinión del médico", "Evolución", "Zona marcada"], filas,
                  [22, 66, 46, 24, 22], resaltar=[x.id for x in anteriores].index(e.id))
        pdf.parrafo("La zona marcada es la fracción de la imagen que ocupa la lesión detectada; es una medida relativa "
                    "que depende del encuadre de cada radiografía.", tam=8, estilo="I")

    # firma
    if pdf.get_y() > pdf.h - 55:
        pdf.add_page()
    pdf.ln(14); x = pdf.w - 15 - 75
    pdf.set_draw_color(*TINTA); pdf.line(x, pdf.get_y(), pdf.w - 15, pdf.get_y()); pdf.ln(1.5)
    pdf.set_x(x); pdf.set_font("Helvetica", "B", 10); pdf.cell(75, 5, _t(medico.nombre if medico else "-"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(x); pdf.set_font("Helvetica", "", 8.5); pdf.set_text_color(*GRIS)
    pdf.cell(75, 4.5, _t("Traumatólogo" + (f" · valorado el {_f(e.valorado_en)}" if e.valorado_en else "")), align="C")
    pdf.set_text_color(*TINTA); pdf.ln(8)
    _bloque_verificacion(pdf, verificacion)
    return bytes(pdf.output())


def informe_paciente(estudio, paciente, carpeta, verificacion=None) -> bytes:
    e = estudio
    pdf = _Informe("Resumen de tu estudio", f"emitido el {_ahora():%d/%m/%Y}")
    pdf.add_page()
    pdf.seccion("Tus datos"); _datos_paciente(pdf, paciente, e)
    pdf.seccion("Lo que dice tu médico")
    if e.evolucion:
        pdf.caja(f"Evolución: {EVOLUCIONES.get(e.evolucion, e.evolucion)}")
    pdf.parrafo(e.mensaje_paciente or "Tu médico aún no dejó un mensaje para este estudio.", tam=11)
    if e.tratamiento:
        pdf.ln(2); pdf.parrafo("Tratamiento indicado", tam=9, estilo="B"); pdf.parrafo(e.tratamiento)
    pdf.seccion("Tu radiografía")
    pdf.imagenes([(_abrir(carpeta, "radiografia"), f"Radiografía del {_f(e.fecha_estudio)}")], alto_max=120)
    pdf.ln(2)
    pdf.parrafo("Este resumen fue revisado por tu médico. Ante cualquier duda, consúltalo en tu próxima cita.", tam=9, estilo="I")
    if e.proximo_control:
        pdf.ln(2); pdf.caja(f"Tu próximo control: {_f(e.proximo_control)}")
    _bloque_verificacion(pdf, verificacion)
    return bytes(pdf.output())
