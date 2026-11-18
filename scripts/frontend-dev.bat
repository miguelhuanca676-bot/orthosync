@echo off
rem Para trabajar en el diseño: recarga la página al guardar cambios en frontend\src.
rem Necesita Node.js 22 y que iniciar.bat esté corriendo (la API en el puerto 8000).
cd /d "%~dp0..\frontend"
if not exist node_modules call npm ci
start "" cmd /c "timeout /t 5 >nul & start http://localhost:5173/app"
call npm run dev
