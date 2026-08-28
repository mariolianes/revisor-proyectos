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

REM El frontend se compila SIEMPRE, no solo cuando falta.
REM
REM Antes se compilaba unicamente "if not exist frontend\dist\index.html", y
REM frontend\dist esta en .gitignore, asi que no viaja con el repositorio.
REM Quien ya tenia compilada una version anterior se quedaba, al actualizar,
REM con el backend nuevo y la interfaz vieja: pantallas que faltan, campos que
REM el backend ya no devuelve, y la conclusion razonable de que esto no
REM funciona. El fallo no da ningun error; solo una interfaz que no se
REM corresponde con el programa.
REM
REM Comparar en .cmd la fecha del codigo fuente con la de lo compilado sale
REM enrevesado y fragil. Compilar siempre cuesta unos segundos y no se
REM equivoca nunca. NO lo "optimices" volviendo a compilar solo cuando falte.

where npm >nul 2>nul
if errorlevel 1 goto :sin_npm

echo Compilando el frontend...
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
goto :arrancar

:sin_npm
REM Sin npm no se puede recompilar. Si hay algo compilado de antes se arranca
REM con ello, pero diciendo que puede estar desfasado: dejar al docente sin
REM arrancar seria peor, y callarselo lo devolveria al fallo de arriba.
if exist "frontend\dist\index.html" (
    echo.
    echo AVISO: no se encuentra "npm" en el PATH, asi que no se ha podido
    echo recompilar la interfaz. Se arranca con la que habia compilada, que
    echo puede no corresponderse con esta version del programa.
    echo Instala Node.js ^(incluye npm^) desde https://nodejs.org/ y vuelve a
    echo arrancar para quitar esa duda.
    echo.
    goto :arrancar
)
echo No se encuentra "npm" en el PATH.
echo El frontend todavia no esta compilado y hace falta npm para compilarlo.
echo Instala Node.js ^(incluye npm^) desde https://nodejs.org/
pause
exit /b 1

:arrancar
python -m backend
if errorlevel 1 (
    echo.
    echo El editor se ha detenido con un error. Revisa el mensaje de arriba.
    pause
    exit /b 1
)
