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

REM Las dependencias, ANTES de nada. Hasta el 2026-09-07 este script no las
REM instalaba: con un Python recien instalado, lo primero que veia quien
REM abriera esto era un ModuleNotFoundError de fastapi y ninguna pista de
REM que faltaba un "pip install". Es rapido si ya estan: pip no reinstala lo
REM que ya cumple la version pedida.
echo Comprobando las dependencias...
python -m pip install --quiet --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
    echo.
    echo No se han podido instalar las dependencias. Revisa los mensajes de
    echo arriba: lo mas comun es no tener conexion, o que pip no este
    echo instalado con este Python.
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
REM El codigo de salida se guarda ANTES de popd: no basta con mirar si
REM existe "frontend\dist\index.html". "npm run build" es "tsc -b && vite
REM build", asi que un error de TypeScript hace que vite ni llegue a
REM ejecutarse y el dist ANTERIOR se queda intacto: la comprobacion de que
REM el fichero existe la pasaba tan campante y se arrancaba en silencio con
REM la interfaz vieja, que es exactamente el fallo que este script
REM recompila siempre para evitar.
set "FALLO_LA_COMPILACION=%errorlevel%"
popd
if not "%FALLO_LA_COMPILACION%"=="0" goto :build_fallido
if not exist "frontend\dist\index.html" (
    echo.
    echo La compilacion del frontend no ha generado "frontend\dist\index.html".
    echo Revisa los mensajes de arriba.
    pause
    exit /b 1
)
goto :arrancar

:build_fallido
REM Misma franqueza que la rama de "falta npm": se dice que lo que se va a
REM servir puede no corresponderse con el programa, en vez de callarlo.
if exist "frontend\dist\index.html" (
    echo.
    echo AVISO: la compilacion de la interfaz ha FALLADO. Revisa los errores
    echo de arriba. Se arranca con la interfaz que habia compilada de antes,
    echo que puede no corresponderse con esta version del programa.
    echo.
    goto :arrancar
)
echo.
echo La compilacion de la interfaz ha fallado y no hay ninguna compilada de
echo antes con la que arrancar. Revisa los errores de arriba.
pause
exit /b 1

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
