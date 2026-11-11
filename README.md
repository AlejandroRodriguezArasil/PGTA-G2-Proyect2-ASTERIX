# Decodificador ASTERIX CAT048 / CAT021

PGTA · Proyecto 2 · Grupo G2 · Repositorio: https://github.com/AlejandroRodriguezArasil/PGTA-G2-Proyect2-ASTERIX

Aplicación de escritorio que decodifica ficheros ASTERIX con mensajes CAT048 (radar de Barcelona) y CAT021 (ADS-B). Muestra los mensajes en una tabla, permite filtrarlos, exportarlos a CSV y simular las trayectorias en un mapa.

- **Manual de uso** (guía visual, paso a paso): `manual/Manual_de_uso.pdf` (en la entrega, también en `report/`).
- **Este README:** la parte técnica, es decir, de qué dato sale cada funcionalidad, qué criterio aplica y en qué parte del código está.

## Entrega

```
Group_02_P2.zip
├── DecodificadorASTERIX.exe           el ejecutable
├── code/                              este proyecto, igual que el repositorio de GitHub
├── report/
│   ├── Flujo_motor_decodificacion.pdf  explicación del código de la decodificación
│   ├── Manual_de_uso.pdf               guía de uso
│   ├── README.md                       este mismo README
│   └── Planificacion.pdf               planificación del proyecto
└── Enlace_GitHub.txt                  enlace al repositorio
```

Los ficheros .ast no van en la entrega: son los de la asignatura (`asterix_radar.ast`, `asterix_adsb.ast` y `asterix_combinado.ast`).

## El ejecutable

- **Funciona solo:** no necesita Python ni ningún otro fichero. Es para Windows de 64 bits.
- **Aviso de Windows:** la primera vez puede salir «Windows protegió su PC», porque el ejecutable no está firmado. Hay que pulsar «Más información» y después «Ejecutar de todas formas».
- **Arranque:** tarda unos segundos en abrirse, porque lleva dentro todo lo que necesita y lo descomprime al arrancar.
- **Internet:** el mapa de la simulación la necesita. Todo lo demás funciona sin conexión.

## Ejecutar desde el código

Hace falta Windows y Python 3; el proyecto se ha probado con Python 3.14. Desde esta carpeta:

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

**Regenerar el .exe:** doble clic en `crear_exe.bat`.
- Crea `.venv` si no existe e instala siempre `requirements.txt` y PyInstaller. La primera vez tarda unos minutos y necesita internet; las siguientes, solo comprueba que esté todo.
- Deja `DecodificadorASTERIX.exe` en esta carpeta, sin carpetas `build` ni `dist` ni fichero `.spec`.

**Regenerar el manual:** doble clic en `crear_manual.bat`. Convierte `manual/manual.html` en `manual/Manual_de_uso.pdf` con Microsoft Edge.

**Prueba de los recuentos:** con el entorno activado, `python -m pruebas.prueba_recuentos`. Decodifica los tres ficheros de la asignatura (los busca en `../Docs.Proyecto 2/Aterix files/`) y compara los recuentos con los esperados.

## Estructura de la carpeta

```
main.py              punto de entrada: la clase Aplicacion, con los métodos en el orden del flujo
funciones/           la lógica: lectura, decodificación, coordenadas, QNH, filtros, CSV y simulación
interfaz/            la ventana (ventana.py), el mapa (mapa.py) y los colores y tipografías (estilo.py)
pruebas/             prueba_recuentos.py, que no forma parte de la aplicación
manual/              Manual_de_uso.pdf y su fuente: manual.html y capturas/
crear_exe.bat        genera DecodificadorASTERIX.exe en esta carpeta
crear_manual.bat     vuelve a generar manual\Manual_de_uso.pdf
requirements.txt     librerías y versiones
```

Al ejecutar `crear_exe.bat` aparecen además `.venv/` y `DecodificadorASTERIX.exe`. Se generan en cada equipo, así que no están en el repositorio.

## Cómo funciona por dentro

### Decodificación

