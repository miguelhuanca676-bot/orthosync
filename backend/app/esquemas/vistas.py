"""Cómo se muestra cada registro hacia afuera. Nunca salen los id internos: solo identificadores aleatorios."""
from ..db.modelos import Estudio, Paciente, Usuario
from ..dominio.reglas import es_menor

_OCULTOS = {"id", "uid", "carpeta", "paciente_id", "medico_id"}


def usuario(u: Usuario) -> dict:
    return {"id": u.id, "nombre": u.nombre, "correo": u.correo, "rol": u.rol, "activo": u.activo,
            "debe_cambiar_clave": bool(u.debe_cambiar_clave),
            "acepto_terminos": bool(u.acepto_terminos_en) if u.rol == "paciente" else True}


def paciente(p: Paciente, tiene_cuenta: bool | None = None) -> dict:
    d = {"id": p.uid, "codigo": p.codigo, "nombres": p.nombres, "apellidos": p.apellidos,
         "documento": p.documento, "fecha_nacimiento": p.fecha_nacimiento, "sexo": p.sexo, "telefono": p.telefono,
         "tutor_nombre": p.tutor_nombre, "tutor_documento": p.tutor_documento,
         "consentimiento_en": p.consentimiento_en, "es_menor": es_menor(p.fecha_nacimiento)}
    if tiene_cuenta is not None:
        d["tiene_cuenta"] = tiene_cuenta
    return d


def estudio(e: Estudio) -> dict:
    """Vista completa, solo para el traumatólogo."""
    d = {c.name: getattr(e, c.name) for c in Estudio.__table__.columns if c.name not in _OCULTOS}
    d.update(id=e.uid, paciente_id=e.paciente.uid)
    return d


def estudio_para_paciente(e: Estudio) -> dict:
    """Lo que ve el paciente: sin porcentajes ni resultados sin validar."""
    return {"id": e.uid, "fecha_estudio": e.fecha_estudio, "hueso": e.hueso, "lado": e.lado,
            "evolucion": e.evolucion, "mensaje": e.mensaje_paciente, "tratamiento": e.tratamiento,
            "zona_3d": e.zona_3d if e.opinion in ("benigno", "maligno") else None,
            "hay_lesion": e.opinion in ("benigno", "maligno"), "proximo_control": e.proximo_control}
