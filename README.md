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
| CAT021 | Los 8 DI que el enunciado marca en verde, incluido el BPS del Reserved Expansion Field. De I021/040 solo se lee el bit GBS, para el descarte en tierra; el resto se salta por su longitud (FX) | `funciones/cat021.py` |
| Fichero completo | Une los pasos, aplica los descartes y cuenta los recuentos del resumen. Se ejecuta en un hilo aparte, con barra de progreso | `funciones/decodificar.py`, `main.decodificar_en_segundo_plano` |

- **Fichero vacío o que no es ASTERIX:** se rechaza con un mensaje.
- **Si falla al abrir otro fichero:** se mantienen los datos que había cargados (tabla, filtros y simulación).

### Ficheros dañados

- **Fichero cortado:** si se corta en mitad del último bloque, se lee hasta el bloque anterior y el resumen lo avisa.
- **Bloque de otra categoría:** no es un error; se salta entero y se sigue con el siguiente.
- **Registro mal formado:** si las longitudes de los registros de un bloque no cuadran con su LEN, el bloque se cuenta como «desincronizado» en el resumen y se sigue con el siguiente.
- **LEN no válido (menor que 3):** en el primer bloque, el fichero se rechaza; más adelante, se para en ese bloque, se queda todo lo leído y el resumen dice en qué octeto está. Este caso y el del fichero cortado los comprueba `lector.problema_bloque`.
- **Límites:** ASTERIX no tiene marcas de sincronización ni suma de control. Si un LEN está mal, lo que viene detrás no se puede recuperar de forma fiable, y un valor cambiado dentro de un registro de longitud correcta no se puede detectar. No se usan heurísticas que la norma no define.

### Descartes obligatorios

Estos mensajes no entran en la tabla ni en el CSV. El resumen muestra cuántos se han descartado por cada motivo.

| Motivo | Dato | Criterio | Dónde |
| --- | --- | --- | --- |
| Sin posición | I048/040 (CAT048), I021/131 (CAT021) | El mensaje no trae ese DI. Sin posición no se puede aplicar el filtro geográfico obligatorio | `decodificar.procesar_registro_048`, `cat021.decodificar_registro` |
| Fuera de la zona | LAT y LON en WGS84 | Fuera de 40,9–41,7° N y 1,5–2,6° E (límites excluidos) | `geo.dentro_de_zona` |
| CAT021 en tierra | GBS de I021/040 | GBS = 1. Se comprueba antes que la posición | `cat021.decodificar_registro` |

Mensajes sin posición en `asterix_combinado.ast`: 6.025 CAT048 y 890 CAT021. De los 890, 333 están además en tierra y el resumen los cuenta como «en tierra», así que como «sin posición» salen 557.

### Coordenadas

- **CAT048:** se parte de ρ y θ de I048/040 y de la altura, que es FL × 100 ft sin corregir. Sin FL se usa h = 0 y `H_SIN_FL` = 1.
  - La cadena es la de GeoUtils, portada a Python con los mismos nombres: `CalculateElevation` → `change_radar_spherical2radar_cartesian` → `change_radar_cartesian2geocentric` → `change_geocentric2geodesic`.
  - Usa el radar de Barcelona: 41° 18' 02,5284" N, 02° 06' 07,4095" E, a 2,007 m de terreno más 25,25 m de antena.
  - Todo está en `geo.posicion_wgs84_048`.
- **CAT021:** LAT y LON vienen ya en I021/131. No tiene altura WGS84 (no se decodifica I021/140), así que `H` y `H_SIN_FL` quedan vacías en todas sus filas.

### Corrección de altitud (QNH)

- **Fórmula:** altitud = FL × 100 + (BP − 1013,25) × 30 ft. BP es la presión de referencia que manda el avión: BDS 4.0 en CAT048 y BPS en CAT021.
- **Cuándo se corrige:** solo si FL × 100 < 6000 ft. Con FL × 100 de 6000 ft o más, la celda queda vacía. Por debajo, la altitud corregida puede pasar un poco de 6000.
- **BP guardado por avión** (por su TA, una tabla para CAT048 y otra para CAT021):
  - Se guarda el último BP no estándar que ha mandado cada avión, a cualquier altitud.
  - Si un mensaje trae un BP estándar (1013–1013,5 hPa en CAT048; 1012,8 o 1013,6 hPa en CAT021), se corrige con el BP guardado.
  - Si el avión no tiene ningún BP guardado, la celda queda vacía.
  - El BP guardado se borra cuando el avión cruza 6000 ft hacia arriba.
- **Dónde:** `qnh.corregir_altitud`, y el resultado va a la columna `ALT_CORREGIDA_FT`.

### Tabla y CSV

