# Decodificador ASTERIX CAT048 / CAT021

PGTA · Proyecto 2 · Grupo G2

Aplicación de escritorio que decodifica ficheros ASTERIX con mensajes CAT048 (radar de Barcelona) y CAT021 (ADS-B). Muestra los mensajes en una tabla, permite filtrarlos, exportarlos a CSV y simular las trayectorias en un mapa.

**Manual de uso:** `manual/Manual_de_uso.pdf`, paso a paso y con capturas.

## Estructura de la carpeta

```
main.py              punto de entrada de la aplicación
funciones/           la lógica: lectura, decodificación, coordenadas, QNH, filtros, CSV y simulación
interfaz/            la ventana: construcción (ventana), mapa, y colores y tipografías (estilo)
pruebas/             prueba_recuentos.py, que no forma parte de la aplicación
manual/              Manual_de_uso.pdf y su fuente: manual.html y capturas/
crear_exe.bat        genera el .exe en dist\
crear_manual.bat     genera manual\Manual_de_uso.pdf con Microsoft Edge
requirements.txt     librerías y versiones
dist/                generada por crear_exe.bat; no va en el .zip
.venv/               entorno virtual de Python, cada uno crea el suyo; no va en el .zip
```

## Qué va en el .zip de la entrega

```
DecodificadorASTERIX.exe       el ejecutable (copiado de dist\)
Manual_de_uso.pdf              copia de manual/Manual_de_uso.pdf
Codigo/                        esta carpeta, sin dist/ ni .venv/
Documentacion/                 la documentación
```

Tampoco van `build`, `__pycache__` ni los `.spec`, ni los ficheros .ast: son los de la asignatura (`asterix_radar.ast`, `asterix_adsb.ast` y `asterix_combinado.ast`).

## Cómo se ejecuta

**Con el ejecutable:** doble clic en `DecodificadorASTERIX.exe`. No hace falta instalar nada. El mapa de la simulación necesita conexión a internet.

