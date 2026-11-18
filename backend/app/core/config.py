"""Configuración de la API. Todo se cambia con variables de entorno (ver docs/configuracion.md).
En local no hace falta definir nada: se usan valores por defecto seguros para desarrollo."""
import os
import secrets

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # carpeta backend/

BASE_DATOS = os.environ.get("ORTHOSYNC_BD", "sqlite:///" + os.path.join(RAIZ, "orthosync.db"))
# 1 para no mantener conexiones abiertas (recomendado con bases de datos que se apagan solas, como Neon)
BD_SIN_POOL = os.environ.get("ORTHOSYNC_BD_SIN_POOL", "0") == "1"
DIR_ARCHIVOS = os.environ.get("ORTHOSYNC_ARCHIVOS", os.path.join(RAIZ, "archivos"))
# Interfaz ya compilada (frontend/dist). En local la API también la muestra; en la nube la sirve Cloudflare Pages.
DIR_INTERFAZ = os.environ.get("ORTHOSYNC_INTERFAZ", os.path.join(os.path.dirname(RAIZ), "frontend", "dist"))
# Carpeta con las claves secretas generadas automáticamente. NUNCA se comparte ni se sube a internet.
DIR_SECRETOS = os.environ.get("ORTHOSYNC_SECRETOS", os.path.join(RAIZ, "secretos"))


def _secreto(variable: str, archivo: str, generar) -> str:
    """Toma la clave de una variable de entorno; si no existe, la crea una sola vez y la guarda en secretos/."""
    if os.environ.get(variable):
        return os.environ[variable]
    os.makedirs(DIR_SECRETOS, exist_ok=True)
    ruta = os.path.join(DIR_SECRETOS, archivo)
    if not os.path.exists(ruta):
        with open(ruta, "w", encoding="ascii") as f:
            f.write(generar())
    with open(ruta, encoding="ascii") as f:
        return f.read().strip()


def _clave_fernet() -> str:
    from cryptography.fernet import Fernet
    return Fernet.generate_key().decode()


# Firma de las sesiones y cifrado de las radiografías guardadas en disco
CLAVE_SECRETA = _secreto("ORTHOSYNC_CLAVE", "sesiones.key", lambda: secrets.token_urlsafe(48))
CLAVE_ARCHIVOS = _secreto("ORTHOSYNC_CLAVE_ARCHIVOS", "archivos.key", _clave_fernet)
HORAS_SESION = int(os.environ.get("ORTHOSYNC_HORAS_SESION", "8"))

# 1 cuando el sistema se publique con HTTPS: la cookie de sesión solo viaja cifrada
HTTPS = os.environ.get("ORTHOSYNC_HTTPS", "0") == "1"
# 1 cuando el servidor está detrás de un proxy propio (Caddy/Nginx) que agrega X-Forwarded-For
PROXY = os.environ.get("ORTHOSYNC_PROXY", "0") == "1"
# Secreto compartido con la función de Cloudflare Pages que reenvía /api al servidor. Si llega correcto,
# se confía en la cabecera X-Cliente-IP (la IP real del visitante) para el control de intentos.
PROXY_SECRETO = os.environ.get("ORTHOSYNC_PROXY_SECRETO", "")
# 1 solo para desarrollo: muestra la documentación interactiva de la API en /docs
DOCS = os.environ.get("ORTHOSYNC_DOCS", "0") == "1"

# Primer administrador (se crea solo si no existe ninguno; debe cambiar la contraseña al entrar)
ADMIN_CORREO = os.environ.get("ORTHOSYNC_ADMIN_CORREO", "admin@orthosync.local")
ADMIN_CLAVE = os.environ.get("ORTHOSYNC_ADMIN_CLAVE", "Admin12345")

ORIGENES_PERMITIDOS = [o for o in os.environ.get(
    "ORTHOSYNC_ORIGENES", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o]

TAM_MAX_ARCHIVO_MB = 40
INTENTOS_MAXIMOS = 5            # intentos fallidos antes de bloquear la cuenta
MINUTOS_BLOQUEO = 15
# Diferencia horaria para mostrar fechas (Bolivia: UTC-4, sin horario de verano)
HORAS_UTC = float(os.environ.get("ORTHOSYNC_HORAS_UTC", "-4"))

# Servicio de inferencia (la CNN). Es otro proceso: la API lo llama por la red interna con una clave propia.
INFERENCIA_URL = os.environ.get("ORTHOSYNC_INFERENCIA_URL", "http://127.0.0.1:8001").rstrip("/")
INFERENCIA_TOKEN = os.environ.get("ORTHOSYNC_INFERENCIA_TOKEN", "")
INFERENCIA_ESPERA_S = float(os.environ.get("ORTHOSYNC_INFERENCIA_ESPERA_S", "180"))

# Dirección pública del sitio (para el código QR de los informes). Si no se define, se usa la del pedido.
SITIO = os.environ.get("ORTHOSYNC_SITIO", "").rstrip("/")

NOMBRE_SISTEMA = "Orthosync"
NOMBRE_CLINICA = "SpineBolivia"
AVISO = ("Sistema de apoyo al diagnóstico. No sustituye el criterio médico ni el estudio histopatológico. "
         "Los porcentajes expresan la confianza del modelo, no una probabilidad clínica.")
