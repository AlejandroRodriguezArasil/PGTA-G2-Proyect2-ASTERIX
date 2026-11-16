@echo off
rem Genera manual\User_Manual.pdf a partir de manual\manual.html con Microsoft Edge (viene con Windows).
rem Las capturas que usa el manual estan en manual\capturas\.
rem --headless: sin abrir ventana. --no-pdf-header-footer: sin fecha ni ruta en los margenes.

rem Edge puede estar instalado en cualquiera de estas dos carpetas
set "EDGE=C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if not exist "%EDGE%" set "EDGE=C:\Program Files\Microsoft\Edge\Application\msedge.exe"
if not exist "%EDGE%" goto sin_edge

"%EDGE%" --headless --disable-gpu --no-pdf-header-footer --print-to-pdf="%~dp0manual\User_Manual.pdf" "%~dp0manual\manual.html"

echo.
echo Manual created: %~dp0manual\User_Manual.pdf
pause
exit /b 0

:sin_edge
echo.
echo Microsoft Edge (msedge.exe) was not found in:
echo   C:\Program Files (x86)\Microsoft\Edge\Application\
echo   C:\Program Files\Microsoft\Edge\Application\
echo Install Edge or open manual\manual.html in a browser and print it as PDF.
pause
exit /b 1
