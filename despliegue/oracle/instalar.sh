#!/usr/bin/env bash
# Instala (o actualiza a la v5) Orthosync en la máquina de Oracle (Ubuntu, 1 GB de RAM).
# Se ejecuta EN la máquina, como root:   sudo bash /opt/orthosync/despliegue/oracle/instalar.sh
#
# Deja corriendo dos servicios separados:
#   orthosync-api  (puerto interno 8000)  API por capas, base de datos en Neon
#   orthosync-cnn  (puerto interno 8001)  servicio de inferencia con los modelos ONNX
# y Caddy delante (https), que SOLO acepta pedidos que vienen de Cloudflare Pages (traen el secreto).
set -euo pipefail
APP=/opt/orthosync; DATOS=/var/lib/orthosync; ENV=/etc/orthosync.env
export DEBIAN_FRONTEND=noninteractive
[ "$(id -u)" = 0 ] || { echo "Ejecuta con sudo"; exit 1; }
[ -d $APP/.git ] || { echo "Primero clona el repositorio en $APP (ver docs/despliegue.md)"; exit 1; }

IP="$(curl -fs4 https://api.ipify.org || hostname -I | awk '{print $1}')"
DOMINIO="$(echo "$IP" | tr . -).sslip.io"

echo "==> Datos de tus cuentas (se guardan solo en este servidor, en $ENV)"
PAGINAS="$(grep -s '^ORTHOSYNC_SITIO=' $ENV | cut -d= -f2- || true)"
if [ -z "$PAGINAS" ] || [[ "$PAGINAS" == *sslip.io* ]]; then
  read -rp "Dirección de tu sitio en Cloudflare Pages (ej. https://orthosync.pages.dev): " PAGINAS
