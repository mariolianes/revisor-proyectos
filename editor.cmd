@echo off
REM Arranca el editor de criterios y abre el navegador.
cd /d "%~dp0"

if not exist "frontend\dist\index.html" (
    echo Compilando el frontend...
    pushd frontend
    call npm install
    call npm run build
    popd
)

start "" http://127.0.0.1:8000
python -m backend
