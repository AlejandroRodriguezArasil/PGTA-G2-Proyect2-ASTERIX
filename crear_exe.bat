@echo off
REM ==========================================================================
REM crear_exe.bat
REM Genera el ejecutable de la aplicacion: un unico .exe aislado, como pide el enunciado.
REM
REM Uso: doble clic en este fichero. Solo hace falta tener Python 3 instalado.
REM   1. Busca Python: primero el lanzador "py -3" y, si no esta, "python".
REM   2. Si no existe el entorno .venv, lo crea. Despues instala siempre
REM      requirements.txt y PyInstaller: la primera vez tarda unos minutos y
REM      necesita internet; las siguientes, pip solo comprueba que este todo.
REM   3. Ejecuta PyInstaller y deja ASTERIXDecoder.exe en esta carpeta,
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
set "TEMPORAL=%TEMP%\ASTERIXDecoder_build"
set "EXE=%~dp0ASTERIXDecoder.exe"
set "PYTHON_VENV=.venv\Scripts\python.exe"
set "VENV_NUEVO="

REM --- 1. Python ---------------------------------------------------------------
echo [1/4] Looking for Python...
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
echo Python 3 was not found.
echo Install it from https://www.python.org/downloads/ ticking "Add python.exe to PATH"
echo and run this file again.
pause
exit /b 1

:hay_python
echo       Using: %PYTHON%

REM --- 2. Entorno .venv con las librerias y PyInstaller ------------------------
echo [2/4] Preparing the .venv environment...
if exist "%PYTHON_VENV%" goto venv_existe
echo       It does not exist: creating it. The first time takes a few minutes and needs internet.
%PYTHON% -m venv .venv
if errorlevel 1 goto error_venv
set "VENV_NUEVO=1"

:venv_existe
REM Siempre se instalan las dos cosas: si ya estan, pip solo lo comprueba y va rapido.
REM Asi un .venv a medias (por ejemplo, de un pip install que fallo) se completa.
echo       Installing requirements.txt and PyInstaller %VERSION_PYINSTALLER% (if already installed, only checked)...
"%PYTHON_VENV%" -m pip install --disable-pip-version-check -r requirements.txt pyinstaller==%VERSION_PYINSTALLER%
if errorlevel 1 goto error_instalar

REM --- 3. PyInstaller ----------------------------------------------------------
echo [3/4] Building ASTERIXDecoder.exe with PyInstaller...
REM Si el .exe esta abierto, Windows no deja sobrescribirlo
tasklist /fi "imagename eq ASTERIXDecoder.exe" | find /i "ASTERIXDecoder.exe" >nul
if not errorlevel 1 goto error_abierto

"%PYTHON_VENV%" -m PyInstaller --noconfirm --onefile --windowed --name ASTERIXDecoder --collect-data customtkinter --distpath "%~dp0." --workpath "%TEMPORAL%" --specpath "%TEMPORAL%" "%~dp0main.py"
set "RESULTADO=%errorlevel%"

REM --- 4. Limpieza y resultado -------------------------------------------------
echo [4/4] Deleting the temporary folder...
if exist "%TEMPORAL%" rmdir /s /q "%TEMPORAL%"

if not "%RESULTADO%"=="0" goto error_pyinstaller
if not exist "%EXE%" goto error_pyinstaller
echo.
echo Executable created: %EXE%
pause
exit /b 0

REM --- Errores -----------------------------------------------------------------
:error_venv
echo.
echo ERROR: the .venv environment could not be created with %PYTHON%.
pause
exit /b 1

:error_instalar
echo.
echo ERROR: the libraries could not be installed.
echo Check the internet connection and run this file again.
REM Si el entorno se acaba de crear, se borra para que la proxima vez empiece de cero
if defined VENV_NUEVO rmdir /s /q ".venv"
pause
exit /b 1

:error_abierto
echo.
echo ERROR: ASTERIXDecoder.exe is open and cannot be overwritten.
echo Close the application and run this file again.
pause
exit /b 1

:error_pyinstaller
echo.
echo ERROR: the executable could not be created (see the messages above).
echo If ASTERIXDecoder.exe was open, close the application and try again.
pause
exit /b 1