- **Columnas:** siempre las mismas 82 columnas, en el mismo orden, para cualquier fichero. Si el mensaje no trae un dato, su celda queda vacía; por ejemplo, las columnas de CAT021 en un mensaje CAT048.
- **Filas:** una por mensaje, en el orden del fichero. La tabla las muestra en páginas de 500.
- **Formato:**
  - Separador `;` y coma decimal, para que Excel en español lo abra bien con doble clic.
  - LAT y LON con 8 decimales; H y ALT_CORREGIDA_FT con 2; el resto, con su valor exacto.
  - TIME como hh:mm:ss,sss; texto en UTF-8.
- **Columnas extra:** LAT, LON y H en WGS84, `H_SIN_FL` y `ALT_CORREGIDA_FT`. `H` y `H_SIN_FL` son solo de CAT048.
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
| Quitar blancos puros | TYP de I048/020 (`I048_020_TYP`) | Se quitan los CAT048 con TYP = 0, 1, 2 o 3 (sin detección, PSR, SSR o PSR+SSR): no vienen de una interrogación Modo S | `filtros.es_blanco_puro` |
| Quitar transponder fijo | Modo 3/A (`MODE3A`) | Se quitan los mensajes con Modo 3/A 7777 | `filtros.es_transponder_fijo` |
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
| Avión en el mapa | La pareja (categoría, TA) o, sin TA, (categoría, track number). El mismo avión visto por radar y por ADS-B son dos siluetas | `simulacion.identificador_avion` |
| Desaparición | Un avión desaparece si pasa más de 12 s sin mensajes | `simulacion.SEGUNDOS_PARA_CADUCAR` |
| Ir a otra hora | Con «Ir a la hora» (hh:mm y Ir o Intro) o con la barra de tiempo, que va de la primera a la última hora de los datos y avanza sola al reproducir. Al arrastrarla, el reloj enseña la hora; el salto se hace al soltar. La simulación se repite segundo a segundo hasta esa hora, sin dibujar ni anotar eventos, así que cada avión queda igual que si se hubiera reproducido hasta ahí | `simulacion.ir_a_segundo`, `main.soltar_barra_tiempo` |
| Sistema | Ambos, Radar (CAT048) o ADS-B (CAT021). También filtra las listas de tráfico | `mapa.sistema_visible`, `mapa.categorias_visibles` |
| Dibujo | Radar en azul y ADS-B en naranja. El avión pulsado y su pareja, en rojo. Blancos puros: punto gris con su tipo y número («PSR 45»). Transponder fijo: antena. Radar de Barcelona: triángulo. Rectángulo de la zona del filtro geográfico | `interfaz/mapa.py` |
| Siluetas | Apuntan al rumbo: en radar, el de I048/200; en ADS-B, la dirección en la que se ha movido (se recalcula cada 100 m, solo para dibujar). Sin rumbo, miran al norte | `mapa.rumbo_para_dibujar` |
| Etiquetas | Bloque de datos de dos líneas, como en una pantalla radar: el callsign (o la TA) y, debajo, el nivel con su tendencia y la velocidad GS en nudos (I048/200 o, si no, BDS 5.0), por ejemplo «045↑ 210». En ADS-B no hay velocidad, porque no se decodifica. Un avión que ven los dos sistemas lleva una sola etiqueta, en la silueta de radar si está en el mapa y, si no, en la de ADS-B; la otra silueta va sin texto. Los aviones en tierra no llevan etiqueta (en LEBL se amontonan y tapan el aeropuerto), salvo el seleccionado: aparece al despegar y se quita al aterrizar. En cada salto solo se repasan las etiquetas de los aviones que han cambiado, y el texto de un marcador solo se cambia cuando es distinto | `mapa.texto_etiqueta`, `mapa.lleva_etiqueta`, `mapa.actualizar_etiquetas_de` |
| Estelas | La línea con las últimas 15 posiciones de cada avión | `mapa.dibujar_estela` |
| Seguir | Con un avión seleccionado, el mapa se centra en él cada vez que se mueve, sin cambiar el zoom. El mapa se mueve como al arrastrarlo (`draw_move`), que es más ligero que volver a crear todas las teselas. Si el avión desaparece, se deja de seguir | `main.seguir_avion`, `mapa.centrar_en` |

**Tráfico: en tierra o en vuelo.** En el tráfico (listas y eventos) un avión es su TA, lo vea un sistema o los dos. Los blancos puros (sin TA) y el transponder fijo no son tráfico, pero se siguen dibujando en el mapa.

