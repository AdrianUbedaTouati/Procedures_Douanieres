@echo off
REM Script para ejecutar tests en Windows
REM Uso: run_tests.bat [opciones]
REM   run_tests.bat           - Ejecutar todos los tests
REM   run_tests.bat -v        - Modo verbose
REM   run_tests.bat --quick   - Solo tests rapidos

echo.
echo ============================================================
echo    ChatBot IA - Test Suite
echo ============================================================
echo.

REM Verificar que estamos en el directorio correcto
if not exist "manage.py" (
    echo ERROR: No se encuentra manage.py
    echo Ejecuta este script desde el directorio raiz del proyecto
    exit /b 1
)

REM Ejecutar el script de Python con los argumentos pasados
python run_tests.py %*

exit /b %ERRORLEVEL%
