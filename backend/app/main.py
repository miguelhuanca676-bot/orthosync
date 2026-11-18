"""API de Orthosync. Aquí solo se arma la aplicación: middleware, errores y rutas.

    rutas/         reciben el pedido HTTP y responden (delgadas)
    servicios/     reglas del sistema (qué se puede hacer y cómo)
    repositorios/  consultas a la base de datos
    integraciones/ servicios externos: CNN (inferencia), PDF, lectura de archivos
    dominio/       reglas clínicas puras (sin base de datos ni web)
    db/            conexión, tablas y migraciones
    core/          configuración, seguridad y almacenamiento cifrado

Ejecutar (dentro de backend/):  uvicorn app.main:app --reload
"""
import mimetypes, os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .core import config
from .core.almacen import cifrar_existentes
from .core.errores import ErrorSistema
from .db.base import Sesion
from .db.migraciones import crear_tablas
from .rutas import administracion, autenticacion, clinica, estudios, pacientes, portal
from .servicios.autenticacion import preparar_administrador

for tipo, ext in (("application/javascript", ".js"), ("text/css", ".css"), ("image/svg+xml", ".svg"),
                  ("image/webp", ".webp"), ("application/manifest+json", ".webmanifest")):
    mimetypes.add_type(tipo, ext)      # Windows a veces registra .js como texto plano


@asynccontextmanager
async def ciclo(_: FastAPI):
    crear_tablas()
    os.makedirs(config.DIR_ARCHIVOS, exist_ok=True)
    cifrar_existentes(config.DIR_ARCHIVOS)
    with Sesion() as bd:
        preparar_administrador(bd)
    yield


app = FastAPI(title=f"{config.NOMBRE_SISTEMA} API", version="2.0", lifespan=ciclo,
              docs_url="/docs" if config.DOCS else None, redoc_url=None,
              openapi_url="/openapi.json" if config.DOCS else None)
app.add_middleware(CORSMiddleware, allow_origins=config.ORIGENES_PERMITIDOS, allow_methods=["GET", "POST", "PATCH", "DELETE"],
                   allow_headers=["Content-Type", "X-Orthosync"], allow_credentials=True)


@app.exception_handler(ErrorSistema)
async def error_sistema(_: Request, err: ErrorSistema):
    return JSONResponse({"detail": err.mensaje}, status_code=err.estado)


CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; "
       "connect-src 'self'; font-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; "
       "form-action 'self'")


@app.middleware("http")
async def proteccion(request: Request, call_next):
    # Contra CSRF: toda petición que cambia datos debe traer una cabecera que solo nuestra página envía
    if (request.url.path.startswith("/api/") and request.method not in ("GET", "HEAD", "OPTIONS")
            and request.headers.get("x-orthosync") != "1"):
        return JSONResponse({"detail": "Solicitud no válida"}, status_code=403)
    r = await call_next(request)
    r.headers["X-Content-Type-Options"] = "nosniff"
    r.headers["X-Frame-Options"] = "DENY"
    r.headers["Referrer-Policy"] = "no-referrer"
    r.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
    r.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    r.headers["Content-Security-Policy"] = CSP
    if config.HTTPS:
        r.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if request.url.path.startswith("/api/"):
        r.headers["Cache-Control"] = r.headers.get("Cache-Control") if "private" in r.headers.get("Cache-Control", "") else "no-store"
    return r


for modulo in (clinica, autenticacion, administracion, pacientes, estudios, portal):
    app.include_router(modulo.r)


# ---------------------------------------------------------------- páginas (solo en local; en la nube las sirve Cloudflare)
if os.path.isdir(config.DIR_INTERFAZ):
    @app.get("/app", include_in_schema=False)
    def pagina_app():
        return FileResponse(os.path.join(config.DIR_INTERFAZ, "app.html"), headers={"Cache-Control": "no-cache"})

    @app.get("/sw.js", include_in_schema=False)
    def service_worker():      # siempre la versión más nueva, para que las actualizaciones lleguen
        return FileResponse(os.path.join(config.DIR_INTERFAZ, "sw.js"), media_type="application/javascript",
                            headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": "/"})

    app.mount("/", StaticFiles(directory=config.DIR_INTERFAZ, html=True), name="interfaz")
