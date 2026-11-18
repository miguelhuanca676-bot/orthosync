"""Configuración del servicio de inferencia (la CNN)."""
import os

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))     # carpeta inferencia/
# Carpeta con los modelos ONNX y su info.json (salen del cuaderno de Kaggle)
DIR_MODELOS = os.environ.get("ORTHOSYNC_MODELOS", os.path.join(RAIZ, "modelos"))
# Clave que debe enviar la API en la cabecera X-Token-Interno. Vacía = solo para desarrollo local.
TOKEN = os.environ.get("ORTHOSYNC_INFERENCIA_TOKEN", "")
TAM_MAX_MB = 40
