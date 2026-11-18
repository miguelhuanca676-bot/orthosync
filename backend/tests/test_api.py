"""Pruebas automáticas de la API, incluidas pruebas de ATAQUE.  Ejecutar (dentro de backend/):  pytest -q

El servicio de inferencia (la CNN) se conecta EN MEMORIA, sin red (ver conftest.py).
Si ORTHOSYNC_MODELOS apunta a modelos ONNX, también se prueba el análisis real.
Para probar contra PostgreSQL:  ORTHOSYNC_BD_PRUEBAS=postgresql://... pytest -q"""
import base64, hashlib, io, os, shutil, tempfile, zipfile
from datetime import date

import jwt
import numpy as np
import pytest
from PIL import Image, ImageDraw

_tmp = tempfile.mkdtemp()
os.environ["ORTHOSYNC_BD"] = os.environ.get("ORTHOSYNC_BD_PRUEBAS") or "sqlite:///" + os.path.join(_tmp, "prueba.db")
os.environ["ORTHOSYNC_ARCHIVOS"] = os.path.join(_tmp, "archivos")
os.environ["ORTHOSYNC_SECRETOS"] = os.path.join(_tmp, "secretos")
os.environ.setdefault("ORTHOSYNC_MODELOS", os.path.join(_tmp, "sin_modelos"))

from fastapi.testclient import TestClient  # noqa: E402

from conftest import conectar_cnn_en_memoria  # noqa: E402

conectar_cnn_en_memoria()

from app.core import config  # noqa: E402
from app.core.seguridad import COOKIE, _fallos_ip  # noqa: E402
from app.main import app  # noqa: E402

HAY_MODELOS = os.path.exists(os.path.join(os.environ["ORTHOSYNC_MODELOS"], "info.json"))
CSRF = {"X-Orthosync": "1"}
NACIDO_ADULTO, NACIDO_MENOR = "1990-05-01", str(date(date.today().year - 10, 1, 1))


