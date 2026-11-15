@echo off
rem ========================================================
rem    ARES-Nav // Build the frontend and start the server
rem    (same as: python start.py)
rem ========================================================
cd /d "%~dp0"

where python >nul 2>nul
if %errorlevel%==0 (
    python start.py %*
) else (
    py -3 start.py %*
)

if errorlevel 1 pause