| Paso | Qué hace | Dónde |
| --- | --- | --- |
| Lectura | El fichero se lee una sola vez. Se recorre bloque a bloque (CAT y LEN); en cada registro se lee el FSPEC (bit FX) | `funciones/lector.py` |
| CAT048 | Los 14 DI que pide el enunciado, con una función por DI; los demás se saltan sumando su longitud. BDS 4.0, 5.0 y 6.0 dentro de I048/250 | `funciones/cat048.py`, `funciones/bds.py` |
| CAT021 | Los 9 DI que pide el enunciado, incluido el BPS del Reserved Expansion Field | `funciones/cat021.py` |
| Fichero completo | Une los pasos, aplica los descartes y cuenta los recuentos del resumen. Se ejecuta en un hilo aparte, con barra de progreso | `funciones/decodificar.py`, `main.decodificar_en_segundo_plano` |

- **Bloque desincronizado:** si las longitudes de los registros de un bloque no cuadran con su LEN, el bloque se cuenta como «desincronizado» en el resumen y se sigue con el siguiente.
- **Fichero cortado:** si se corta en mitad del último bloque, se lee hasta el bloque anterior y el resumen lo avisa (`lector.bloque_cortado`).
- **Fichero vacío o que no es ASTERIX:** se rechaza con un mensaje.
- **Si falla al abrir otro fichero:** se mantienen los datos que había cargados (tabla, filtros y simulación).

### Descartes obligatorios

Estos mensajes no entran en la tabla ni en el CSV. El resumen muestra cuántos se han descartado por cada motivo.

| Motivo | Dato | Criterio | Dónde |
| --- | --- | --- | --- |
| Sin posición | I048/040 (CAT048), I021/131 (CAT021) | El mensaje no trae ese DI (duda 10) | `decodificar.procesar_registro_048`, `cat021.decodificar_registro` |
| Fuera de la zona | LAT y LON en WGS84 | Fuera de 40,9–41,7° N y 1,5–2,6° E (límites excluidos) | `geo.dentro_de_zona` |
| CAT021 en tierra | GBS de I021/040 | GBS = 1 | `cat021.decodificar_registro` |

### Coordenadas

- **CAT048:** se parte de ρ y θ de I048/040 y de la altura, que es FL × 100 ft sin corregir (duda 7). Sin FL se usa h = 0 y `H_SIN_FL` = 1 (duda 8).
  - La cadena es la de GeoUtils, portada a Python con los mismos nombres: `CalculateElevation` → `change_radar_spherical2radar_cartesian` → `change_radar_cartesian2geocentric` → `change_geocentric2geodesic`.
  - Usa el radar de Barcelona: 41° 18' 02,5284" N, 02° 06' 07,4095" E, a 2,007 m de terreno más 25,25 m de antena.
  - Todo está en `geo.posicion_wgs84_048`.
- **CAT021:** LAT y LON vienen ya en I021/131. H es FL × 100 ft pasado a metros (duda 9).

### Corrección de altitud (QNH)

- **Fórmula:** altitud = FL × 100 + (BP − 1013,25) × 30 ft. BP es la presión de referencia que manda el avión: BDS 4.0 en CAT048 y BPS en CAT021.
- **Cuándo se corrige:** solo si FL × 100 < 6000 ft (duda 2). Con FL × 100 de 6000 ft o más, la celda queda vacía (duda 4). Por debajo, la altitud corregida puede pasar un poco de 6000.
- **BP guardado por avión** (por su TA, una tabla para CAT048 y otra para CAT021):
  - Se guarda el último BP no estándar que ha mandado cada avión.
  - Si un mensaje trae un BP estándar (duda 1), se corrige con el BP guardado.
  - El BP guardado se borra cuando el avión cruza 6000 ft hacia arriba (duda 5).
- **Dónde:** `qnh.corregir_altitud`, y el resultado va a la columna `ALT_CORREGIDA_FT`.

### Tabla y CSV

- **Columnas:** siempre las mismas 97 columnas, en el mismo orden, para cualquier fichero. Si el mensaje no trae un dato, su celda queda vacía; por ejemplo, las columnas de CAT021 en un mensaje CAT048.
- **Filas:** una por mensaje, en el orden del fichero. La tabla las muestra en páginas de 500.
- **Formato:**
  - Separador `;` y coma decimal, para que Excel en español lo abra bien con doble clic.
  - LAT y LON con 8 decimales; H y ALT_CORREGIDA_FT con 2; el resto, con su valor exacto.
  - TIME como hh:mm:ss,sss; texto en UTF-8.
