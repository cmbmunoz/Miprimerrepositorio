@echo off
chcp 65001 > nul
echo.
echo  Sistema de Pre-Facturación Automática
echo  =========================================
echo.

if not exist ".env" (
    echo  ERROR: No encontré el archivo .env
    echo  Copiá .env.example a .env y completá los valores.
    echo.
    pause
    exit /b 1
)

python run.py
pause
