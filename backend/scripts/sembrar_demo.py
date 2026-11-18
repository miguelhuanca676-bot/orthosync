"""Crea usuarios y pacientes FICTICIOS para probar o presentar el sistema.
    python scripts/sembrar_demo.py   (dentro de backend/)
Todos los datos son inventados. NO usar en un sistema con pacientes reales.
En un servidor público usa ORTHOSYNC_DEMO_ALEATORIO=1: las contraseñas se generan al azar y se muestran una vez."""
import os
import secrets
from datetime import date

from sqlalchemy import select

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # carpeta backend/

from app.core.seguridad import cifrar_clave  # noqa: E402
from app.db.base import Sesion, ahora  # noqa: E402
from app.db.migraciones import crear_tablas  # noqa: E402
from app.db.modelos import Paciente, Usuario  # noqa: E402

USUARIOS = [("Dra. Valeria Rojas", "medico@demo.orthosync", "traumatologo", "Medico12345"),
            ("Carla Mendoza", "recepcion@demo.orthosync", "recepcion", "Recepcion12345")]
PACIENTES = [("Mateo", "Quispe Flores", "8457123", date(2011, 3, 14), "M", "Rosa Flores Mamani", "4512367"),
             ("Lucía", "Vargas Céspedes", "9034511", date(2008, 9, 2), "F", None, None),
             ("Andrés", "Mamani Rocha", "7765290", date(1995, 12, 20), "M", None, None)]

ALEATORIO = os.environ.get("ORTHOSYNC_DEMO_ALEATORIO") == "1"
clave_de = lambda fija: (secrets.token_urlsafe(9) + "7a") if ALEATORIO else fija
claves = {}

crear_tablas()
with Sesion() as bd:
    for nombre, correo, rol, clave in USUARIOS:
        if not bd.scalar(select(Usuario).where(Usuario.correo == correo)):
            claves[correo] = clave = clave_de(clave)
            bd.add(Usuario(nombre=nombre, correo=correo, rol=rol, clave_hash=cifrar_clave(clave), debe_cambiar_clave=False))
    if not bd.scalar(select(Paciente)):
        for nombres, apellidos, doc, nac, sexo, tutor, doc_tutor in PACIENTES:
            p = Paciente(codigo="", nombres=nombres, apellidos=apellidos, documento=doc, fecha_nacimiento=nac, sexo=sexo,
                         tutor_nombre=tutor, tutor_documento=doc_tutor, consentimiento_en=ahora())
            bd.add(p); bd.flush(); p.codigo = f"P-{p.id:04d}"
        bd.flush()
        p = bd.scalar(select(Paciente).order_by(Paciente.id))
        bd.add(Usuario(nombre=f"{p.nombres} {p.apellidos}", correo="paciente@demo.orthosync", rol="paciente",
                       paciente_id=p.id, clave_hash=cifrar_clave(claves.setdefault("paciente@demo.orthosync", clave_de("Paciente12345"))),
                       debe_cambiar_clave=False))
    bd.commit()
if ALEATORIO:
    print("Cuentas de demostración creadas (guarda estas contraseñas; no se vuelven a mostrar):")
    for correo, clave in claves.items():
        print(f"  {correo:28s} {clave}")
    raise SystemExit
print("Datos de demostración listos (SOLO para pruebas; contraseñas conocidas):")
print("  Traumatólogo : medico@demo.orthosync / Medico12345")
print("  Recepción    : recepcion@demo.orthosync / Recepcion12345")
print("  Paciente     : paciente@demo.orthosync / Paciente12345  (aceptará los términos al entrar)")
