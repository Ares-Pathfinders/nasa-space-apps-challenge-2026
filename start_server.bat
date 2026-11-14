@echo off
echo ========================================================
echo    ARES-Nav // Arrancando Servidor Web y Motor de Celdas
echo ========================================================
echo.
echo Abriendo en: http://localhost:8000
echo Mapa 2D:    http://localhost:8000/tactical
echo.

cd /d "%~dp0"
start http://localhost:8000/tactical
python backend/server.py 8000