def radiografia(ancho=500, alto=700) -> Image.Image:
    rng = np.random.default_rng(1)
    img = Image.fromarray(rng.normal(50, 10, (alto, ancho)).clip(0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    d.rectangle([ancho * 0.4, 0, ancho * 0.6, alto], fill=180)
    d.ellipse([ancho * 0.4, alto * 0.4, ancho * 0.62, alto * 0.55], fill=90)
    return img


def como_png(img) -> bytes:
    b = io.BytesIO(); img.save(b, "PNG"); return b.getvalue()


def pdf_con_imagen_incrustada() -> bytes:
    import pymupdf
    doc = pymupdf.open(); pag = doc.new_page()
    pag.insert_text((50, 50), "Centro de Imagenologia - Informe radiologico")
    pag.insert_image(pymupdf.Rect(60, 90, 400, 560), stream=como_png(radiografia()))
    return doc.tobytes()


def pdf_escaneado() -> bytes:
    import pymupdf
    pagina = Image.new("L", (1240, 1754), 255)
    d = ImageDraw.Draw(pagina)
    for i in range(6):
        d.text((100, 60 + i * 30), "Paciente: FICTICIO   Estudio: Rx de femur   " * 2, fill=0)
    pagina.paste(radiografia(600, 900), (320, 400))
    doc = pymupdf.open(); pag = doc.new_page(width=595, height=842)
    pag.insert_image(pag.rect, stream=como_png(pagina))
    return doc.tobytes()


def nuevo_cliente() -> TestClient:
    c = TestClient(app); c.headers.update(CSRF); return c


def entrar(correo, clave, nueva=None) -> TestClient:
    """Inicia sesión (cookie). Si el sistema exige cambiar la contraseña, la cambia."""
    c = nuevo_cliente()
    r = c.post("/api/auth/login", json={"correo": correo, "clave": clave})
    assert r.status_code == 200, r.text
    assert COOKIE in r.cookies and "token" not in r.json()            # la sesión NO viaja en el cuerpo
    if r.json()["debe_cambiar_clave"]:
        assert c.post("/api/auth/cambiar-clave", json={"clave_actual": clave, "clave_nueva": nueva or "Nueva12345"}).status_code == 200
    return c


@pytest.fixture(scope="module")
def principal():
    with TestClient(app) as c:      # arranca la aplicación (crea tablas y administrador)
        yield c
    shutil.rmtree(_tmp, ignore_errors=True)


@pytest.fixture(scope="module")
def cab(principal):
    admin = entrar(config.ADMIN_CORREO, config.ADMIN_CLAVE, "AdminSeguro2026")
    for nombre, correo, rol in (("Dra. Prueba", "doc@clinica.com", "traumatologo"), ("Recepción", "rec@clinica.com", "recepcion")):
        r = admin.post("/api/usuarios", json={"nombre": nombre, "correo": correo, "rol": rol, "clave": "Inicial123"})
        assert r.status_code == 201, r.text
    return {"admin": admin, "doc": entrar("doc@clinica.com", "Inicial123", "Doctora2026"),
            "rec": entrar("rec@clinica.com", "Inicial123", "Recepcion2026")}


# ---------------------------------------------------------------- sesión y cabeceras
def test_administrador_inicial_debe_cambiar_clave(principal):
    c = nuevo_cliente()
    r = c.post("/api/auth/login", json={"correo": config.ADMIN_CORREO, "clave": config.ADMIN_CLAVE})
    if r.status_code == 200:      # (si otra prueba ya la cambió, la clave inicial ya no sirve)
        assert r.json()["debe_cambiar_clave"] is True
        assert c.get("/api/usuarios").status_code == 403


def test_cabeceras_de_seguridad_y_documentacion_oculta(principal):
    r = principal.get("/api/salud")
    for h in ("content-security-policy", "x-frame-options", "x-content-type-options", "referrer-policy"):
        assert h in r.headers
    assert r.headers["cache-control"] == "no-store"
    assert "modelos" not in r.json()                                  # no revela detalles internos
    for ruta in ("/docs", "/openapi.json", "/redoc"):
        assert principal.get(ruta).status_code == 404


def test_sin_sesion_y_tokens_falsos(principal, cab):
    c = nuevo_cliente()
    assert c.get("/api/pacientes").status_code == 401
    falso = jwt.encode({"sub": "1", "ver": 0, "exp": 9999999999}, "clave-inventada", algorithm="HS256")
    assert c.get("/api/usuarios", headers={"Authorization": "Bearer " + falso}).status_code == 401
    c.cookies.set(COOKIE, falso)
    assert c.get("/api/auth/yo").status_code == 401


def test_csrf_sin_cabecera_se_rechaza(principal, cab):
    c = TestClient(app)    # sin la cabecera X-Orthosync
    assert c.post("/api/auth/login", json={"correo": "doc@clinica.com", "clave": "Doctora2026"}).status_code == 403


def test_politica_de_contrasenas(principal, cab):
    r = cab["admin"].post("/api/usuarios", json={"nombre": "Débil", "correo": "debil@c.com", "rol": "recepcion", "clave": "solotexto"})
    assert r.status_code == 400


# ---------------------------------------------------------------- escalada de privilegios: siempre "No encontrado"
def test_roles_reciben_no_encontrado(principal, cab):
    for quien in ("doc", "rec"):
        for ruta in ("/api/usuarios", "/api/admin/auditoria", "/api/admin/estadisticas", "/api/admin/solicitudes"):
            r = cab[quien].get(ruta)
            assert r.status_code == 404 and r.json()["detail"] == "No encontrado", (quien, ruta)
    assert cab["rec"].post("/api/usuarios", json={"nombre": "X", "correo": "x@c.com", "rol": "administrador",
                                                   "clave": "Clave12345"}).status_code == 404


def test_no_se_puede_crear_un_administrador_paciente(principal, cab):
    r = cab["admin"].post("/api/usuarios", json={"nombre": "X", "correo": "x@c.com", "rol": "paciente", "clave": "Clave12345"})
    assert r.status_code in (400, 422)
    yo = cab["admin"].get("/api/auth/yo").json()["id"]
    assert cab["admin"].patch(f"/api/usuarios/{yo}", json={"activo": False}).status_code == 400


# ---------------------------------------------------------------- pacientes, consentimiento y menores
@pytest.fixture(scope="module")
def paciente(principal, cab):
    base = {"nombres": "Ana", "apellidos": "Ficticia", "fecha_nacimiento": NACIDO_MENOR, "sexo": "F"}
    assert cab["rec"].post("/api/pacientes", json=base).status_code == 400                         # sin consentimiento
    assert cab["rec"].post("/api/pacientes", json={**base, "consentimiento": True}).status_code == 400   # menor sin tutor
    r = cab["rec"].post("/api/pacientes", json={**base, "consentimiento": True, "tutor_nombre": "Rosa Ficticia"})
    assert r.status_code == 201, r.text
    p = r.json()
    assert p["codigo"] == "P-0001" and p["es_menor"] and p["consentimiento_en"]
    assert len(p["id"]) >= 16 and not p["id"].isdigit()                                          # id aleatorio
    return p


def test_identificadores_no_adivinables(principal, cab, paciente):
    for intento in ("1", "2", "P-0001", "../../etc/passwd", "%27%20OR%201=1"):
        assert cab["doc"].get(f"/api/pacientes/{intento}").status_code == 404


def test_recepcion_no_ve_lo_clinico(principal, cab, paciente):
    pid = paciente["id"]
    assert cab["rec"].get("/api/pacientes?buscar=fict").json()[0]["id"] == pid
    assert cab["rec"].get(f"/api/pacientes/{pid}/estudios").status_code == 404
    assert cab["admin"].get(f"/api/pacientes/{pid}/estudios").status_code == 404
    r = cab["rec"].post(f"/api/pacientes/{pid}/estudios", files={"archivo": ("rx.png", como_png(radiografia()), "image/png")})
    assert r.status_code == 404


@pytest.fixture(scope="module")
def estudios(principal, cab, paciente):
    pid = paciente["id"]; res = []
    for nombre, datos, fecha in (("rx1.png", como_png(radiografia()), "2026-01-10"),
                                 ("informe.pdf", pdf_con_imagen_incrustada(), "2026-04-10"),
                                 ("escaneado.pdf", pdf_escaneado(), "2026-07-10")):
        r = cab["doc"].post(f"/api/pacientes/{pid}/estudios", data={"fecha_estudio": fecha},
                            files={"archivo": (nombre, datos, "application/octet-stream")})
        assert r.status_code == 201, r.text
        res.append(r.json())
    return res


def test_subida_recorte_y_cifrado_en_disco(principal, cab, estudios):
    assert estudios[0]["evolucion"] == "primera" and estudios[1]["evolucion"] is None
    assert not any(k in estudios[0] for k in ("carpeta", "medico_id", "uid"))                    # nada interno
    tam = [Image.open(io.BytesIO(cab["doc"].get(f"/api/estudios/{e['id']}/imagen/radiografia").content)).size for e in estudios]
    assert tam[0] == (500, 700) and tam[1] == (500, 700)
    assert abs(tam[2][0] / tam[2][1] - 600 / 900) < 0.05
    # en el disco solo hay imágenes cifradas y ningún archivo original
    for raiz, _, archivos in os.walk(config.DIR_ARCHIVOS):
        for f in archivos:
            assert not f.startswith("original"), f
            assert not open(os.path.join(raiz, f), "rb").read(8).startswith(b"\x89PNG"), f


def test_archivos_no_validos(principal, cab, paciente):
    pid = paciente["id"]
    for nombre, datos in (("nota.txt", b"hola"), ("rota.png", b"no soy una imagen"), ("roto.pdf", b"%PDF-nada")):
        r = cab["doc"].post(f"/api/pacientes/{pid}/estudios", files={"archivo": (nombre, datos, "x/y")})
        assert r.status_code == 400, (nombre, r.text)


def test_dicom_no_conserva_datos_del_paciente(principal, cab, paciente):
    from pydicom.dataset import FileDataset, FileMetaDataset
    from pydicom.uid import ExplicitVRLittleEndian, generate_uid
    a = np.asarray(radiografia()).astype(np.uint16) * 16
    m = FileMetaDataset(); m.TransferSyntaxUID = ExplicitVRLittleEndian
    m.MediaStorageSOPClassUID = generate_uid(); m.MediaStorageSOPInstanceUID = generate_uid()
    b = io.BytesIO()
    ds = FileDataset(None, {}, file_meta=m, preamble=b"\0" * 128)
    ds.Rows, ds.Columns = a.shape; ds.BitsAllocated = 16; ds.BitsStored = 12; ds.HighBit = 11
    ds.PixelRepresentation = 0; ds.SamplesPerPixel = 1; ds.PhotometricInterpretation = "MONOCHROME2"
    ds.PixelData = a.tobytes(); ds.PatientName = "NOMBRE_SECRETO"
    ds.save_as(b)
    r = cab["doc"].post(f"/api/pacientes/{paciente['id']}/estudios", files={"archivo": ("placa.dcm", b.getvalue(), "application/dicom")})
    assert r.status_code == 201, r.text
    for raiz, _, archivos in os.walk(config.DIR_ARCHIVOS):
        for f in archivos:
            assert b"NOMBRE_SECRETO" not in open(os.path.join(raiz, f), "rb").read()
    assert cab["doc"].delete(f"/api/estudios/{r.json()['id']}").status_code == 204
    assert cab["doc"].get(f"/api/estudios/{r.json()['id']}").status_code == 404


def test_analisis(principal, cab, estudios):
    e = estudios[0]
    if not HAY_MODELOS:
        assert e["estado_analisis"] == "sin_modelos" and e["p_tumor"] is None
        return
    assert e["estado_analisis"] == "listo" and 0 <= e["p_tumor"] <= 1
    for tipo in ("cajas", "calor"):
        assert cab["doc"].get(f"/api/estudios/{e['id']}/imagen/{tipo}").status_code == 200
    r = cab["doc"].post(f"/api/estudios/{e['id']}/recortar", json={"x1": 0.2, "y1": 0.2, "x2": 0.8, "y2": 0.9})
    assert r.status_code == 200 and r.json()["estado_analisis"] == "listo"


# ---------------------------------------------------------------- portal: términos, privacidad, datos ajenos
@pytest.fixture(scope="module")
def pac(principal, cab, paciente, estudios):
    pid = paciente["id"]; e1, e2 = estudios[0]["id"], estudios[1]["id"]
    assert cab["doc"].post(f"/api/estudios/{e1}/publicar", json={"publicado": True}).status_code == 400
    r = cab["doc"].patch(f"/api/estudios/{e1}/valoracion", json={
        "hueso": "femur", "lado": "derecho", "opinion": "benigno", "tratamiento": "Control en 3 meses",
        "zona_3d": {"posicion": 0.8, "extension": 0.2}, "mensaje_paciente": "Lesión de aspecto benigno.", "publicar": True})
    assert r.status_code == 200 and r.json()["publicado"]                     # guardar la valoración la publica
    assert cab["doc"].patch(f"/api/estudios/{e2}/valoracion", json={"publicar": True}).status_code == 400   # sin opinión no se publica
    assert not cab["doc"].get(f"/api/estudios/{e2}").json()["publicado"]
    cab["doc"].patch(f"/api/estudios/{e2}/valoracion", json={"opinion": "benigno", "evolucion": "mejoria"})
    r = cab["rec"].post(f"/api/pacientes/{pid}/cuenta", json={"correo": "tutor@correo.com"})
    assert r.status_code == 201
    temporal = r.json()["clave_temporal"]
    c = nuevo_cliente()
    assert c.post("/api/auth/login", json={"correo": "tutor@correo.com", "clave": temporal}).json()["debe_cambiar_clave"]
    assert c.get("/api/portal/resumen").status_code == 403                       # primero debe cambiar la clave
    assert c.post("/api/auth/cambiar-clave", json={"clave_actual": temporal, "clave_nueva": "Familia2026"}).status_code == 200
    assert c.get("/api/portal/resumen").status_code == 403                       # luego aceptar los términos
    assert c.post("/api/portal/aceptar-terminos").json()["acepto_terminos"] is True
    return c


def test_portal_solo_ve_lo_publicado(principal, cab, estudios, pac):
    e1, e2 = estudios[0]["id"], estudios[1]["id"]
    portal = pac.get("/api/portal/resumen").json()
    assert [x["id"] for x in portal["estudios"]] == [e1]
    texto = str(portal)
    assert "p_tumor" not in texto and "p_maligno" not in texto and "cajas" not in texto
    assert portal["estudios"][0]["zona_3d"]["posicion"] == 0.8


def test_paciente_intenta_escalar_privilegios(principal, cab, estudios, pac):
    e1, e2 = estudios[0]["id"], estudios[1]["id"]
    for ruta in ("/api/pacientes", "/api/usuarios", "/api/admin/auditoria", "/api/admin/estadisticas",
                 f"/api/estudios/{e1}", f"/api/estudios/{e1}/imagen/calor", f"/api/estudios/{e2}/imagen/radiografia"):
        r = pac.get(ruta)
        assert r.status_code == 404 and r.json()["detail"] == "No encontrado", ruta
    assert pac.post("/api/usuarios", json={"nombre": "Yo", "correo": "yo@c.com", "rol": "administrador", "clave": "Clave12345"}).status_code == 404
    assert pac.get(f"/api/estudios/{e1}/imagen/radiografia").status_code == 200
    # un token "fabricado" con rol de administrador no sirve: está firmado y el rol se lee de la base de datos
    falso = jwt.encode({"sub": "1", "rol": "administrador", "ver": 0, "exp": 9999999999}, "otra-clave", algorithm="HS256")
    c = nuevo_cliente(); c.cookies.set(COOKIE, falso)
    assert c.get("/api/usuarios").status_code == 401


def test_exportar_y_solicitar_eliminacion(principal, cab, paciente, pac):
    r = pac.get("/api/portal/mis-datos")
    assert r.status_code == 200 and r.json()["datos_personales"]["codigo"] == paciente["codigo"]
    assert pac.post("/api/portal/solicitar-eliminacion", json={"motivo": "Ya no deseo usar el portal"}).status_code == 201
    assert pac.post("/api/portal/solicitar-eliminacion", json={}).status_code == 409
    assert pac.get("/api/portal/resumen").json()["solicitud_eliminacion"]["estado"] == "pendiente"
    sols = cab["admin"].get("/api/admin/solicitudes").json()
    assert sols[0]["estado"] == "pendiente"
    assert cab["admin"].post(f"/api/admin/solicitudes/{sols[0]['id']}/rechazar", json={"respuesta": "Retención legal del expediente"}).status_code == 200
    assert pac.get("/api/portal/resumen").json()["solicitud_eliminacion"]["estado"] == "rechazada"


def test_informes_pdf(principal, cab, estudios, pac):
    e1, e2 = estudios[0]["id"], estudios[1]["id"]
    b = io.BytesIO(); Image.new("RGB", (300, 200), (20, 60, 140)).save(b, "PNG")
    r = cab["doc"].post(f"/api/estudios/{e1}/informe", json={"imagen_3d": "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()})
    assert r.status_code == 200 and r.content.startswith(b"%PDF")
    assert cab["doc"].post(f"/api/estudios/{e2}/informe").content.startswith(b"%PDF")
    assert cab["admin"].post(f"/api/estudios/{e1}/informe").status_code == 404
    assert pac.get(f"/api/portal/estudios/{e1}/informe").content.startswith(b"%PDF")
    assert pac.get(f"/api/portal/estudios/{e2}/informe").status_code == 404


def test_evolucion_y_auditoria(principal, cab, paciente, pac):
    ev = cab["doc"].get(f"/api/pacientes/{paciente['id']}/evolucion").json()
    assert [p["fecha"] for p in ev["puntos"]] == ["2026-01-10", "2026-04-10", "2026-07-10"]
    acciones = {a["accion"] for a in cab["admin"].get("/api/admin/auditoria").json()}
    assert {"login", "crear_paciente", "subir_estudio", "valorar_estudio", "publicar_estudio", "aceptar_terminos",
            "exportar_datos", "solicitar_eliminacion", "borrar_estudio"} <= acciones


def test_cerrar_sesion_invalida_la_cookie(principal, cab):
    c = entrar("doc@clinica.com", "Doctora2026")
    robada = c.cookies.get(COOKIE)
    assert c.post("/api/auth/salir").status_code == 200
    otro = nuevo_cliente(); otro.cookies.set(COOKIE, robada)
    assert otro.get("/api/auth/yo").status_code == 401                # la cookie copiada ya no sirve
    cab["doc"] = entrar("doc@clinica.com", "Doctora2026")             # (cerrar sesión cierra todas las sesiones del usuario)


def test_bloqueo_por_intentos(principal, cab):
    _fallos_ip.clear()
    c = nuevo_cliente()
    for _ in range(config.INTENTOS_MAXIMOS):
        assert c.post("/api/auth/login", json={"correo": "rec@clinica.com", "clave": "mala"}).status_code == 401
    # ni siquiera con la contraseña correcta mientras dura el bloqueo
    assert c.post("/api/auth/login", json={"correo": "rec@clinica.com", "clave": "Recepcion2026"}).status_code == 401
    acciones = [a["accion"] for a in cab["admin"].get("/api/admin/auditoria").json()]
    assert "cuenta_bloqueada" in acciones
    _fallos_ip.clear()


# ---------------------------------------------------------------- funciones nuevas
def test_correccion_y_control(principal, cab, estudios, pac):
    e1 = estudios[0]["id"]
    assert cab["doc"].patch(f"/api/estudios/{e1}/valoracion", json={"cajas_medico": [[0.1, 0.1, 0.1, 0.1]]}).status_code == 400
    assert cab["doc"].patch(f"/api/estudios/{e1}/valoracion", json={"proximo_control": "2000-01-01"}).status_code == 400
    r = cab["doc"].patch(f"/api/estudios/{e1}/valoracion", json={"cajas_medico": [[0.6, 0.5, 0.2, 0.3]],
                                                                  "proximo_control": "2099-03-01"})
    assert r.status_code == 200 and r.json()["cajas_medico"] == [[0.2, 0.3, 0.6, 0.5]] and r.json()["corregido_en"]
    ultimo = max(estudios, key=lambda x: x["fecha_estudio"])["id"]           # la lista usa el último estudio del paciente
    cab["doc"].patch(f"/api/estudios/{ultimo}/valoracion", json={"proximo_control": "2099-03-01"})
    controles = cab["rec"].get("/api/controles").json()                     # recepción organiza las citas
    assert any(c["fecha_control"] == "2099-03-01" for c in controles)
    assert "p_tumor" not in str(controles) and "opinion" not in str(controles)
    assert pac.get("/api/controles").status_code == 404
    assert pac.get("/api/portal/resumen").json()["proximo_control"] == "2099-03-01"


def test_validacion_y_exportacion(principal, cab, estudios, pac):
    assert cab["admin"].get("/api/validacion").status_code == 200
    v = cab["doc"].get("/api/validacion").json()
    assert "uso_real" in v and v["uso_real"]["corregidos"] >= 1
    for c in (cab["rec"], pac):
        assert c.get("/api/validacion").status_code == 404
        assert c.get("/api/correcciones/exportar").status_code == 404
    assert cab["admin"].get("/api/correcciones/exportar").status_code == 404     # el administrador no ve lo clínico
    r = cab["doc"].get("/api/correcciones/exportar")
    assert r.status_code == 200
    z = zipfile.ZipFile(io.BytesIO(r.content))
    nombres = z.namelist()
    assert "casos.csv" in nombres and any(n.startswith("images/") for n in nombres)
    texto = z.read("casos.csv").decode()
    assert "Prueba" not in texto and "Quispe" not in texto                      # sin datos personales


def test_informe_con_qr_verificable(principal, cab, estudios, pac):
    e1 = estudios[0]["id"]
    pdf = cab["doc"].post(f"/api/estudios/{e1}/informe", json={}).content
    from app.db.base import Sesion as S
    from app.db.modelos import InformeEmitido
    from sqlalchemy import select as sel
    with S() as s:
        reg = s.scalars(sel(InformeEmitido).order_by(InformeEmitido.id.desc())).first()
        codigo, huella = reg.uid, reg.huella
    assert hashlib.sha256(pdf).hexdigest() == huella
    anonimo = nuevo_cliente()
    r = anonimo.get(f"/api/verificar/{codigo}")
    assert r.status_code == 200 and r.json()["huella"] == huella and "nombres" not in r.text
    assert anonimo.get("/api/verificar/codigo-inventado").status_code == 404
    assert pac.get(f"/api/portal/estudios/{e1}/informe").status_code == 200



def test_eliminacion_completa_de_datos(principal, cab):
    r = cab["doc"].post("/api/pacientes", json={"nombres": "Borrar", "apellidos": "Prueba", "fecha_nacimiento": NACIDO_ADULTO,
                                                 "consentimiento": True})
    p = r.json()
    cab["doc"].post(f"/api/pacientes/{p['id']}/estudios", files={"archivo": ("rx.png", como_png(radiografia()), "image/png")})
    clave = cab["doc"].post(f"/api/pacientes/{p['id']}/cuenta", json={"correo": "borrar@correo.com"}).json()["clave_temporal"]
    c = entrar("borrar@correo.com", clave, "Borrar2026"); c.post("/api/portal/aceptar-terminos")
    c.post("/api/portal/solicitar-eliminacion", json={})
    sol = next(s for s in cab["admin"].get("/api/admin/solicitudes").json() if s["codigo_paciente"] == p["codigo"])
    assert cab["admin"].post(f"/api/admin/solicitudes/{sol['id']}/ejecutar").status_code == 200
    assert cab["doc"].get(f"/api/pacientes/{p['id']}").status_code == 404
    assert c.get("/api/auth/yo").status_code == 401                     # su cuenta también se borró


def test_usuario_desactivado_pierde_acceso(principal, cab):
    usuarios = cab["admin"].get("/api/usuarios").json()
    rec = next(u for u in usuarios if u["rol"] == "recepcion")
    assert cab["admin"].patch(f"/api/usuarios/{rec['id']}", json={"activo": False}).status_code == 200
    assert cab["rec"].get("/api/pacientes").status_code == 401



def test_cnn_caida_no_impide_guardar(principal, cab, paciente):
    """Si el servicio de inferencia no responde, el estudio se guarda igual y se puede reanalizar luego."""
    import httpx
    from app.integraciones import inferencia
    anterior = inferencia._cliente
    inferencia.usar_cliente(httpx.Client(base_url="http://127.0.0.1:9", timeout=0.5))
    try:
        r = cab["doc"].post(f"/api/pacientes/{paciente['id']}/estudios",
                            files={"archivo": ("rx.png", como_png(radiografia()), "image/png")})
        assert r.status_code == 201 and r.json()["estado_analisis"] == "sin_servicio"
        assert cab["admin"].get("/api/admin/estadisticas").json()["modelos"] == {"servicio": False}
    finally:
        inferencia.usar_cliente(anterior)
    r2 = cab["doc"].post(f"/api/estudios/{r.json()['id']}/analizar")
    assert r2.status_code == 200 and r2.json()["estado_analisis"] in ("sin_modelos", "listo")
    assert cab["doc"].delete(f"/api/estudios/{r.json()['id']}").status_code == 204
