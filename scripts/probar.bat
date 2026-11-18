@echo off
chcp 65001 >nul
rem Ejecuta todas las pruebas automáticas (API + CNN). Primero ejecuta iniciar.bat una vez.
cd /d "%~dp0..\inferencia" && .venv\Scripts\python -m pytest -q || goto fallo
cd /d "%~dp0..\backend" && .venv\Scripts\python -m pytest -q || goto fallo
echo. & echo TODAS LAS PRUEBAS PASARON & pause & exit /b 0
:fallo
echo. & echo HAY PRUEBAS QUE FALLARON (mira arriba cual) & pause & exit /b 1
