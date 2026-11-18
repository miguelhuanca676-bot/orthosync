# Guía de desarrollo: dónde está cada cosa y cómo probarla

## 1. Abrir el proyecto

1. Instala **VS Code**, **Python 3.12**, **Git** y, para el diseño, **Node.js 22**.
2. En VS Code: *Archivo → Abrir carpeta…* y elige la carpeta `orthosync` (la raíz, no una subcarpeta).
3. VS Code te ofrecerá instalar las extensiones recomendadas (Python, Tailwind, GitHub Actions). Acepta.
4. Ejecuta una vez `scripts\iniciar.bat`. Crea los entornos `backend\.venv` e `inferencia\.venv` y la base de datos de prueba.

## 2. Tres formas de correr el sistema

| Para qué | Cómo | Dirección |
|---|---|---|
| Usarlo o mostrarlo | Doble clic en `scripts\iniciar.bat` | http://localhost:8000 |
| Corregir código Python con puntos de parada | VS Code → panel *Ejecutar y depurar* (Ctrl+Shift+D) → **Sistema completo** → F5 | http://localhost:8000 · documentación de la API en http://localhost:8000/docs |
| Cambiar el diseño y ver el cambio al guardar | Con el sistema encendido, doble clic en `scripts\frontend-dev.bat` | http://localhost:5173/app |

Con `iniciar.bat` o F5, la API se reinicia sola al guardar un archivo `.py`. La CNN no se reinicia sola: ciérrala y ábrela de nuevo.

Para probar el análisis con modelos reales, copia los `.onnx` y el `info.json` a `inferencia\modelos\`. Sin modelos, los estudios quedan como «sin modelos».

## 3. «Quiero cambiar…» → este archivo

### Lo que se ve (frontend/)

| Quiero cambiar… | Archivo |
|---|---|
| La página pública de inicio | `frontend/index.html` |
| Privacidad, términos, cookies, créditos | `frontend/privacidad.html`, `terminos.html`, `cookies.html`, `creditos.html` |
| Nombre, dirección y teléfono de la clínica | `frontend/public/clinica.js` |
| Colores, tipografía, modo oscuro | `frontend/src/estilos.css` |
| El menú lateral, la barra superior, botones comunes | `frontend/src/componentes.tsx` (`Marco`, `Encabezado`, `Dato`…) |
| Inicio de sesión y cambio de contraseña | `frontend/src/paginas/Acceso.tsx` |
| Lista de pacientes, ficha, subir radiografía | `frontend/src/paginas/Pacientes.tsx` |
| Pantalla del estudio (resultado de la CNN, valoración del médico, recuadros) | `frontend/src/paginas/Estudio.tsx` |
| Visor 3D del hueso | `frontend/src/Visor3D.tsx` y `frontend/src/hueso3d.ts` |
| Validación del modelo y controles programados | `frontend/src/paginas/Clinica.tsx` |
| Panel del administrador (usuarios, auditoría, solicitudes) | `frontend/src/paginas/Admin.tsx` |
| Portal del paciente | `frontend/src/paginas/Portal.tsx` |
| Qué pantalla corresponde a cada rol | `frontend/src/main.tsx` |
| Cómo se llama a la API | `frontend/src/api.ts` |

### Lo que se decide (backend/app/)

| Quiero cambiar… | Archivo |
|---|---|
| Una dirección de la API (`/api/...`) o qué rol puede usarla | `rutas/<tema>.py` |
| Una regla («solo se publica si hay opinión», «el menor necesita tutor») | `servicios/<tema>.py` o `dominio/reglas.py` |
| Los huesos, opiniones o evoluciones permitidas | `dominio/reglas.py` |
| Qué datos se aceptan en un formulario (largos, formatos) | `esquemas/entradas.py` |
| Qué datos se devuelven al navegador | `esquemas/vistas.py` |
| Una tabla o columna nueva | `db/modelos.py`. Las columnas nuevas se agregan solas al arrancar (`db/migraciones.py`) |
| Una consulta a la base de datos | `repositorios/<tema>.py` |
| El diseño de los informes PDF | `integraciones/pdf.py` |
| Cómo se leen PDF y DICOM | `integraciones/documentos.py` |
| Contraseñas, sesiones, bloqueo por intentos | `core/seguridad.py` |
| Valores por defecto y variables de entorno | `core/config.py` (lista completa en [configuracion.md](configuracion.md)) |

Los temas son: `autenticacion`, `usuarios`, `administracion`, `pacientes`, `estudios`, `clinica`, `informes` y `portal`.

### La CNN

| Quiero cambiar… | Archivo |
|---|---|
| Cómo se analiza una imagen (umbrales, cajas, mapa de calor) | `inferencia/cnn/motor.py` |
| La API interna de la CNN | `inferencia/cnn/main.py` |
| Cómo la API llama a la CNN | `backend/app/integraciones/inferencia.py` |
| El entrenamiento | `entrenamiento/codigo/*.py`, y luego `python entrenamiento/cuaderno/construir_cuaderno.py` para regenerar el cuaderno de Kaggle |

### Ejemplo: agregar «escápula» a la lista de huesos

1. `backend/app/dominio/reglas.py`: agrega `"escapula"` a `HUESOS`.
2. `backend/app/integraciones/pdf.py`: agrega su nombre bonito en `HUESOS`.
3. `frontend/src/api.ts`: agrega `escapula: "Escápula"` en `HUESOS` (de ahí sale la lista del formulario).
4. Ejecuta `scripts\probar.bat`.

## 4. Pruebas

- Todas: `scripts\probar.bat`.
- En VS Code: ícono del matraz (*Testing*) → ▶ en la prueba que quieras.
- Contra PostgreSQL: define `ORTHOSYNC_BD_PRUEBAS=postgresql://...` antes de `pytest`.

Cada vez que subes un cambio a GitHub, las pruebas corren solas (pestaña **Actions** del repositorio):

- ✓ verde: todo bien.
- ✗ roja: abre el detalle para ver qué prueba falló y por qué.

## 5. Subir un cambio

```
git add .
git commit -m "Describe el cambio"
git push
```

Después del `push`:

- Cloudflare vuelve a compilar el frontend en 1 o 2 minutos.
- El servidor de Oracle trae el cambio en menos de 10 minutos y reinicia solo lo que cambió (API o CNN).
- Para no esperar, en el servidor: `sudo bash /opt/orthosync/despliegue/oracle/actualizar.sh`.
