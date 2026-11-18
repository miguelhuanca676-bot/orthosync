# backend · API de Orthosync

FastAPI organizada por capas. La explicación completa está en [../docs/arquitectura.md](../docs/arquitectura.md#backend-por-capas).

```
app/main.py        arma la aplicación (middleware de seguridad, errores, rutas)
app/rutas/         HTTP: un archivo por tema (pacientes, estudios, portal…)
app/servicios/     reglas del sistema
app/repositorios/  consultas a la base de datos
app/esquemas/      qué entra (entradas.py) y qué sale (vistas.py)
app/dominio/       reglas clínicas puras
app/integraciones/ CNN (inferencia.py), PDF (pdf.py), lectura de DICOM/PDF (documentos.py)
app/db/            tablas (modelos.py), conexión (base.py), migraciones.py
app/core/          config.py, seguridad.py, almacen.py (cifrado), errores.py
scripts/           sembrar_demo.py, migrar_a_postgres.py
tests/             pytest (26 pruebas, incluye ataques)
```

Correr solo la API (dentro de `backend/`, con la CNN ya encendida):

```
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```
