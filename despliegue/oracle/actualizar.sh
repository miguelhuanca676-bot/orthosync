#!/usr/bin/env bash
# Lo ejecuta el temporizador cada 10 minutos: si en GitHub hay cambios, los trae y reinicia lo que cambió.
# También se puede correr a mano:  sudo bash /opt/orthosync/despliegue/oracle/actualizar.sh
set -euo pipefail
cd /opt/orthosync
git fetch -q origin
ANTES=$(git rev-parse HEAD); DESPUES=$(git rev-parse @{u})
[ "$ANTES" = "$DESPUES" ] && exit 0
git merge -q --ff-only @{u}
cambios=$(git diff --name-only "$ANTES" "$DESPUES")
echo "Actualizando $ANTES -> $DESPUES"; echo "$cambios"
for parte in backend inferencia; do
  if echo "$cambios" | grep -q "^$parte/requirements.txt"; then
    grep -viE '^(pytest|httpx)\b' $parte/requirements.txt > /tmp/req-$parte.txt || true
    [ $parte = backend ] && echo httpx >> /tmp/req-$parte.txt
    $parte/.venv/bin/pip install -q --no-cache-dir -r /tmp/req-$parte.txt
  fi
done
echo "$cambios" | grep -q '^inferencia/' && systemctl restart orthosync-cnn
echo "$cambios" | grep -q '^backend/' && systemctl restart orthosync-api
if echo "$cambios" | grep -q '^despliegue/oracle/systemd/'; then
  cp despliegue/oracle/systemd/*.service despliegue/oracle/systemd/*.timer /etc/systemd/system/ && systemctl daemon-reload
fi
exit 0
