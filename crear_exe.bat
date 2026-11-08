@echo off
REM ==========================================================================
REM crear_exe.bat
REM Genera el ejecutable unico de la aplicacion (R49: un solo .exe aislado).
REM
REM Uso: doble clic en este fichero. Solo hace falta tener Python 3 instalado.
REM   1. Busca Python: primero el lanzador "py -3" y, si no esta, "python".
REM   2. Si no existe el entorno .venv, lo crea e instala requirements.txt y
REM      PyInstaller (la primera vez tarda unos minutos y necesita internet).
REM      Si .venv ya existe pero le falta PyInstaller, instala solo PyInstaller.
REM   3. Ejecuta PyInstaller y deja DecodificadorASTERIX.exe en esta carpeta,
REM      junto a main.py. Lo que PyInstaller genera de paso (la carpeta build y
REM      el .spec) va a una carpeta temporal de %TEMP% que se borra al acabar.
REM PyInstaller no esta en requirements.txt porque solo sirve para crear el .exe,
REM no lo usa la aplicacion.
REM
REM Parametros de PyInstaller:
REM   --noconfirm      no pregunta antes de borrar lo de una vez anterior
REM   --onefile        mete Python, las librerias y nuestro codigo en un unico .exe
REM   --windowed       sin la ventana negra de consola detras de la aplicacion
REM   --name           nombre del .exe que se genera
REM   --collect-data customtkinter
REM                    incluye los ficheros de customtkinter que no son codigo Python
REM                    (temas .json, fuentes e iconos); sin ellos el .exe no arranca
REM   --distpath       donde queda el .exe: esta carpeta ("%~dp0." porque la ruta
REM                    acaba en \ y, sin el punto, la \ se comeria las comillas)
REM   --workpath       carpeta de trabajo de PyInstaller (temporal)
REM   --specpath       donde escribe el .spec (temporal); por eso main.py va con
REM                    su ruta completa
REM ==========================================================================

REM Se trabaja siempre desde la carpeta de este fichero
cd /d "%~dp0"

set "VERSION_PYINSTALLER=6.22.3"
set "TEMPORAL=%TEMP%\DecodificadorASTERIX_build"
set "EXE=%~dp0DecodificadorASTERIX.exe"
set "PYTHON_VENV=.venv\Scripts\python.exe"
set "VENV_NUEVO="

REM --- 1. Python ---------------------------------------------------------------
echo [1/4] Buscando Python...
py -3 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON=py -3"
    goto hay_python
)
python --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON=python"
    goto hay_python
)
echo.
echo No se ha encontrado Python 3.
echo Instalalo desde https://www.python.org/downloads/ marcando "Add python.exe to PATH"
echo y vuelve a ejecutar este fichero.
pause
exit /b 1

:hay_python
echo       Se usa: %PYTHON%

REM --- 2. Entorno .venv con las librerias y PyInstaller ------------------------
echo [2/4] Preparando el entorno .venv...
if exist "%PYTHON_VENV%" goto venv_existe

echo       No existe: se crea y se instalan requirements.txt y PyInstaller %VERSION_PYINSTALLER%.
echo       La primera vez tarda unos minutos y necesita internet.
%PYTHON% -m venv .venv
if errorlevel 1 goto error_venv
set "VENV_NUEVO=1"
"%PYTHON_VENV%" -m pip install --disable-pip-version-check -r requirements.txt pyinstaller==%VERSION_PYINSTALLER%
if errorlevel 1 goto error_instalar
goto venv_listo

:venv_existe
"%PYTHON_VENV%" -m PyInstaller --version >nul 2>&1
if not errorlevel 1 (
    echo       Ya existe y tiene PyInstaller.
    goto venv_listo
)
echo       Ya existe, pero le falta PyInstaller: se instala %VERSION_PYINSTALLER%.
"%PYTHON_VENV%" -m pip install --disable-pip-version-check pyinstaller==%VERSION_PYINSTALLER%
if errorlevel 1 goto error_instalar

:venv_listo

REM --- 3. PyInstaller ----------------------------------------------------------
echo [3/4] Generando DecodificadorASTERIX.exe con PyInstaller...
REM Si el .exe esta abierto, Windows no deja sobrescribirlo
tasklist /fi "imagename eq DecodificadorASTERIX.exe" | find /i "DecodificadorASTERIX.exe" >nul
if not errorlevel 1 goto error_abierto

"%PYTHON_VENV%" -m PyInstaller --noconfirm --onefile --windowed --name DecodificadorASTERIX --collect-data customtkinter --distpath "%~dp0." --workpath "%TEMPORAL%" --specpath "%TEMPORAL%" "%~dp0main.py"
set "RESULTADO=%errorlevel%"

REM --- 4. Limpieza y resultado -------------------------------------------------
echo [4/4] Borrando la carpeta temporal...
if exist "%TEMPORAL%" rmdir /s /q "%TEMPORAL%"

if not "%RESULTADO%"=="0" goto error_pyinstaller
if not exist "%EXE%" goto error_pyinstaller
echo.
echo Ejecutable creado: %EXE%
pause
exit /b 0

REM --- Errores -----------------------------------------------------------------
:error_venv
echo.
echo ERROR: no se ha podido crear el entorno .venv con %PYTHON%.
pause
exit /b 1

:error_instalar
echo.
echo ERROR: no se han podido instalar las librerias.
echo Comprueba la conexion a internet y vuelve a ejecutar este fichero.
REM Si el entorno se acaba de crear, se borra para que la proxima vez empiece de cero
if defined VENV_NUEVO rmdir /s /q ".venv"
pause
exit /b 1

:error_abierto
echo.
echo ERROR: DecodificadorASTERIX.exe esta abierto y no se puede sobrescribir.
echo Cierra la aplicacion y vuelve a ejecutar este fichero.
pause
exit /b 1

:error_pyinstaller
echo.
echo ERROR: no se ha podido crear el ejecutable (mira los mensajes de arriba).
echo Si DecodificadorASTERIX.exe estaba abierto, cierra la aplicacion y vuelve a intentarlo.
pause
exit /b 1
