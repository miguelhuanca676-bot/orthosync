# Orthosync · SpineBolivia

Sistema web de apoyo al traumatólogo para leer radiografías de hueso. Una red neuronal convolucional (CNN) detecta y localiza posibles tumores óseos. También estima si una lesión parece benigna o maligna. El médico revisa ese resultado, lo corrige y decide qué se publica para el paciente.

Proyecto de grado de **Juan Miguel Huanca Uruña** · Universidad Privada del Valle (UNIVALLE).

> Es un sistema de apoyo al diagnóstico. No sustituye el criterio médico ni el estudio histopatológico.

---

## Cómo está organizado

El sistema tiene cuatro partes independientes. Cada una vive en su carpeta y en la nube corre en su propio servicio:

| Carpeta | Qué es | Tecnología | Dónde corre en la nube |
|---|---|---|---|
| [`frontend/`](frontend/) | Las páginas que ve el usuario | React, TypeScript, Tailwind, Three.js | **Cloudflare Pages** |
| [`backend/`](backend/) | La API, organizada por capas (reglas, seguridad, datos) | Python, FastAPI, SQLAlchemy | **Oracle Cloud** (servicio `orthosync-api`) |
| [`inferencia/`](inferencia/) | La CNN, como servicio aparte | Python, ONNX Runtime | **Oracle Cloud** (servicio `orthosync-cnn`) |
| base de datos | Usuarios, pacientes, estudios y auditoría | PostgreSQL | **Neon** |
| [`entrenamiento/`](entrenamiento/) | Código que entrena los modelos | PyTorch, YOLO | **Kaggle** (GPU gratis) |

Servicios de apoyo:

- **GitHub** guarda el código.
- **GitHub Actions** prueba todo en cada cambio.
- **UptimeRobot** avisa si el sistema se cae.

El detalle está en [docs/arquitectura.md](docs/arquitectura.md).

```
orthosync/
├── frontend/          páginas (React)            → Cloudflare Pages
│   ├── src/           código de la aplicación (pantallas en src/paginas/)
│   └── functions/     puente /api → servidor (función de Cloudflare)
├── backend/           API por capas (FastAPI)     → Oracle
│   ├── app/rutas/         recibe el pedido HTTP
│   ├── app/servicios/     reglas del sistema
│   ├── app/repositorios/  consultas a la base de datos
│   ├── app/integraciones/ CNN, PDF, lectura de DICOM/PDF
│   ├── app/dominio/       reglas clínicas
│   ├── app/db/            tablas y migraciones
│   ├── app/core/          configuración, seguridad, cifrado
│   ├── scripts/           datos de prueba, migración a Neon
│   └── tests/             pruebas automáticas (incluye ataques)
├── inferencia/        servicio de la CNN           → Oracle
│   ├── cnn/               API interna /analizar y motor ONNX
│   └── modelos/           aquí van los .onnx (no se suben a GitHub)
├── entrenamiento/     entrenamiento de modelos      → Kaggle
│   ├── codigo/            scripts de entrenamiento y evaluación
│   └── cuaderno/          cuaderno .ipynb para Kaggle
├── despliegue/        instalación en Oracle y alternativa con Docker
├── scripts/           iniciar.bat, probar.bat (para tu laptop)
├── docs/              arquitectura, desarrollo, despliegue, configuración
└── .github/workflows/ pruebas automáticas en GitHub
```

## Ponerlo en marcha en tu laptop

1. Instala **Python 3.12** (marca «Add Python to PATH»). Si vas a cambiar el diseño, instala también **Node.js 22**.
2. Doble clic en **`scripts/iniciar.bat`**.
   - Se abre una ventana para la CNN (puerto 8001) y otra para la API (puerto 8000).
   - La primera vez instala las librerías, lo que tarda varios minutos.
3. Abre http://localhost:8000.

Cuentas de demostración (datos ficticios, solo en tu laptop):

| Rol | Correo | Contraseña |
|---|---|---|
| Administrador | admin@orthosync.local | Admin12345 (pide cambiarla) |
| Traumatólogo | medico@demo.orthosync | Medico12345 |
| Recepción | recepcion@demo.orthosync | Recepcion12345 |
| Paciente | paciente@demo.orthosync | Paciente12345 |

Para trabajar con el código en VS Code (qué archivo cambiar para cada cosa, depurar con F5, correr pruebas), lee [docs/desarrollo.md](docs/desarrollo.md).

## Publicarlo en internet

Puedes publicarlo gratis siguiendo la guía paso a paso de [docs/despliegue.md](docs/despliegue.md). El orden es GitHub → Cloudflare → Neon → Oracle → UptimeRobot.

## Pruebas

```
scripts\probar.bat
```

Hay 26 pruebas de la API (permisos por rol, ataques, privacidad, PDF con QR, CNN caída, etc.) y 4 del servicio de la CNN. En GitHub corren solas en cada cambio, contra SQLite y contra PostgreSQL.

## Licencia

[AGPL-3.0](LICENSE). Algunas librerías que usa el sistema (PyMuPDF, Ultralytics) tienen esta licencia, por eso el código es público.