**Con Python** (Windows, desde esta carpeta). El proyecto se ha probado con Python 3.14.

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Para volver a generar el `.exe`: `.venv\Scripts\python -m pip install pyinstaller` (una sola vez) y después `crear_exe.bat`. El ejecutable queda en `dist\`.

**Prueba de los recuentos:** desde esta carpeta, con el entorno activado:

```
python -m pruebas.prueba_recuentos
```

Decodifica los tres ficheros de la asignatura y compara los recuentos con los esperados. Los busca en `../Docs.Proyecto 2/Aterix files/`. Se ejecuta con `-m` desde esta carpeta para que Python encuentre `funciones/`.

## Cómo se usa

**Pestaña Datos**
- **Abrir fichero .ast** (arriba a la derecha): el fichero se decodifica con una barra de progreso. A la izquierda aparece el resumen: registros leídos, mensajes en la tabla y descartados por motivo.
- **Descartes obligatorios:** los mensajes fuera de 40,9–41,7° N y 1,5–2,6° E, los CAT021 en tierra (GBS = 1) y los mensajes sin posición no entran.
- **Tabla:** todos los mensajes, en el orden del fichero y en páginas de 500.
- **Filtros:** se marcan las condiciones y se pulsa **Aplicar filtros**. Se pueden combinar todas; **Quitar filtros** vuelve a mostrar todo.
- **Exportar todo** / **Exportar lo filtrado:** guardan un CSV donde se elija.

**CSV**
- Separador `;` y coma decimal, una fila por mensaje y una columna por subcampo (97 columnas). La celda queda vacía si el mensaje no trae ese dato.
- **Columnas extra:** LAT, LON y H en WGS84, y ALT_CORREGIDA_FT (corrección QNH por debajo de 6000 ft).
- **Excel:** quita el cero inicial de `MODE3A` y puede leer alguna `TA` como número; para verlas igual, hay que importar esas columnas como texto.

**Pestaña Simulación**
- **Qué se simula:** los mensajes que se ven en la pestaña Datos, con sus filtros. El aviso de encima del mapa lo recuerda.
- **Controles:** **Reproducir**, **Pausa**, **+1 s** y **Reset**. Los saltos son siempre de 1 s de hora del día; la velocidad (x1 a x60) solo cambia cada cuánto se dibujan. Al cambiar a la pestaña Datos, la simulación se pausa.
- **Sistema:** Ambos, Radar o ADS-B. Radar en azul y ADS-B en naranja; con «Ambos», un avión visto por los dos sistemas aparece dos veces.
- **Siluetas:** apuntan al rumbo del avión. En radar es el de I048/200; en ADS-B, la dirección en la que se ha movido (se recalcula cada 100 m), solo para dibujar.
- **Blancos puros** (CAT048 con TYP 0, 1, 2 o 3, sin Modo S): se dibujan con un punto gris, sin silueta ni rumbo. Su etiqueta es el tipo (PSR, SSR, PSR+SSR o Sin det.) seguido del Modo 3/A o, si no lo traen, del track number; por ejemplo, «PSR 45». Se quitan con el filtro «Quitar blancos puros».
- **En el mapa:** tres cifras, radar, ADS-B y blancos puros. Los blancos puros no cuentan como radar y el transponder fijo no se cuenta.
- **Clic en un avión:** muestra su información en el panel y resalta también el mismo avión visto por el otro sistema. Con el selector **Radar / ADS-B** del panel se pasa a los datos de ese mismo avión en el otro sistema; la opción sale en gris si no está en el mapa por ese sistema.
- **Ir a la hora (hh:mm):** salta a ese momento; cada avión aparece en su última posición conocida.
- **Desaparición:** un avión desaparece con más de 12 s sin mensajes. El transponder fijo (7777) se dibuja con una antena y siempre está quieto.

## Filtros

| Filtro | Columna | Criterio |
| --- | --- | --- |
| Categoría | `CAT` | Se quedan los mensajes de la categoría elegida (048 o 021) |
| Quitar blancos puros | `I048_020_TYP` | Se quitan los CAT048 con TYP = 0, 1, 2 o 3 (no vienen de una interrogación Modo S) |
| Quitar transponder fijo | `MODE3A`, `I048_020_RAB`, `I021_040_RAB` | Se quitan los mensajes con Modo 3/A 7777 o RAB = 1 |
| Quitar aeronaves en tierra | `I048_230_STAT` | Se quitan los CAT048 con STAT = 1 o 3 |
| Solo mensajes con FL | `FL` | Se quedan los mensajes con nivel de vuelo |
| Altitud máxima | `ALT_CORREGIDA_FT` o, si está vacía, `FL` × 100 | Se quedan los mensajes con altitud ≤ al valor; los que no tienen ninguna se quitan |
| Aeronave | `TI`, `TA`, `MODE3A` | Se quedan los mensajes en los que el texto aparece en alguna de las tres |

Entrada del P3: Categoría CAT048 + Quitar aeronaves en tierra + Solo mensajes con FL + Altitud máxima 6000.

## En qué orden leer el código

1. `main.py`: la aplicación. Los métodos van en el orden del flujo: elegir fichero → decodificar → mostrar → filtrar → exportar → simular.
2. `funciones/decodificar.py`: decodifica un fichero completo y aplica los descartes.
3. `funciones/lector.py`: bloques, FSPEC y funciones de bits.
4. `funciones/cat048.py` y `funciones/bds.py`: los DI de CAT048 y los BDS 4.0, 5.0 y 6.0.
5. `funciones/cat021.py`: los DI de CAT021 y el BPS del Reserved Expansion Field.
6. `funciones/geo.py`: port de GeoUtils.cs (radar → WGS84 y proyección estereográfica para el P3).
7. `funciones/qnh.py`: corrección de altitud (D14 y D15).
8. `funciones/exportar_csv.py`: columnas y formato del CSV.
9. `funciones/filtros.py`: un filtro por función.
10. `funciones/simulacion.py` e `interfaz/mapa.py`: lógica de la simulación y lo que se dibuja en el mapa.
11. `interfaz/ventana.py` e `interfaz/estilo.py`: construcción de la ventana, y colores y tipografías.
12. `funciones/decisiones.py`: decisiones de las dudas del enunciado.

`pruebas/prueba_recuentos.py` comprueba los recuentos de los tres ficheros de la asignatura; no forma parte de la aplicación.

## Decisiones de las dudas del enunciado

| # | Duda | Decisión |
| --- | --- | --- |
| 1 | Presión estándar | 1013–1013,5 hPa en CAT048; 1012,8 y 1013,6 hPa en CAT021 (el BPS va en saltos de 0,8 hPa) |
| 2 | Umbral de 6000 ft | Se compara con FL × 100 sin corregir |
| 3 | Sin ningún BP no estándar previo | No se corrige (celda vacía) |
| 4 | Altitud corregida a 6000 ft o más | Celda vacía |
| 5 | BP guardado | Se borra al cruzar 6000 ft hacia arriba; un BP no estándar se guarda a cualquier altitud |
| 6 | FL no validado o garbled | Se corrige igual |
| 7 | Altura para transformar CAT048 | FL sin corregir |
| 8 | CAT048 sin FL | Se transforma con h = 0 y `H_SIN_FL` = 1 |
| 9 | h de CAT021 | FL × 100 ft en metros |
| 10 | Mensajes sin posición | Se descartan |
| 11 | Fichero combinado | Un solo CSV con la columna CAT |
| 12 | I021/040 | Se decodifica entero |
| 13 | TYP = 000 | Cuenta como blanco puro |
| 14 | Transponder fijo | Modo 3/A 7777 o RAB = 1 |

## Mapa

El mapa usa las teselas de OpenStreetMap. Su [política de uso](https://operations.osmfoundation.org/policies/tiles/) bloquea la identificación genérica de tkintermapview, por eso `interfaz/mapa.py` pide las teselas con un User-Agent propio. Se muestra la atribución, solo se descargan las teselas que se ven y no se guardan para usarlas sin conexión.
