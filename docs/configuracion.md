# Variables de configuración

En tu laptop no hace falta definir ninguna. En el servidor están en `/etc/orthosync.env`. Ese archivo lo escribe el instalador, solo root puede leerlo y **nunca** se sube a GitHub.

## API (`backend/app/core/config.py`)

| Variable | Para qué | Por defecto (laptop) |
|---|---|---|
| `ORTHOSYNC_BD` | Base de datos. En la nube, la cadena de Neon | `sqlite:///backend/orthosync.db` |
| `ORTHOSYNC_BD_SIN_POOL` | `1` = no deja conexiones abiertas, para que Neon pueda dormir | `0` (con Neon se activa sola) |
| `ORTHOSYNC_ARCHIVOS` | Carpeta de radiografías (cifradas) | `backend/archivos` |
| `ORTHOSYNC_SECRETOS` | Claves de sesión y de cifrado. **Si se pierde, no se pueden abrir las radiografías** | `backend/secretos` |
| `ORTHOSYNC_INTERFAZ` | Carpeta del frontend compilado (solo en local) | `frontend/dist` |
| `ORTHOSYNC_INFERENCIA_URL` | Dónde está la CNN | `http://127.0.0.1:8001` |
| `ORTHOSYNC_INFERENCIA_TOKEN` | Clave interna API ↔ CNN (la misma en las dos) | vacía |
| `ORTHOSYNC_INFERENCIA_ESPERA_S` | Segundos máximos de espera al análisis | `180` |
| `ORTHOSYNC_PROXY_SECRETO` | Clave compartida con la función de Cloudflare | vacía |
| `ORTHOSYNC_PROXY` | `1` detrás de Caddy/Nginx | `0` |
| `ORTHOSYNC_HTTPS` | `1` = la cookie de sesión solo viaja por https | `0` |
| `ORTHOSYNC_SITIO` | Dirección pública (para el QR de los informes) | la del pedido |
| `ORTHOSYNC_ORIGENES` | Orígenes permitidos (CORS) | `http://localhost:5173` |
| `ORTHOSYNC_ADMIN_CORREO` / `ORTHOSYNC_ADMIN_CLAVE` | Primer administrador (debe cambiar la contraseña al entrar) | `admin@orthosync.local` / `Admin12345` |
| `ORTHOSYNC_HORAS_SESION` | Duración de la sesión | `8` |
| `ORTHOSYNC_HORAS_UTC` | Zona horaria de las fechas (Bolivia: -4) | `-4` |
| `ORTHOSYNC_DOCS` | `1` = documentación interactiva en `/docs` | `0` |

## CNN (`inferencia/cnn/config.py`)

| Variable | Para qué | Por defecto |
|---|---|---|
| `ORTHOSYNC_MODELOS` | Carpeta con los `.onnx` e `info.json` | `inferencia/modelos` |
| `ORTHOSYNC_INFERENCIA_TOKEN` | Clave interna que debe enviar la API | vacía (sin control, solo en local) |
| `ORTHOSYNC_POCA_MEMORIA` | `1` = un hilo y sin reservas de memoria (servidor de 1 GB) | `0` |

## Cloudflare Pages (Settings → Variables and Secrets)

| Variable | Valor |
|---|---|
| `ORIGEN_API` | `https://<ip-con-guiones>.sslip.io` |
| `PROXY_SECRETO` | El mismo valor que `ORTHOSYNC_PROXY_SECRETO` del servidor (tipo **Secret**) |

## Frontend (`frontend/.env.production`)

| Variable | Valor |
|---|---|
| `VITE_SITIO` | Dirección pública (metadatos para buscadores y redes sociales) |