fi
PAGINAS="${PAGINAS%/}"
[[ "$PAGINAS" == https://* ]] || { echo "Debe empezar con https://"; exit 1; }
NEON="$(grep -s "^ORTHOSYNC_BD='postgresql" $ENV | cut -d= -f2- | tr -d "'" || true)"
if [ -z "$NEON" ]; then
  echo "Pega la cadena de conexión de Neon (no se mostrará en pantalla)."
  echo "Déjala vacía y presiona Enter para seguir con SQLite en este servidor."
  read -rsp "Neon: " NEON; echo
  NEON="${NEON#psql }"; NEON="${NEON//\'/}"; NEON="${NEON//\"/}"; NEON="$(echo "$NEON" | tr -d '[:space:]')"
  [ -z "$NEON" ] || [[ "$NEON" == postgresql://* ]] || { echo "La cadena de Neon debe empezar con postgresql://"; exit 1; }
fi

echo "==> 1/9 Memoria de intercambio"
if ! swapon --show | grep -q /swapfile; then
  fallocate -l 3G /swapfile && chmod 600 /swapfile && mkswap /swapfile >/dev/null && swapon /swapfile
  grep -q /swapfile /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi
echo 'vm.swappiness=60' > /etc/sysctl.d/90-orthosync.conf; sysctl -q -p /etc/sysctl.d/90-orthosync.conf

echo "==> 2/9 Paquetes del sistema"
apt-get update -qq
apt-get install -y -qq python3-venv python3-pip git curl unzip iptables-persistent >/dev/null
if ! command -v caddy >/dev/null; then
  apt-get install -y -qq caddy >/dev/null 2>&1 || {
    apt-get install -y -qq debian-keyring debian-archive-keyring apt-transport-https gnupg >/dev/null
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' > /etc/apt/sources.list.d/caddy-stable.list
    apt-get update -qq && apt-get install -y -qq caddy >/dev/null; }
fi

echo "==> 3/9 Usuario y carpetas de datos"
id orthosync >/dev/null 2>&1 || useradd --system --home $DATOS --shell /usr/sbin/nologin orthosync
mkdir -p $DATOS/archivos $DATOS/secretos $DATOS/modelos
git config --global --add safe.directory $APP

echo "==> 4/9 Entornos de Python (API y CNN por separado; tarda unos minutos)"
for parte in backend inferencia; do
  [ -x $APP/$parte/.venv/bin/python ] || python3 -m venv $APP/$parte/.venv
  $APP/$parte/.venv/bin/pip install -q --upgrade pip
  grep -viE '^(pytest|httpx)\b' $APP/$parte/requirements.txt > /tmp/req-$parte.txt || true
  [ $parte = backend ] && echo httpx >> /tmp/req-$parte.txt
  $APP/$parte/.venv/bin/pip install -q --no-cache-dir -r /tmp/req-$parte.txt
done

echo "==> 5/9 Modelos de la CNN"
if [ ! -f $DATOS/modelos/info.json ]; then
  ZIP="$(ls -t /tmp/*modelos*.zip 2>/dev/null | head -1 || true)"
  if [ -n "$ZIP" ]; then
    T=$(mktemp -d); unzip -oq "$ZIP" -d "$T"; INFO=$(find "$T" -name info.json | head -1)
    [ -n "$INFO" ] && cp -a "$(dirname "$INFO")"/. $DATOS/modelos/ && find $DATOS/modelos -name '*.pt' -delete
    rm -rf "$T"
  else
    echo "   (sin modelos todavía: los estudios se guardan y se analizan cuando los copies, ver docs/despliegue.md)"
  fi
fi
ls $DATOS/modelos || true

echo "==> 6/9 Configuración ($ENV)"
[ -f $ENV ] && cp $ENV $ENV.anterior
viejo() { grep -s "^$1=" $ENV.anterior | cut -d= -f2- || true; }
ADMIN_CLAVE="$(viejo ORTHOSYNC_ADMIN_CLAVE)"; NUEVO_ADMIN=""
[ -n "$ADMIN_CLAVE" ] || { ADMIN_CLAVE="$(python3 -c 'import secrets; print(secrets.token_urlsafe(10) + "9b")')"; NUEVO_ADMIN=1; }
SECRETO_PROXY="$(viejo ORTHOSYNC_PROXY_SECRETO)"; [ -n "$SECRETO_PROXY" ] || SECRETO_PROXY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
TOKEN_CNN="$(viejo ORTHOSYNC_INFERENCIA_TOKEN)"; [ -n "$TOKEN_CNN" ] || TOKEN_CNN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
BD="${NEON:-sqlite:///$DATOS/orthosync.db}"
cat > $ENV <<CONF
# Configuración de Orthosync en este servidor. NO se sube a GitHub. Permisos: solo root.
# entre comillas: la cadena de Neon trae '&'
ORTHOSYNC_BD='$BD'
ORTHOSYNC_BD_SIN_POOL=1
ORTHOSYNC_ARCHIVOS=$DATOS/archivos
ORTHOSYNC_SECRETOS=$DATOS/secretos
ORTHOSYNC_MODELOS=$DATOS/modelos
ORTHOSYNC_INTERFAZ=/nada
ORTHOSYNC_HTTPS=1
ORTHOSYNC_PROXY=1
ORTHOSYNC_PROXY_SECRETO=$SECRETO_PROXY
ORTHOSYNC_INFERENCIA_URL=http://127.0.0.1:8001
ORTHOSYNC_INFERENCIA_TOKEN=$TOKEN_CNN
ORTHOSYNC_SITIO=$PAGINAS
ORTHOSYNC_ORIGENES=$PAGINAS
ORTHOSYNC_ADMIN_CORREO=admin@orthosync.local
ORTHOSYNC_ADMIN_CLAVE=$ADMIN_CLAVE
ORTHOSYNC_POCA_MEMORIA=1
ORTHOSYNC_HORAS_UTC=-4
CONF
chmod 600 $ENV; rm -f $ENV.anterior
chown -R orthosync:orthosync $DATOS; chmod 700 $DATOS/secretos

echo "==> 7/9 Servicios (systemd), Caddy y actualización automática"
systemctl disable --now orthosync 2>/dev/null || true; rm -f /etc/systemd/system/orthosync.service   # el de la v4
cp $APP/despliegue/oracle/systemd/*.service $APP/despliegue/oracle/systemd/*.timer /etc/systemd/system/
sed -e "s|__DOMINIO__|$DOMINIO|g" -e "s|__SECRETO__|$SECRETO_PROXY|g" -e "s|__PAGINAS__|$PAGINAS|g" \
    $APP/despliegue/oracle/Caddyfile.plantilla > /etc/caddy/Caddyfile
chmod 640 /etc/caddy/Caddyfile; chgrp caddy /etc/caddy/Caddyfile
for p in 80 443; do
  iptables -C INPUT -p tcp -m state --state NEW --dport $p -j ACCEPT 2>/dev/null || \
    iptables -I INPUT 5 -p tcp -m state --state NEW --dport $p -j ACCEPT
done
netfilter-persistent save >/dev/null 2>&1 || iptables-save > /etc/iptables/rules.v4

echo "==> 8/9 Base de datos"
cargar_env() { set -a; . $ENV; set +a; }
if [ -n "$NEON" ] && [ -f $DATOS/orthosync.db ] && [ ! -f $DATOS/.migrado_a_neon ]; then
  echo "   Copiando los datos de SQLite a Neon..."
  (cd $APP/backend && cargar_env && sudo -u orthosync -E .venv/bin/python scripts/migrar_a_postgres.py \
      "sqlite:///$DATOS/orthosync.db" "$ORTHOSYNC_BD") && touch $DATOS/.migrado_a_neon
fi
CREDS_DEMO=""
HAY=$(cd $APP/backend && cargar_env && sudo -u orthosync -E .venv/bin/python -c "
from app.db.migraciones import crear_tablas; crear_tablas()
from app.db.base import Sesion; from app.db.modelos import Paciente; from sqlalchemy import select
print(1 if Sesion().scalar(select(Paciente)) else 0)")
if [ "$HAY" = 0 ]; then
  CREDS_DEMO="$(cd $APP/backend && cargar_env && sudo -u orthosync -E ORTHOSYNC_DEMO_ALEATORIO=1 .venv/bin/python scripts/sembrar_demo.py)"
fi

echo "==> 9/9 Arrancando"
systemctl daemon-reload
systemctl enable --now orthosync-cnn orthosync-api orthosync-actualizar.timer >/dev/null 2>&1
systemctl restart orthosync-cnn orthosync-api
systemctl enable --now caddy >/dev/null 2>&1; systemctl reload caddy || systemctl restart caddy
for i in $(seq 1 40); do curl -fs -o /dev/null http://127.0.0.1:8000/api/salud && break; sleep 3; done
curl -fs http://127.0.0.1:8000/api/salud >/dev/null && echo "API respondiendo." || { journalctl -u orthosync-api -n 30 --no-pager; exit 1; }
curl -fs http://127.0.0.1:8001/salud >/dev/null && echo "CNN respondiendo." || journalctl -u orthosync-cnn -n 30 --no-pager

echo
echo "=================================================================="
echo " Servidor listo. Ahora configura Cloudflare Pages con estas dos variables:"
echo
echo "   ORIGEN_API     = https://$DOMINIO"
echo "   PROXY_SECRETO  = $SECRETO_PROXY      (márcala como Secret)"
echo
echo " El sistema se abrirá en:  $PAGINAS"
if [ -n "$NUEVO_ADMIN" ]; then
  echo; echo " Administrador: admin@orthosync.local"
  echo " Contraseña temporal: $ADMIN_CLAVE   (te pedirá cambiarla al entrar)"
fi
[ -n "$CREDS_DEMO" ] && { echo; echo "$CREDS_DEMO"; }
echo "=================================================================="
