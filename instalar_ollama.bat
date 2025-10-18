@echo off
REM ====================================================================
REM Script de Instalacion Automatica de Ollama para TenderAI Platform
REM ====================================================================
REM
REM Este script:
REM 1. Descarga e instala Ollama
REM 2. Descarga el modelo Qwen2.5 72B (recomendado)
REM 3. Descarga el modelo de embeddings nomic-embed-text
REM 4. Inicia el servidor Ollama
REM 5. Verifica que todo funciona correctamente
REM
REM ====================================================================

echo.
echo ========================================================================
echo   INSTALADOR AUTOMATICO DE OLLAMA PARA TENDERAI PLATFORM
echo ========================================================================
echo.
echo Este script instalara Ollama y los modelos recomendados:
echo   - Qwen2.5 72B (chat, ~41GB)
echo   - nomic-embed-text (embeddings, ~274MB)
echo.
echo IMPORTANTE: Necesitas al menos 50GB de espacio libre en disco
echo.
pause

REM Verificar si se esta ejecutando como administrador
net session >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Ejecutando como administrador
) else (
    echo [ERROR] Este script necesita permisos de administrador
    echo Por favor, ejecutalo con clic derecho y "Ejecutar como administrador"
    pause
    exit /b 1
)

echo.
echo ========================================================================
echo PASO 1: Verificando instalacion de Ollama
echo ========================================================================
echo.

REM Verificar si Ollama ya esta instalado
ollama --version >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Ollama ya esta instalado
    ollama --version
) else (
    echo [INFO] Ollama no esta instalado. Descargando...

    REM Descargar Ollama
    echo Descargando instalador de Ollama...
    powershell -Command "Invoke-WebRequest -Uri 'https://ollama.com/download/OllamaSetup.exe' -OutFile '%TEMP%\OllamaSetup.exe'"

    if exist "%TEMP%\OllamaSetup.exe" (
        echo [OK] Instalador descargado
        echo.
        echo Ejecutando instalador de Ollama...
        echo (Se abrira una ventana de instalacion - sigue las instrucciones)
        start /wait "%TEMP%\OllamaSetup.exe"

        REM Esperar a que se complete la instalacion
        timeout /t 5 /nobreak >nul

        REM Verificar instalacion
        ollama --version >nul 2>&1
        if %errorLevel% == 0 (
            echo [OK] Ollama instalado correctamente
            ollama --version
        ) else (
            echo [ERROR] Ollama no se instalo correctamente
            echo Por favor, visita https://ollama.com/download y descarga manualmente
            pause
            exit /b 1
        )
    ) else (
        echo [ERROR] No se pudo descargar el instalador
        echo Por favor, visita https://ollama.com/download y descarga manualmente
        pause
        exit /b 1
    )
)

echo.
echo ========================================================================
echo PASO 2: Iniciando servidor Ollama
echo ========================================================================
echo.

REM Verificar si Ollama ya esta corriendo
curl -s http://localhost:11434 >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Servidor Ollama ya esta corriendo
) else (
    echo [INFO] Iniciando servidor Ollama en segundo plano...
    start /B ollama serve

    REM Esperar a que el servidor arranque
    echo Esperando a que el servidor inicie...
    timeout /t 5 /nobreak >nul

    REM Verificar que arranco
    curl -s http://localhost:11434 >nul 2>&1
    if %errorLevel% == 0 (
        echo [OK] Servidor Ollama iniciado correctamente
    ) else (
        echo [WARNING] El servidor puede estar iniciando, continuando...
    )
)

echo.
echo ========================================================================
echo PASO 3: Descargando modelo Qwen2.5 72B (esto puede tardar 15-30 min)
echo ========================================================================
echo.

