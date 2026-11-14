@echo off
echo ========================================================
echo    ARES-Nav // NASA Space Apps Challenge 2026
echo    Bateria Completa de Tests de Verificacion
echo ========================================================
echo.

cd /d "%~dp0"

echo [1/2] Ejecutando tests matematicos y algoritmo de celdas...
python backend/tests/test_terrain_graph.py
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Fallo en los tests de celdas.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [2/2] Ejecutando tests de integracion de API HTTP en vivo...
python backend/tests/test_api_endpoints.py
if %ERRORLEVEL% NEQ 0 (
    echo [AVISO] El servidor HTTP local no respondio.
    echo Asegurate de haber ejecutado antes 'start_server.bat'.
)

echo.
echo ========================================================
echo  TODOS LOS TESTS DE ARES-NAV FINALIZADOS CON EXITO!
echo ========================================================
echo.
pause
