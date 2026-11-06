@echo off
rem Genera manual\Manual_de_uso.pdf a partir de manual\manual.html con Microsoft Edge (viene con Windows).
rem Las capturas que usa el manual estan en manual\capturas\.
rem --headless: sin abrir ventana. --no-pdf-header-footer: sin fecha ni ruta en los margenes.

rem Edge puede estar instalado en cualquiera de estas dos carpetas
set "EDGE=C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if not exist "%EDGE%" set "EDGE=C:\Program Files\Microsoft\Edge\Application\msedge.exe"
if not exist "%EDGE%" goto sin_edge

"%EDGE%" --headless --disable-gpu --no-pdf-header-footer --print-to-pdf="%~dp0manual\Manual_de_uso.pdf" "%~dp0manual\manual.html"

echo.
echo Manual generado: %~dp0manual\Manual_de_uso.pdf
pause
exit /b 0

:sin_edge
echo.
echo No se ha encontrado Microsoft Edge (msedge.exe) en:
echo   C:\Program Files (x86)\Microsoft\Edge\Application\
echo   C:\Program Files\Microsoft\Edge\Application\
echo Instala Edge o abre manual\manual.html en un navegador e imprimelo como PDF.
pause
exit /b 1