| Criterio | Cómo funciona | Dónde |
| --- | --- | --- |
| Radar | STAT de I048/230 (CAT048 v1.31, §5.2.23): 1 y 3, en tierra; 0 y 2, en vuelo; 4 a 7 no dicen si está en tierra o en el aire. Un mensaje sin I048/230 tampoco dice nada | `simulacion.estado_observado` |
| ADS-B | Los mensajes en tierra (GBS = 1) se descartan al decodificar, así que todo lo que llega por ADS-B está en vuelo | `simulacion.estado_observado` |
| Los dos sistemas | Si el radar ve el avión con un STAT que dice tierra o vuelo, manda el radar y el mensaje ADS-B no cuenta | `simulacion.estado_observado` |
| Confirmación | Un estado nuevo (también el primero) solo se acepta tras 2 mensajes seguidos que lo digan. Un mensaje que no dice nada no corta la cuenta; uno con el estado de antes, sí. Así un STAT que parpadea no da despegues falsos. Mientras no hay ninguno confirmado, el estado es desconocido y el avión no sale en ninguna lista | `simulacion.cambiar_estado`, `simulacion.MENSAJES_PARA_CAMBIAR_ESTADO` |

**Eventos** (franja debajo del mapa, el más reciente arriba; se guardan los 300 últimos):

| Evento | Cuándo | Dónde |
| --- | --- | --- |
| Nuevo contacto | La primera vez que aparece un avión, o cuando vuelve después de haber desaparecido | `simulacion.actualizar_trafico` |
| Despega / Aterriza | Cambio confirmado de en tierra a en vuelo / de en vuelo a en tierra. A la derecha de la franja, los totales | `simulacion.cambiar_estado` |
| Pérdida de contacto | El avión pasa más de 12 s sin mensajes por ningún sistema. Su hora es la de la simulación cuando desaparece | `simulacion.quitar_caducados` |

- Cada evento lleva la hora del mensaje que lo provoca, el callsign (o la TA) y el sistema (R radar, A ADS-B). Con un clic se selecciona el avión y se centra el mapa en él, si sigue a la vista.
- Solo salen al reproducir o al avanzar 1 s. Al saltar de hora (Ir a la hora, la barra de tiempo o Reset) el estado se recalcula en silencio, el registro se vacía y los totales empiezan de cero.
- Con `asterix_radar.ast` entero salen 123 despegues y 83 aterrizajes, todos a menos de 2 km de LEBL y con FL entre −0,75 y 1,75 (uno no trae FL): son despegues y aterrizajes en la pista.

**Tendencia vertical y nivel** (`simulacion.calcular_tendencia`, `simulacion.texto_nivel`):
- **Tendencia:** ↑ sube, ↓ baja, → nivelado. En radar, con la velocidad vertical del BDS 6.0 (BAR o, si no viene, IVV). Si no la hay, y siempre en ADS-B, con la variación del FL entre el mensaje más antiguo y el más reciente de los últimos 10 s (separados al menos 4 s, una vuelta de antena). Umbral: ±300 ft/min (`UMBRAL_TENDENCIA_FT_MIN`).
- **Nivel, al estilo de control aéreo:** «A025» si hay altitud corregida por QNH (en cientos de pies) y «FL045» si no, con la flecha de tendencia: «FL045↑». En las etiquetas del mapa va sin el prefijo, para que sea corto.

**Panel derecho**, de arriba abajo:
- **Tráfico:** los contadores «✈ N en vuelo» y «▣ N en tierra», cada uno encima de su lista, y las cifras de lo dibujado en el mapa (radar, ADS-B y blancos puros; los blancos puros no cuentan como radar y el transponder fijo no se cuenta).
  - En vuelo: Callsign | Nivel | Sist.; en tierra: Callsign | Sist. Sist. es R, A o RA según qué sistemas lo ven. Una fila por TA, en orden alfabético, y solo con los sistemas que deja ver el selector Sistema (`simulacion.filas_trafico`).
  - Clic en una fila: se selecciona el avión como en el mapa (su silueta de radar si la tiene; si no, la de ADS-B) y se centra el mapa en él (`main.al_pulsar_fila_trafico`).
  - Para que vaya fluido a x60, las listas no se rehacen en cada salto: se añaden, quitan o cambian solo las filas que cambian, y solo se reordena cuando entra o sale alguien (`ventana.ListaIncremental`). El registro de eventos igual: solo se añaden los nuevos (`ventana.RegistroEventos`).
- **Avión seleccionado:** los datos del último mensaje del avión pulsado, con su estado y su tendencia (`mapa.texto_informacion`). Con el selector Radar / ADS-B se pasa a su pareja del otro sistema (misma TA); la opción sale en gris si la pareja no está en el mapa.
- **Leyenda:** plegable y recogida al empezar.
- **Desplazamiento:** el panel se desplaza con la rueda del ratón o con el panel táctil, como el panel lateral y la tabla de la pestaña Datos (`ventana.Desplazador`). Encima de una lista con filas ocultas se desplaza la lista.

