"""Pruebas del servicio de inferencia.  Ejecutar (dentro de inferencia/):  pytest -q"""
import io, os, tempfile

os.environ.setdefault("ORTHOSYNC_MODELOS", os.path.join(tempfile.mkdtemp(), "sin_modelos"))
os.environ["ORTHOSYNC_INFERENCIA_TOKEN"] = "token-de-prueba"

import numpy as np  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

from cnn.main import app  # noqa: E402

c = TestClient(app)
T = {"X-Token-Interno": "token-de-prueba"}


def _png():
    b = io.BytesIO(); Image.fromarray(np.full((64, 64), 120, np.uint8)).save(b, "PNG"); return b.getvalue()


def test_salud_sin_token():
    assert c.get("/salud").json()["ok"] is True


def test_rechaza_sin_token():
    assert c.post("/analizar", files={"imagen": ("x.png", _png(), "image/png")}).status_code == 401
    assert c.get("/info").status_code == 401


def test_sin_modelos_responde_estado():
    r = c.post("/analizar", headers=T, files={"imagen": ("x.png", _png(), "image/png")})
    assert r.status_code == 200 and r.json()["estado"] in ("sin_modelos", "listo")


def test_rechaza_archivo_que_no_es_imagen():
    r = c.post("/analizar", headers=T, files={"imagen": ("x.png", b"no soy imagen", "image/png")})
    assert r.status_code == 400
