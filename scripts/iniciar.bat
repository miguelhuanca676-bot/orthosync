@echo off
chcp 65001 >nul
title Orthosync - API
rem Arranca el sistema completo en tu laptop: la CNN (puerto 8001) en otra ventana y la API (puerto 8000) en esta.
rem Luego abre http://localhost:8000
cd /d "%~dp0.."
set RAIZ=%cd%
python --version >nul 2>&1 || goto sinpython

echo === 1/4 Servicio de inferencia (CNN) ===
cd /d "%RAIZ%\inferencia"
if not exist .venv ( python -m venv .venv || goto error )
.venv\Scripts\python -m pip install -q --upgrade pip
.venv\Scripts\pip install -q -r requirements.txt || goto error

echo === 2/4 API (backend) ===
cd /d "%RAIZ%\backend"
if not exist .venv ( python -m venv .venv || goto error )
.venv\Scripts\python -m pip install -q --upgrade pip
.venv\Scripts\pip install -q -r requirements.txt || goto error
if not exist orthosync.db .venv\Scripts\python scripts\sembrar_demo.py

echo === 3/4 Paginas (frontend) ===
if not exist "%RAIZ%\frontend\dist\index.html" (
  where npm >nul 2>&1 && (
    cd /d "%RAIZ%\frontend" && call npm ci && call npm run build
  ) || echo AVISO: falta frontend\dist y no hay Node.js. Instala Node.js 22 o usa el zip que ya trae dist.
)

echo === 4/4 Arrancando ===
start "Orthosync - CNN (no cerrar)" /d "%RAIZ%\inferencia" cmd /k ".venv\Scripts\python -m uvicorn cnn.main:app --port 8001"
start "" cmd /c "timeout /t 8 >nul & start http://localhost:8000"
echo.
echo   Sistema:        http://localhost:8000
echo   API (docs):     http://localhost:8000/docs     (solo si ORTHOSYNC_DOCS=1)
echo   CNN (docs):     http://localhost:8001/docs
echo   Para detenerlo, cierra esta ventana y la de la CNN.
echo.
cd /d "%RAIZ%\backend"
.venv\Scripts\python -m uvicorn app.main:app --port 8000 --reload
pause
exit /b 0

:sinpython
echo ERROR: no se encontro Python. Instala Python 3.12 desde python.org marcando "Add Python to PATH".
pause & exit /b 1
:error
echo ERROR durante la instalacion. Revisa el mensaje de arriba.
pause & exit /b 1