- **Columnas extra:** LAT, LON y H en WGS84, `H_SIN_FL` y `ALT_CORREGIDA_FT`.
- **Dónde:** `funciones/exportar_csv.py`, con `COLUMNAS` y `formatear_valor`.

**Exportar:**
- **Exportar todo:** guarda todos los mensajes decodificados.
- **Exportar lo filtrado:** guarda solo los que quedan tras los filtros. Se activa al aplicar un filtro que deje al menos un mensaje.
- **Dónde se guarda:** en las dos opciones se elige carpeta y nombre en la ventana «Guardar CSV».
- **Hilo aparte:** la escritura va en un hilo, con barra de progreso (`main.exportar`).
- **Cerrar a media exportación:** si se cierra la ventana mientras se exporta, pregunta antes. Si se cierra igualmente, se borra el CSV incompleto (`main.al_cerrar_ventana`).

**Excel:**
- Si sale «#######» en una celda (pasa con TIME), la columna es demasiado estrecha. Se arregla ensanchándola: doble clic en el borde derecho de la cabecera, o Formato > Autoajustar ancho de columna.
- Al abrir con doble clic, Excel quita el cero inicial de `MODE3A` y puede leer alguna `TA` como número. Para verlas igual que en la aplicación, hay que importar esas columnas como texto.

### Filtros

Se marcan las condiciones y se pulsa «Aplicar filtros» (o Intro en un campo de texto). Se combinan todas, una detrás de otra (`filtros.aplicar_filtros`). «Quitar filtros» deja el panel como al principio y vuelve a mostrar todo.

| Filtro | Dato | Criterio | Dónde |
| --- | --- | --- | --- |
| Categoría | `CAT` | Se quedan los mensajes de la categoría elegida (048 o 021) | `filtros.filtrar_por_categoria` |
| Quitar blancos puros | TYP de I048/020 (`I048_020_TYP`) | Se quitan los CAT048 con TYP = 0, 1, 2 o 3 (sin detección, PSR, SSR o PSR+SSR): no vienen de una interrogación Modo S (duda 13) | `filtros.es_blanco_puro` |
| Quitar transponder fijo | Modo 3/A (`MODE3A`), RAB de I048/020 y de I021/040 | Se quitan los mensajes con Modo 3/A 7777 o RAB = 1 (duda 14) | `filtros.es_transponder_fijo` |
| Quitar aeronaves en tierra | STAT de I048/230 (`I048_230_STAT`) | Se quitan los CAT048 con STAT = 1 o 3. Los CAT021 en tierra (GBS = 1) ya se descartaron al decodificar | `filtros.quitar_en_tierra` |
| Solo mensajes con FL | `FL` | Se quedan los mensajes con nivel de vuelo | `filtros.solo_con_fl` |
| Altitud máxima | `ALT_CORREGIDA_FT` o, si está vacía, `FL` × 100 | Se quedan los mensajes con altitud ≤ valor; los que no tienen ninguna se quitan | `filtros.filtrar_altitud_maxima` |
| Aeronave | `TI`, `TA`, `MODE3A` | Se quedan los mensajes en los que el texto aparece en alguna de las tres, sin distinguir mayúsculas | `filtros.buscar_aeronave` |

Entrada del P3: Categoría CAT048 + Quitar aeronaves en tierra + Solo mensajes con FL + Altitud máxima 6000 (20.952 mensajes con `asterix_combinado.ast`).

### Simulación

