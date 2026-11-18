"""Configuración de las pruebas: conecta el servicio de inferencia (carpeta inferencia/) en memoria."""
import os, sys, tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(RAIZ, "backend"))
sys.path.insert(1, os.path.join(RAIZ, "inferencia"))
os.environ.setdefault("ORTHOSYNC_MODELOS", os.path.join(tempfile.mkdtemp(), "sin_modelos"))


def conectar_cnn_en_memoria():
    from fastapi.testclient import TestClient

    from app.integraciones import inferencia
    from cnn.main import app as app_cnn
    inferencia.usar_cliente(TestClient(app_cnn))
