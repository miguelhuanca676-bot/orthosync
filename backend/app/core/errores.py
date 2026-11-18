"""Errores del sistema. Los servicios lanzan estos errores (sin depender de FastAPI) y main.py los
convierte en respuestas HTTP con un mensaje claro para el usuario."""


class ErrorSistema(Exception):
    estado = 400

    def __init__(self, mensaje: str = ""):
        super().__init__(mensaje or self.__class__.mensaje_por_defecto)
        self.mensaje = mensaje or self.__class__.mensaje_por_defecto

    mensaje_por_defecto = "Solicitud no válida"


class DatoInvalido(ErrorSistema):        # el pedido no cumple una regla (400)
    estado = 400


class NoAutenticado(ErrorSistema):       # falta iniciar sesión o venció (401)
    estado = 401
    mensaje_por_defecto = "Debes iniciar sesión"


class Prohibido(ErrorSistema):           # hay sesión pero falta un paso previo (403)
    estado = 403
    mensaje_por_defecto = "No puedes hacer esto todavía"


class NoEncontrado(ErrorSistema):        # no existe O no tienes permiso: no se distingue a propósito (404)
    estado = 404
    mensaje_por_defecto = "No encontrado"


class Conflicto(ErrorSistema):           # ya existe (409)
    estado = 409


class ArchivoGrande(ErrorSistema):       # 413
    estado = 413


class DemasiadosIntentos(ErrorSistema):  # 429
    estado = 429
    mensaje_por_defecto = "Demasiados intentos. Espera unos minutos."