| Funcionalidad | Cómo funciona | Dónde |
| --- | --- | --- |
| Qué se simula | Los mensajes que quedan en la pestaña Datos, con sus filtros, ordenados por `TIME_S`. Un aviso encima del mapa lo recuerda | `simulacion.preparar` |
| Saltos | Siempre de 1 s de hora del día. Reproducir, Pausa, +1 s y Reset (vuelve a la primera hora). Al pasar a la pestaña Datos, la simulación se pausa | `simulacion.avanzar_un_segundo`, `main.tic_reloj` |
| Velocidad | De x1 a x60. Solo cambia la espera entre saltos: x1, un salto por segundo; x60, 60 por segundo | `main.ESPERA_POR_VELOCIDAD_MS` |
| Avión | Un avión es la pareja (categoría, TA) o, sin TA, (categoría, track number). El mismo avión visto por radar y por ADS-B son dos aviones del mapa | `simulacion.identificador_avion` |
| Desaparición | Un avión desaparece si pasa más de 12 s sin mensajes | `simulacion.SEGUNDOS_PARA_CADUCAR` |
| Ir a la hora | Se escribe hh:mm (UTC) y se pulsa Ir o Intro. Cada avión aparece en su última posición conocida antes de esa hora | `simulacion.ir_a_segundo` |
| Sistema | Ambos, Radar (CAT048) o ADS-B (CAT021) | `mapa.sistema_visible` |
| Dibujo | Radar en azul y ADS-B en naranja. El avión pulsado y su pareja, en rojo. Blancos puros: punto gris con su tipo y número («PSR 45»). Transponder fijo: antena. Radar de Barcelona: triángulo. Rectángulo de la zona del filtro geográfico | `interfaz/mapa.py` |
| Siluetas | Apuntan al rumbo: en radar, el de I048/200; en ADS-B, la dirección en la que se ha movido (se recalcula cada 100 m, solo para dibujar). Sin rumbo, miran al norte | `mapa.rumbo_para_dibujar` |
| Etiquetas y estelas | Casillas para mostrar u ocultar el callsign (o la TA) y la línea con las últimas 15 posiciones | `mapa.texto_etiqueta`, `mapa.dibujar_estela` |

**Panel derecho:**
- **Leyenda:** plegable y recogida al empezar.
- **En el mapa:** tres cifras, radar, ADS-B y blancos puros. Los blancos puros no cuentan como radar y el transponder fijo no se cuenta.
- **Avión seleccionado:** los datos del último mensaje del avión pulsado (`mapa.texto_informacion`). Con el selector Radar / ADS-B se pasa a su pareja del otro sistema (misma TA); la opción sale en gris si la pareja no está en el mapa.
- **Desplazamiento:** el panel se desplaza con la rueda del ratón o con el panel táctil, como el panel lateral y la tabla de la pestaña Datos (`ventana.Desplazador`).

**Mapa:** usa las teselas de OpenStreetMap. Su [política de uso](https://operations.osmfoundation.org/policies/tiles/) bloquea la identificación genérica de tkintermapview, por eso `interfaz/mapa.py` pide las teselas con un User-Agent propio. Se muestra la atribución, solo se descargan las teselas que se ven y no se guardan para usarlas sin conexión.

## En qué orden leer el código

1. `main.py`: la aplicación. Los métodos van en el orden del flujo: elegir fichero → decodificar → mostrar → filtrar → exportar → simular.
2. `funciones/decodificar.py`: decodifica un fichero completo y aplica los descartes.
3. `funciones/lector.py`: bloques, FSPEC y funciones de bits.
4. `funciones/cat048.py` y `funciones/bds.py`: los DI de CAT048 y los BDS 4.0, 5.0 y 6.0.
5. `funciones/cat021.py`: los DI de CAT021 y el BPS del Reserved Expansion Field.
6. `funciones/geo.py`: port de GeoUtils.cs (radar → WGS84 y proyección estereográfica para el P3).
7. `funciones/qnh.py`: corrección de altitud con el QNH por debajo de 6000 ft.
8. `funciones/exportar_csv.py`: columnas y formato del CSV.
9. `funciones/filtros.py`: un filtro por función.
10. `funciones/simulacion.py` e `interfaz/mapa.py`: lógica de la simulación y lo que se dibuja en el mapa.
11. `interfaz/ventana.py` e `interfaz/estilo.py`: construcción de la ventana, colores y tipografías.
12. `funciones/decisiones.py`: decisiones de las dudas del enunciado.

## Decisiones de las dudas del enunciado

| # | Duda | Decisión |
| --- | --- | --- |
| 1 | Presión estándar | 1013–1013,5 hPa en CAT048; 1012,8 y 1013,6 hPa en CAT021 (el BPS va en saltos de 0,8 hPa) |
| 2 | Umbral de 6000 ft | Se compara con FL × 100 sin corregir |
| 3 | Sin ningún BP no estándar previo | No se corrige (celda vacía) |
| 4 | FL × 100 de 6000 ft o más | La altitud corregida queda vacía |
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
