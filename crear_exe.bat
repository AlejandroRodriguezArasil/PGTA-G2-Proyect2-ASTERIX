@echo off
REM ==========================================================================
REM crear_exe.bat
REM Genera el ejecutable unico de la aplicacion (R49: un solo .exe aislado).
REM
REM Uso: doble clic en este fichero, o "crear_exe.bat" desde esta carpeta.
REM Necesita el entorno .venv creado (ver README.md) y PyInstaller instalado en el:
REM     .venv\Scripts\python -m pip install pyinstaller
REM PyInstaller no esta en requirements.txt porque solo sirve para crear el .exe,
REM no lo usa la aplicacion.
REM
REM Parametros de PyInstaller:
REM   --noconfirm      borra sin preguntar lo que haya de una vez anterior en build y dist
REM   --onefile        mete Python, las librerias y nuestro codigo en un unico .exe
REM   --windowed       sin la ventana negra de consola detras de la aplicacion
REM   --name           nombre del .exe que se genera
REM   --collect-data customtkinter
REM                    incluye los ficheros de customtkinter que no son codigo Python
REM                    (temas .json, fuentes e iconos); sin ellos el .exe no arranca
REM   main.py          punto de entrada de la aplicacion
REM
REM Resultado: dist\DecodificadorASTERIX.exe
REM (las carpetas build y dist y el fichero .spec son temporales y no se suben a GitHub)
REM ==========================================================================

REM Se trabaja siempre desde la carpeta de este fichero
cd /d "%~dp0"

".venv\Scripts\python.exe" -m PyInstaller --noconfirm --onefile --windowed --name DecodificadorASTERIX --collect-data customtkinter main.py

echo.
echo Si no hay errores arriba, el ejecutable esta en dist\DecodificadorASTERIX.exe
pause