REM Verificar si el modelo ya esta descargado
ollama list | findstr "qwen2.5:72b" >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Modelo qwen2.5:72b ya esta descargado
) else (
    echo [INFO] Descargando qwen2.5:72b (~41GB)...
    echo.
    echo IMPORTANTE: Esta descarga puede tardar entre 15 y 30 minutos
    echo dependiendo de tu conexion a internet.
    echo.
    echo La descarga continuara aunque minimices esta ventana.
    echo NO CIERRES esta ventana hasta que termine.
    echo.
    pause

    ollama pull qwen2.5:72b

    if %errorLevel% == 0 (
        echo.
        echo [OK] Modelo qwen2.5:72b descargado correctamente
    ) else (
        echo.
        echo [ERROR] Hubo un problema descargando el modelo
        echo Puedes intentar descargarlo manualmente con: ollama pull qwen2.5:72b
        pause
    )
)

echo.
echo ========================================================================
echo PASO 4: Descargando modelo de embeddings (2-3 minutos)
echo ========================================================================
echo.

REM Verificar si el modelo de embeddings ya esta descargado
ollama list | findstr "nomic-embed-text" >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Modelo nomic-embed-text ya esta descargado
) else (
    echo [INFO] Descargando nomic-embed-text (~274MB)...
    echo.

    ollama pull nomic-embed-text

    if %errorLevel% == 0 (
        echo.
        echo [OK] Modelo nomic-embed-text descargado correctamente
    ) else (
        echo.
        echo [ERROR] Hubo un problema descargando el modelo de embeddings
        echo Puedes intentar descargarlo manualmente con: ollama pull nomic-embed-text
        pause
    )
)

echo.
echo ========================================================================
echo PASO 5: Verificando instalacion
echo ========================================================================
echo.

REM Mostrar modelos instalados
echo Modelos instalados:
echo.
ollama list
echo.

REM Verificar servidor
echo Verificando servidor Ollama...
curl -s http://localhost:11434 >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Servidor Ollama funciona correctamente
) else (
    echo [WARNING] Servidor Ollama no responde
    echo Intenta reiniciarlo manualmente con: ollama serve
)

echo.
echo ========================================================================
echo PASO 6: Probando el modelo
echo ========================================================================
echo.

echo Enviando pregunta de prueba al modelo qwen2.5:72b...
echo (Esto puede tardar unos segundos la primera vez)
echo.

REM Crear archivo temporal con la pregunta
echo Hola, como estas? > %TEMP%\ollama_test.txt

REM Probar el modelo
ollama run qwen2.5:72b "Responde en una sola frase: Cual es la capital de Espana?"

if %errorLevel% == 0 (
    echo.
    echo [OK] Modelo funciona correctamente
) else (
    echo.
    echo [WARNING] El modelo puede necesitar mas tiempo para cargar
)

echo.
echo ========================================================================
echo INSTALACION COMPLETADA
echo ========================================================================
echo.
echo Ollama ha sido instalado y configurado correctamente!
echo.
echo Modelos instalados:
echo   - qwen2.5:72b (chat)
echo   - nomic-embed-text (embeddings)
echo.
echo Servidor corriendo en: http://localhost:11434
echo.
echo Proximos pasos:
echo   1. Ve a http://127.0.0.1:8001/perfil/
echo   2. Selecciona "Ollama (Local)" como proveedor
echo   3. Modelo Ollama: qwen2.5:72b
echo   4. Modelo Embeddings: nomic-embed-text
echo   5. Guarda cambios
echo   6. Ve a http://127.0.0.1:8001/ollama/check/ para verificar
echo.
echo Si el servidor se detiene, puedes reiniciarlo con: ollama serve
echo.
echo Documentacion completa: GUIA_INSTALACION_OLLAMA.md
echo.
pause

echo.
echo Quieres abrir el navegador en la pagina de perfil? (S/N)
set /p abrir_navegador=

if /i "%abrir_navegador%"=="S" (
    start http://127.0.0.1:8001/perfil/
)

echo.
echo Instalacion finalizada. Presiona cualquier tecla para salir.
pause >nul
