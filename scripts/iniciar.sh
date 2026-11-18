#!/usr/bin/env bash
# Igual que iniciar.bat, para Linux o macOS.
set -e
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
for parte in inferencia backend; do
  cd "$RAIZ/$parte"; [ -d .venv ] || python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
done
cd "$RAIZ/backend"; [ -f orthosync.db ] || .venv/bin/python scripts/sembrar_demo.py
[ -f "$RAIZ/frontend/dist/index.html" ] || (cd "$RAIZ/frontend" && npm ci && npm run build)
(cd "$RAIZ/inferencia" && .venv/bin/uvicorn cnn.main:app --port 8001) &
trap "kill $!" EXIT
echo "Sistema en http://localhost:8000"
.venv/bin/uvicorn app.main:app --port 8000 --reload
