"""Copia todos los datos de una base SQLite (la de tu laptop o la del servidor) a PostgreSQL (Neon).

Uso (dentro de backend/):
    python scripts/migrar_a_postgres.py  sqlite:///orthosync.db  "postgresql://usuario:clave@host/neondb?sslmode=require"

- Crea las tablas en el destino si no existen.
- Se niega a copiar si el destino ya tiene usuarios (para no mezclar datos).
- Conserva los identificadores y ajusta los contadores de PostgreSQL al final.
- Las radiografías NO están en la base de datos: siguen en la carpeta de archivos (cifradas).
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, func, select, text  # noqa: E402

if len(sys.argv) != 3:
    sys.exit(__doc__)
origen_url, destino_url = sys.argv[1], sys.argv[2]
os.environ["ORTHOSYNC_BD"] = destino_url   # para que las tablas se creen en el destino

from app.db.base import Base  # noqa: E402
from app.db import modelos  # noqa: E402,F401
from app.db.migraciones import crear_tablas  # noqa: E402

origen = create_engine(origen_url)
destino = create_engine(destino_url)
crear_tablas()

with destino.connect() as d:
    if d.scalar(select(func.count()).select_from(modelos.Usuario.__table__)):
        sys.exit("El destino ya tiene usuarios. Usa una base vacía para no mezclar datos.")

# orden que respeta las claves foráneas (usuarios <-> pacientes se resuelve después)
orden = ["pacientes", "usuarios", "estudios", "solicitudes_eliminacion", "informes_emitidos", "auditoria"]
with origen.connect() as o, destino.begin() as d:
    for nombre in orden:
        tabla = Base.metadata.tables[nombre]
        columnas_origen = {c[1] for c in o.execute(text(f"PRAGMA table_info({nombre})"))} if origen.dialect.name == "sqlite" else None
        filas = [dict(f._mapping) for f in o.execute(select(*[c for c in tabla.columns
                                                              if columnas_origen is None or c.name in columnas_origen]))]
        if nombre == "pacientes":
            creadores = {f["id"]: f.pop("creado_por", None) for f in filas}
        if filas:
            d.execute(tabla.insert(), filas)
        if nombre == "usuarios" and filas:
            for pid, uid in creadores.items():
                if uid:
                    d.execute(text("UPDATE pacientes SET creado_por = :u WHERE id = :p"), {"u": uid, "p": pid})
        if destino.dialect.name == "postgresql":
            d.execute(text(f"SELECT setval(pg_get_serial_sequence('{nombre}', 'id'), "
                           f"COALESCE((SELECT MAX(id) FROM {nombre}), 0) + 1, false)"))
        print(f"{nombre}: {len(filas)} filas")
print("Listo. Ahora apunta ORTHOSYNC_BD a la base de PostgreSQL y reinicia la API.")
