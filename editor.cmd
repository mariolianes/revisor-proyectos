@echo off
REM Arranca el editor de criterios. El propio servidor abre el navegador
REM en cuanto esta escuchando: no lo hace este script, para no adelantarse.
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo No se encuentra "python" en el PATH.
    echo Instala Python 3.11 o superior desde https://www.python.org/downloads/
    echo y asegurate de marcar "Add python.exe to PATH" durante la instalacion.
    pause
    exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
    echo No se encuentra "npm" en el PATH.
    echo Instala Node.js ^(incluye npm^) desde https://nodejs.org/
    pause
    exit /b 1
)

if not exist "frontend\dist\index.html" (
    echo Compilando el frontend, esto solo pasa la primera vez...
    pushd frontend
    call npm install
    call npm run build
    popd
    if not exist "frontend\dist\index.html" (
        echo.
        echo La compilacion del frontend no ha generado "frontend\dist\index.html".
        echo Revisa los mensajes de arriba.
        pause
        exit /b 1
    )
)

python -m backend
if errorlevel 1 (
    echo.
    echo El editor se ha detenido con un error. Revisa el mensaje de arriba.
    pause
    exit /b 1
)
