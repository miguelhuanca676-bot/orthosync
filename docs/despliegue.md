# Publicar Orthosync en internet (paso a paso)

Todo es gratis y no pide tarjeta, salvo Oracle, que ya tienes. Las cuentas, contraseñas y claves las creas y escribes **tú**: no se comparten con nadie ni se pegan en el chat.

Orden y tiempo aproximado:

1. GitHub (15 min)
2. Cloudflare Pages (10 min)
3. Neon (5 min)
4. Servidor Oracle (25 min)
5. Conectar Cloudflare con el servidor (5 min)
6. UptimeRobot (5 min)
7. Modelos de Kaggle (cuando termines de reentrenar)

---

## 1. GitHub: subir el código

1. Crea la cuenta en https://github.com si no la tienes.
2. Arriba a la derecha: **+ → New repository**.
   - Repository name: `orthosync`
   - Visibility: **Public** (la licencia AGPL lo exige)
   - No marques «Add a README»: el proyecto ya trae uno.
   - **Create repository**.
3. Instala **Git para Windows** (https://git-scm.com/download/win), con las opciones por defecto.
4. Abre la carpeta `orthosync` en VS Code → *Terminal → Nueva terminal* y escribe, una línea a la vez (cambia `TU_USUARIO`):

   ```
   git init
   git config user.name "Juan Miguel Huanca"
   git config user.email "tu-correo@ejemplo.com"
   git add .
   git commit -m "Orthosync v5: arquitectura por capas"
   git branch -M main
   git remote add origin https://github.com/TU_USUARIO/orthosync.git
   git push -u origin main
   ```

   La primera vez se abre una ventana para iniciar sesión en GitHub desde el navegador.
5. Revisa en GitHub que se ven las carpetas `frontend`, `backend`, `inferencia`…, y que **no** aparecen `orthosync.db`, `secretos`, `archivos` ni `.venv`. El `.gitignore` los excluye.
6. Pestaña **Actions**: en unos minutos aparece «Pruebas» con ✓ verde.

## 2. Cloudflare Pages: crear el sitio

1. Crea la cuenta en https://dash.cloudflare.com/sign-up.
2. Menú izquierdo **Workers & Pages → Create application → Pages → Connect to Git**.
3. Autoriza a Cloudflare en GitHub. Elige **Only select repositories** → `orthosync`.
4. Configuración de compilación:

   | Campo | Valor |
   |---|---|
   | Project name | `orthosync` (si está ocupado, por ejemplo `orthosync-spinebolivia`) |
   | Production branch | `main` |
   | Framework preset | `None` |
   | Build command | `npm run build` |
   | Build output directory | `dist` |
   | Root directory (advanced) | `frontend` |

5. **Save and Deploy**. Al terminar verás tu dirección, por ejemplo `https://orthosync.pages.dev`. **Anótala.**
6. Si el nombre quedó distinto de `orthosync`, cambia la dirección en `frontend/.env.production`, `frontend/public/robots.txt` y `frontend/public/sitemap.xml`. Luego haz `git add .`, `git commit -m "Dirección del sitio"` y `git push`.

En este punto las páginas ya se ven, pero «Ingresar» todavía no funciona. Falta el servidor (pasos 3 a 5).

## 3. Neon: la base de datos

1. Crea la cuenta en https://neon.tech con **Sign up with GitHub**.
2. **Create project**:
   - Name: `orthosync`
   - Postgres version: 16 o la que venga por defecto
   - Region: la más cercana a tu servidor de Oracle. Por ejemplo, Oracle São Paulo → *AWS São Paulo*; Oracle Ashburn → *AWS US East (N. Virginia)*.
3. En el panel del proyecto: **Connect**.
   - Desactiva **Connection pooling**.
   - Copia la cadena que empieza con `postgresql://...neon.tech/neondb?sslmode=require...`.
4. **No la pegues en ningún chat.** Solo la vas a pegar en el servidor en el paso 4, cuando te la pida.

## 4. Servidor Oracle: API + CNN

1. Entra a https://cloud.oracle.com → ícono **>_** (Cloud Shell) arriba a la derecha.
2. Conéctate a tu máquina:

   ```
   ssh -i ~/.ssh/orthosync ubuntu@163.176.34.234
   ```

3. Ya dentro de la máquina, guarda la versión anterior y baja el código desde GitHub (cambia `TU_USUARIO`):

   ```
   sudo systemctl stop orthosync 2>/dev/null; sudo mv /opt/orthosync /opt/orthosync-v4 2>/dev/null
   sudo git clone https://github.com/TU_USUARIO/orthosync.git /opt/orthosync
   sudo bash /opt/orthosync/despliegue/oracle/instalar.sh
   ```

4. El instalador te pregunta dos cosas:
   - **Dirección de Cloudflare Pages:** la del paso 2 (`https://orthosync.pages.dev`).
   - **Neon:** pega la cadena del paso 3. No se ve mientras la pegas; es normal. Presiona Enter.
5. Espera de 10 a 15 minutos. El instalador:
   - instala la API y la CNN como dos servicios separados;
   - copia a Neon los datos que tenías en la v4;
   - conserva tus radiografías cifradas y los modelos que ya estaban.
6. Al final muestra un recuadro con **ORIGEN_API** y **PROXY_SECRETO**. Déjalo abierto para el paso 5.
   - Si es una instalación nueva, también muestra la contraseña temporal del administrador.
   - Si venías de la v4, tu contraseña de administrador sigue igual.

Comandos útiles en el servidor:

| Para | Comando |
|---|---|
| Ver si todo está encendido | `systemctl status orthosync-api orthosync-cnn caddy --no-pager` |
| Ver errores de la API | `journalctl -u orthosync-api -n 50 --no-pager` |
| Ver errores de la CNN | `journalctl -u orthosync-cnn -n 50 --no-pager` |
| Traer de GitHub los cambios ahora mismo | `sudo bash /opt/orthosync/despliegue/oracle/actualizar.sh` |
| Reiniciar todo | `sudo systemctl restart orthosync-cnn orthosync-api` |

## 5. Conectar Cloudflare con el servidor

1. Cloudflare → **Workers & Pages** → tu proyecto `orthosync` → **Settings → Variables and Secrets → Add**:

   | Type | Variable name | Value |
   |---|---|---|
   | Text | `ORIGEN_API` | lo que mostró el instalador (`https://163-176-34-234.sslip.io`) |
   | Secret | `PROXY_SECRETO` | lo que mostró el instalador |

   Agrégalas en **Production** y guarda.
2. **Deployments** → en el último despliegue, menú **⋯ → Retry deployment**. Las variables solo se aplican a despliegues nuevos.
3. Abre `https://orthosync.pages.dev/app` e inicia sesión. Debe funcionar todo: subir radiografía, análisis, informes PDF, portal.
4. Comprobación de seguridad: abre `https://163-176-34-234.sslip.io/app`. Debe llevarte a la dirección de Cloudflare, porque el servidor ya no atiende directo a nadie que no sea Cloudflare.

## 6. UptimeRobot: aviso si se cae

1. Crea la cuenta en https://uptimerobot.com (plan Free).
2. **New monitor**:
   - Monitor type: **HTTP(s)**
   - Friendly name: `Orthosync`
   - URL: `https://orthosync.pages.dev/api/salud`
   - Monitoring interval: 5 minutes
   - Alert contacts: tu correo
3. **Create monitor**.

Este chequeo recorre Cloudflare → servidor → API sin tocar Neon, así la base de datos puede dormir y no gasta su plan gratuito.

## 7. Modelos nuevos de Kaggle

Cuando el cuaderno de `entrenamiento/cuaderno/` termine en Kaggle, descarga el zip `orthosync_modelos.zip` desde la pestaña *Output*. Luego:

1. En Cloud Shell, menú ⚙ → **Upload** → elige el zip.
2. Ejecuta:

   ```
   scp -i ~/.ssh/orthosync ~/orthosync_modelos.zip ubuntu@163.176.34.234:/tmp/
   ssh -i ~/.ssh/orthosync ubuntu@163.176.34.234
   sudo rm -rf /var/lib/orthosync/modelos/* && sudo bash /opt/orthosync/despliegue/oracle/instalar.sh
   ```

   El instalador detecta el zip en `/tmp`, copia los modelos y reinicia la CNN. Las respuestas anteriores ya están guardadas y no las vuelve a preguntar.

## Si algo falla

| Síntoma | Causa probable | Solución |
|---|---|---|
| «Falta configurar ORIGEN_API y PROXY_SECRETO» | Variables no cargadas | Paso 5, incluido *Retry deployment* |
| «El servidor no responde» | API apagada o Caddy sin certificado | `systemctl status orthosync-api caddy` en el servidor |
| Ingresar no funciona y en el servidor aparece un error de Neon | Cadena mal copiada | Revisa `ORTHOSYNC_BD` con `sudo nano /etc/orthosync.env`, luego `sudo systemctl restart orthosync-api` |
| Estudios con «sin servicio» | La CNN está apagada | `sudo systemctl restart orthosync-cnn` y luego «Analizar de nuevo» en el estudio |
| Estudios con «sin modelos» | No hay `.onnx` en `/var/lib/orthosync/modelos` | Paso 7 |
| Las pruebas en GitHub salen ✗ | Un cambio rompió algo | Pestaña Actions → abre el error → corrige → `git push` |
