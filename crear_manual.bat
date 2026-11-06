@echo off
rem Genera manual\Manual_de_uso.pdf a partir de manual\manual.html con Microsoft Edge (viene con Windows).
rem Las capturas que usa el manual estan en manual\capturas\.
rem --headless: sin abrir ventana. --no-pdf-header-footer: sin fecha ni ruta en los margenes.

"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --headless --disable-gpu --no-pdf-header-footer --print-to-pdf="%~dp0manual\Manual_de_uso.pdf" "%~dp0manual\manual.html"

echo.
echo Manual generado: %~dp0manual\Manual_de_uso.pdf
pause