**Rendimiento:** con `asterix_combinado.ast` a x60, un salto (lógica, mapa y paneles) tarda de media 2,6 ms y se mantienen los 60 saltos por segundo.

**Mapa:** usa las teselas de OpenStreetMap. Su [política de uso](https://operations.osmfoundation.org/policies/tiles/) bloquea la identificación genérica de tkintermapview, por eso `interfaz/mapa.py` pide las teselas con un User-Agent propio. Se muestra la atribución, solo se descargan las teselas que se ven y no se guardan para usarlas sin conexión.

## En qué orden leer el código

1. `main.py`: la aplicación. Los métodos van en el orden del flujo: elegir fichero → decodificar → mostrar → filtrar → exportar → simular.
2. `funciones/decodificar.py`: decodifica un fichero completo y aplica los descartes.
3. `funciones/lector.py`: bloques, FSPEC y funciones de bits.
4. `funciones/cat048.py` y `funciones/bds.py`: los DI de CAT048 y los BDS 4.0, 5.0 y 6.0.
5. `funciones/cat021.py`: los DI de CAT021, el bit GBS de I021/040 y el BPS del Reserved Expansion Field.
6. `funciones/geo.py`: port de GeoUtils.cs (radar → WGS84 y proyección estereográfica para el P3).
7. `funciones/qnh.py`: corrección de altitud con el QNH por debajo de 6000 ft.
8. `funciones/exportar_csv.py`: columnas y formato del CSV.
9. `funciones/filtros.py`: un filtro por función.
10. `funciones/simulacion.py` e `interfaz/mapa.py`: lógica de la simulación y lo que se dibuja en el mapa.
11. `interfaz/ventana.py` e `interfaz/estilo.py`: construcción de la ventana, colores y tipografías.

## Criterios aplicados

Cada constante está en el módulo que la usa, con un comentario que explica el criterio.

| Criterio | Motivo |
| --- | --- |
| Presión estándar: 1013–1013,5 hPa en CAT048; 1012,8 y 1013,6 hPa en CAT021 | El rango es el del enunciado. En ADS-B el BPS va en saltos de 0,8 hPa y nunca cae en 1013–1013,5: 1012,8 y 1013,6 son su presión estándar (`qnh.py`) |
| El umbral de 6000 ft se compara con FL × 100 sin corregir | Hay que decidir si se corrige antes de tener la altitud corregida (`qnh.UMBRAL_QNH_FT`) |
| Por debajo de 6000 ft, sin ningún BP no estándar guardado: altitud corregida vacía | Sin un QNH del avión no hay con qué corregir |
| A 6000 ft o más: altitud corregida vacía | Por encima de la altitud de transición no se corrige; la columna solo se rellena cuando hay altitud corregida |
| El BP guardado se borra al cruzar 6000 ft hacia arriba; un BP no estándar se guarda a cualquier altitud | Al pasar la altitud de transición el avión pone la presión estándar; un BP no estándar siempre es el QNH que ha puesto |
| Un FL con V = 1 o G = 1 se corrige igual | El enunciado no los excluye; V y G quedan en sus columnas del CSV |
| CAT048 se transforma a WGS84 con el FL sin corregir | Es la altura que da el radar; la altitud corregida solo existe por debajo de 6000 ft |
| CAT048 sin FL: se transforma con altura 0 y `H_SIN_FL` = 1 | La transformación necesita una altura; `H_SIN_FL` marca que H no sale de un FL (`decodificar.ALTURA_SI_NO_HAY_FL_M`) |
| CAT021 no tiene altura WGS84: `H` y `H_SIN_FL` vacías | No se decodifica I021/140 (Geometric Height); LAT y LON vienen ya en I021/131 |
| Los mensajes sin posición se descartan: 6.025 CAT048 y 890 CAT021 en `asterix_combinado.ast` | Sin posición no se puede aplicar el filtro geográfico obligatorio |
| Un solo CSV para el fichero combinado, con la columna CAT | Todos los CSV tienen las mismas columnas; CAT dice la categoría de cada fila |
| De I021/040 solo se lee el bit GBS | En CAT021 el enunciado pide los DI en verde, e I021/040 no lo está; el GBS hace falta para descartar los aviones en tierra |
| TYP = 0 (sin detección) es blanco puro | Como PSR, SSR y PSR+SSR, no viene de una interrogación Modo S (`filtros.TIPOS_BLANCO_PURO`) |
| Transponder fijo: solo Modo 3/A 7777 | Es el código del transponder de referencia en tierra (`filtros.MODO_3A_TRANSPONDER_FIJO`). La columna `I048_020_RAB` se queda en el CSV porque es un subcampo de I048/020, que sí se decodifica |
