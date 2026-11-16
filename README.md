# ASTERIX Decoder CAT048 / CAT021

PGTA · Project 2 · Group 02 · Repository: https://github.com/AlejandroRodriguezArasil/PGTA-G2-Proyect2-ASTERIX

**Authors:** Alejandro Rodríguez Arasil and Pau Ramírez Hermoso.

Desktop application that decodes ASTERIX files with CAT048 (Barcelona radar) and CAT021 (ADS-B) messages. It shows the messages in a table, filters them, exports them to CSV and simulates the trajectories on a map.

- **User manual** (visual, step-by-step guide): `manual/User_Manual.pdf` (in the delivery, also in `report/`).
- **This README:** the technical part, that is, which data each feature comes from, which criterion it applies and where it is in the code.

## Delivery

```
PGTA_Group_02_P2.zip
├── ASTERIXDecoder.exe                 the executable
├── code/                              this project, identical to the GitHub repository
├── report/
│   ├── Decoding_Engine_Overview.pdf   explanation of the decoding code
│   ├── Decoding_Flowchart.pdf         flowchart of the decoding code
│   ├── User_Manual.pdf                user guide
│   ├── README.md                      this same README
│   └── Planning.pdf                   project planning
└── GitHub_Link.txt                    link to the repository
```

The .ast files are not part of the delivery: they are the course files (`asterix_radar.ast`, `asterix_adsb.ast` and `asterix_combinado.ast`).

## The executable

- **Standalone:** it needs neither Python nor any other file. It is for 64-bit Windows.
- **Windows warning:** the first time, "Windows protected your PC" may appear, because the executable is not signed. Click "More info" and then "Run anyway".
- **Start-up:** it takes a few seconds to open, because it carries everything it needs inside and unpacks it when it starts.
- **Window:** the application opens maximized and adapts to the screen resolution.
- **Internet:** the simulation map needs it. Everything else works offline.

## Running from the code

Windows and Python 3 are needed; the project has been tested with Python 3.14. From this folder:

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

**Rebuilding the .exe:** double-click `crear_exe.bat`.
- It creates `.venv` if it does not exist and always installs `requirements.txt` and PyInstaller. The first time it takes a few minutes and needs internet; after that, it only checks that everything is there.
- It leaves `ASTERIXDecoder.exe` in this folder, with no `build` or `dist` folders and no `.spec` file.

**Rebuilding the manual:** double-click `crear_manual.bat`. It converts `manual/manual.html` into `manual/User_Manual.pdf` with Microsoft Edge.

**Count test:** with the environment activated, `python -m pruebas.prueba_recuentos`. It decodes the three course files (it looks for them in `../Docs.Proyecto 2/Aterix files/`) and compares the counts with the expected ones.

## Folder structure

```
main.py              entry point: the Aplicacion class, with its methods in the order of the flow
funciones/           the logic: reading, decoding, coordinates, QNH, filters, CSV and simulation
interfaz/            the window (ventana.py), the map (mapa.py) and the colours and fonts (estilo.py)
pruebas/             prueba_recuentos.py, which is not part of the application
manual/              User_Manual.pdf and its source: manual.html and capturas/
crear_exe.bat        builds ASTERIXDecoder.exe in this folder
crear_manual.bat     rebuilds manual\User_Manual.pdf
requirements.txt     libraries and versions
```

Running `crear_exe.bat` also creates `.venv/` and `ASTERIXDecoder.exe`. They are generated on each computer, so they are not in the repository.

The code (names of folders, modules, functions and variables, comments and docstrings) is in Spanish; everything the user sees is in English.

## How it works inside

### Decoding

| Step | What it does | Where |
| --- | --- | --- |
| Reading | The file is read only once. It is walked block by block (CAT and LEN); in each record the FSPEC is read (FX bit) | `funciones/lector.py` |
| CAT048 | The 14 data items required by the assignment, with one function per item; the others are skipped by adding their length. BDS 4.0, 5.0 and 6.0 inside I048/250 | `funciones/cat048.py`, `funciones/bds.py` |
| CAT021 | The 8 data items the assignment marks in green, including the BPS of the Reserved Expansion Field. From I021/040 only the GBS bit is read, for the on-ground discard; the rest is skipped by its length (FX) | `funciones/cat021.py` |
| Whole file | Joins the steps, applies the discards and computes the counts of the summary. It runs in a separate thread, with a progress bar | `funciones/decodificar.py`, `main.decodificar_en_segundo_plano` |

- **Empty file or not ASTERIX:** it is rejected with a message.
- **If opening another file fails:** the data already loaded are kept (table, filters and simulation).

### Damaged files

- **Cut file:** if it is cut in the middle of the last block, it is read up to the previous block and the summary warns about it.
- **Block of another category:** it is not an error; the whole block is skipped and reading continues with the next one.
- **Malformed record:** if the lengths of the records of a block do not match its LEN, the block is counted as "desynchronized" in the summary and reading continues with the next one.
- **Invalid LEN (less than 3):** in the first block, the file is rejected; later on, reading stops at that block, everything read so far is kept and the summary says at which byte it is. This case and the cut file are checked by `lector.problema_bloque`.
- **Limits:** ASTERIX has no synchronization marks or checksum. If a LEN is wrong, what follows cannot be recovered reliably, and a changed value inside a record of correct length cannot be detected. No heuristics that the standard does not define are used.

### Mandatory discards

These messages do not go into the table or the CSV. The summary shows how many have been discarded for each reason.

| Reason | Data | Criterion | Where |
| --- | --- | --- | --- |
| No position | I048/040 (CAT048), I021/131 (CAT021) | The message does not carry that data item. Without a position, the mandatory geographic filter cannot be applied | `decodificar.procesar_registro_048`, `cat021.decodificar_registro` |
| Outside the area | LAT and LON in WGS84 | Outside 40.9–41.7° N and 1.5–2.6° E (limits excluded) | `geo.dentro_de_zona` |
| CAT021 on ground | GBS of I021/040 | GBS = 1. It is checked before the position | `cat021.decodificar_registro` |

Messages without position in `asterix_combinado.ast`: 6,025 CAT048 and 890 CAT021. Of the 890, 333 are also on the ground and the summary counts them as "on ground", so 557 appear as "without position".

### Coordinates

- **CAT048:** the starting point is ρ and θ of I048/040 and the height, which is FL × 100 ft without correction. Without FL, h = 0 is used and `H_NO_FL` = 1.
  - The chain is the one of GeoUtils, ported to Python with the same names: `CalculateElevation` → `change_radar_spherical2radar_cartesian` → `change_radar_cartesian2geocentric` → `change_geocentric2geodesic`.
  - It uses the Barcelona radar: 41° 18' 02.5284" N, 02° 06' 07.4095" E, at 2.007 m of terrain plus 25.25 m of antenna.
  - Everything is in `geo.posicion_wgs84_048`.
- **CAT021:** LAT and LON already come in I021/131. It has no WGS84 height (I021/140 is not decoded), so `H` and `H_NO_FL` are empty in all its rows.

### Altitude correction (QNH)

- **Formula:** altitude = FL × 100 + (BP − 1013.25) × 30 ft. BP is the reference pressure sent by the aircraft: BDS 4.0 in CAT048 and BPS in CAT021.
- **When it is corrected:** only if FL × 100 < 6000 ft. With FL × 100 of 6000 ft or more, the cell is empty. Below that, the corrected altitude may go slightly above 6000.
- **Stored BP per aircraft** (by its TA, one table for CAT048 and another for CAT021):
  - The last non-standard BP sent by each aircraft is stored, at any altitude.
  - If a message carries a standard BP (1013–1013.5 hPa in CAT048; 1012.8 or 1013.6 hPa in CAT021), it is corrected with the stored BP.
  - If the aircraft has no stored BP, the cell is empty.
  - The stored BP is cleared when the aircraft climbs through 6000 ft.
- **Where:** `qnh.corregir_altitud`, and the result goes to the `ALT_CORRECTED_FT` column.

### Table and CSV

- **Columns:** always the same 82 columns, in the same order, for any file. If the message does not carry a data item, its cell is empty; for example, the CAT021 columns in a CAT048 message.
- **Rows:** one per message, in the order of the file. The table shows them in pages of 500.
- **CSV format:**
  - `;` separator and decimal comma, so that Excel with a Spanish locale opens it correctly with a double click.
  - LAT and LON with 8 decimals; H and ALT_CORRECTED_FT with 2; the rest, with their exact value.
  - TIME as hh:mm:ss,sss; text in UTF-8.
- **In the interface** the numbers use the English format (decimal point and comma as thousands separator, for example 1,478,799 or 41.43291°); the table shows the same values as the CSV, but with a decimal point. Only the CSV keeps the decimal comma.
- **Extra columns:** LAT, LON and H in WGS84, `H_NO_FL` and `ALT_CORRECTED_FT`. `H` and `H_NO_FL` are only for CAT048.
- **Where:** `funciones/exportar_csv.py`, with `COLUMNAS` and `formatear_valor`.

**Export:**
- **Export all:** saves all the decoded messages.
- **Export filtered:** saves only those left after the filters. It is enabled when a filter that leaves at least one message is applied.
- **Where it is saved:** in both options the folder and the name are chosen in the "Save CSV" dialog.
- **Separate thread:** the writing runs in a thread, with a progress bar (`main.exportar`).
- **Closing during an export:** if the window is closed while exporting, it asks first. If it is closed anyway, the incomplete CSV is deleted (`main.al_cerrar_ventana`).

**Excel:**
- If "#######" appears in a cell (it happens with TIME), the column is too narrow. It is fixed by widening it: double-click the right border of the header, or Format > AutoFit Column Width.
- When opening with a double click, Excel removes the leading zero of `MODE3A` and may read some `TA` as a number. To see them as in the application, those columns have to be imported as text.

### Filters

The conditions are ticked and "Apply filters" is clicked (or Enter in a text field). They are all combined, one after another (`filtros.aplicar_filtros`). "Clear filters" resets the panel and shows everything again.

| Filter | Data | Criterion | Where |
| --- | --- | --- | --- |
| Category | `CAT` | Keeps the messages of the chosen category (048 or 021) | `filtros.filtrar_por_categoria` |
| Remove pure targets | TYP of I048/020 (`I048_020_TYP`) | Removes the CAT048 with TYP = 0, 1, 2 or 3 (no detection, PSR, SSR or PSR+SSR): they do not come from a Mode S interrogation | `filtros.es_blanco_puro` |
| Remove fixed transponder | Mode 3/A (`MODE3A`) | Removes the messages with Mode 3/A 7777 | `filtros.es_transponder_fijo` |
| Remove aircraft on ground | STAT of I048/230 (`I048_230_STAT`) | Removes the CAT048 with STAT = 1 or 3. CAT021 on ground (GBS = 1) were already discarded when decoding | `filtros.quitar_en_tierra` |
| Only messages with FL | `FL` | Keeps the messages with a flight level | `filtros.solo_con_fl` |
| Maximum altitude | `ALT_CORRECTED_FT` or, if empty, `FL` × 100 | Keeps the messages with altitude ≤ value; those with neither are removed | `filtros.filtrar_altitud_maxima` |
| Aircraft | `TI`, `TA`, `MODE3A` | Keeps the messages in which the text appears in any of the three, case-insensitive | `filtros.buscar_aeronave` |

P3 input: Category CAT048 + Remove aircraft on ground + Only messages with FL + Maximum altitude 6000 (20,952 messages with `asterix_combinado.ast`).

### Simulation

| Feature | How it works | Where |
| --- | --- | --- |
| What is simulated | The messages left in the Data tab, with its filters, sorted by `TIME_S`. A notice above the map reminds it | `simulacion.preparar` |
| Steps | Always 1 s of time of day. Play, Pause, +1 s and Reset (back to the first time). When switching to the Data tab, the simulation pauses | `simulacion.avanzar_un_segundo`, `main.tic_reloj` |
| Speed | From x1 to x60. It only changes the wait between steps: x1, one step per second; x60, 60 per second | `main.ESPERA_POR_VELOCIDAD_MS` |
| Aircraft on the map | The pair (category, TA) or, without TA, (category, track number). The same aircraft seen by radar and by ADS-B are two symbols | `simulacion.identificador_avion` |
| Disappearance | An aircraft disappears if it spends more than 12 s without messages | `simulacion.SEGUNDOS_PARA_CADUCAR` |
| Going to another time | With "Go to time" (hh:mm and Go or Enter) or with the time bar, which goes from the first to the last time of the data and moves on its own while playing. While dragging it, the clock shows the time; the jump is made on release. The simulation is repeated second by second up to that time, without drawing or logging events, so each aircraft ends up as if it had been played up to there | `simulacion.ir_a_segundo`, `main.soltar_barra_tiempo` |
| System | Both, Radar (CAT048) or ADS-B (CAT021). It also filters the traffic lists | `mapa.sistema_visible`, `mapa.categorias_visibles` |
| Drawing | Radar in blue and ADS-B in orange. The clicked aircraft and its pair, in red. Pure targets: grey dot with their type and number ("PSR 45"). Fixed transponder: antenna. Barcelona radar: triangle with its name ("Radar BCN"). The limit of the geographic filter, in a red rectangle: outside it the messages are discarded | `interfaz/mapa.py` |
| Inside the map | Bottom left, the legend, with the same images that are drawn and the explanation of the labels; top right, the events window. Both are visible when the tab opens; clicking their title collapses them, in case they cover something on a laptop | `ventana.crear_leyenda_mapa`, `ventana.crear_ventana_eventos`, `ventana.Plegable` |
| Symbols | They point to the heading: in radar, the one of I048/200; in ADS-B, the direction in which it has moved (recomputed every 100 m, only for drawing). Without heading, they face north | `mapa.rumbo_para_dibujar` |
| Labels | Two-line data block, as on a radar display: the callsign (or the TA) and, below, the level with its trend and the ground speed (GS) in knots (I048/200 or, otherwise, BDS 5.0), for example "045↑ 210". In ADS-B there is no speed, because it is not decoded. An aircraft seen by both systems has a single label, on the radar symbol if it is on the map and, otherwise, on the ADS-B one; the other symbol has no text. Aircraft on the ground have no label (at LEBL they pile up and cover the airport), unless selected: it appears at takeoff and disappears at landing. The fixed transponder has none either: it only shows "7777" when selected. In each step only the labels of the aircraft that have changed are checked, and the text of a marker is only changed when it is different | `mapa.texto_etiqueta`, `mapa.lleva_etiqueta`, `mapa.actualizar_etiquetas_de` |
| Trails | The line with the last 15 positions of each aircraft | `mapa.dibujar_estela` |
| Follow | With a selected aircraft, the map centres on it every time it moves, without changing the zoom. The map moves as when it is dragged (`draw_move`), which is lighter than creating all the tiles again. If the aircraft disappears, following stops | `main.seguir_avion`, `mapa.centrar_en` |

**Traffic: on ground or airborne.** In the traffic (lists and events) an aircraft is its TA, whether one system or both see it. Pure targets (without TA) and the fixed transponder are not traffic, but they are still drawn on the map.

| Criterion | How it works | Where |
| --- | --- | --- |
| Radar | STAT of I048/230 (CAT048 v1.31, §5.2.23): 1 and 3, on ground; 0 and 2, airborne; 4 to 7 do not say whether it is on the ground or in the air. A message without I048/230 does not say anything either | `simulacion.estado_observado` |
| ADS-B | The messages on ground (GBS = 1) are discarded when decoding, so everything received by ADS-B is airborne | `simulacion.estado_observado` |
| Both systems | If the radar sees the aircraft with a STAT that says ground or airborne, the radar decides and the ADS-B message does not count | `simulacion.estado_observado` |
| Confirmation | A new status (also the first one) is only accepted after 2 consecutive messages that say it. A message that says nothing does not break the count; one with the previous status does. This way a flickering STAT does not give false takeoffs. While none is confirmed, the status is unknown and the aircraft does not appear in any list | `simulacion.cambiar_estado`, `simulacion.MENSAJES_PARA_CAMBIAR_ESTADO` |

**Events** (window inside the map, top right, with the most recent on top; the last 300 are kept):

| Event | When | Where |
| --- | --- | --- |
| New contact | The first time an aircraft appears, or when it comes back after having disappeared | `simulacion.actualizar_trafico` |
| Takeoff / Landing | Confirmed change from on ground to airborne / from airborne to on ground. The totals are in the title of the window | `simulacion.cambiar_estado` |
| Contact lost | The aircraft spends more than 12 s without messages from any system. Its time is the simulation time when it disappears | `simulacion.quitar_caducados` |

- Each event carries the time of the message that causes it, the callsign (or the TA) and the system (Radar or ADS-B). One click selects the aircraft and centres the map on it, if it is still in view.
- They only appear when playing or stepping 1 s. When jumping in time (Go to time, the time bar or Reset) the status is recomputed silently, the log is cleared and the totals start from zero.
- With the whole `asterix_radar.ast` there are 123 takeoffs and 83 landings, all less than 2 km from LEBL and with FL between −0.75 and 1.75 (one carries no FL): they are takeoffs and landings on the runway.

**Vertical trend and level** (`simulacion.calcular_tendencia`, `simulacion.texto_nivel`):
- **Trend:** ↑ climbing, ↓ descending, → level. In radar, with the vertical rate of BDS 6.0 (BAR or, if it does not come, IVV). If there is none, and always in ADS-B, with the change of FL between the oldest and the most recent message of the last 10 s (at least 4 s apart, one antenna turn). Threshold: ±300 ft/min (`UMBRAL_TENDENCIA_FT_MIN`).
- **Level, in air traffic control style:** "A025" if there is a QNH-corrected altitude (in hundreds of feet) and "FL045" otherwise, with the trend arrow: "FL045↑". In the map labels it goes without the prefix, to keep it short.

**Right panel**, from top to bottom:
- **Traffic:** the counters "✈ N airborne" and "▣ N on ground", each one above its list, and the figures of what is drawn on the map (radar, ADS-B and pure targets; pure targets do not count as radar and the fixed transponder is not counted).
  - Airborne: Callsign | Level | Seen by (Radar, ADS-B or Both); on ground: Callsign, because on the ground only the radar sees it (ADS-B on ground is discarded). One row per TA, in alphabetical order, and only with the systems allowed by the System selector (`simulacion.filas_trafico`).
  - Click on a row: the aircraft is selected as on the map (its radar symbol if it has one; otherwise, the ADS-B one) and the map centres on it (`main.al_pulsar_fila_trafico`).
  - To keep it smooth at x60, the lists are not rebuilt in each step: only the rows that change are added, removed or changed, and they are only re-sorted when someone enters or leaves (`ventana.ListaIncremental`). The event log works the same way: only the new ones are added (`ventana.RegistroEventos`).
- **Selected aircraft:** the data of the last message of the clicked aircraft, with its status and its trend (`mapa.texto_informacion`). With the Radar / ADS-B selector it switches to its pair in the other system (same TA); the option is greyed out if the pair is not on the map.
- **Scrolling:** the panel scrolls with the mouse wheel, like the side panel and the table of the Data tab (`ventana.Desplazador`). Over a list with hidden rows, the list scrolls.

**Performance:** with `asterix_combinado.ast` at x60, a step (logic, map and panels) takes 2.6 ms on average and the 60 steps per second are kept.

**Map:** it uses the OpenStreetMap tiles. Its [usage policy](https://operations.osmfoundation.org/policies/tiles/) blocks the generic identification of tkintermapview, so `interfaz/mapa.py` requests the tiles with its own User-Agent. The attribution is shown, only the visible tiles are downloaded and they are not stored for offline use.

**Dark map:** each tile, when downloaded, is turned grey, inverted and tinted night blue (`mapa.oscurecer_tesela`); it is stored already darkened, so this is done only once and the simulation runs just as smoothly. The "Map: Dark | Light" selector switches between this map and the original one and requests the tiles again. At start-up, the map is the light one.

### Appearance

Dark control-room theme, with all the colours in `interfaz/estilo.py`: night-blue background, slightly lighter cards, a single accent colour (cyan) for the main actions, and radar and ADS-B in blue and orange, as always. customtkinter runs in dark mode; the tables (ttk) and the Windows title bar are darkened by hand (`ventana.configurar_estilo_tabla`, `ventana.poner_barra_titulo_oscura`). All texts have a WCAG contrast of at least 4.5:1 on their background.

## In which order to read the code

1. `main.py`: the application. The methods follow the order of the flow: choose file → decode → show → filter → export → simulate.
2. `funciones/decodificar.py`: decodes a whole file and applies the discards.
3. `funciones/lector.py`: blocks, FSPEC and bit functions.
4. `funciones/cat048.py` and `funciones/bds.py`: the CAT048 data items and BDS 4.0, 5.0 and 6.0.
5. `funciones/cat021.py`: the CAT021 data items, the GBS bit of I021/040 and the BPS of the Reserved Expansion Field.
6. `funciones/geo.py`: port of GeoUtils.cs (radar → WGS84 and stereographic projection for P3).
7. `funciones/qnh.py`: altitude correction with the QNH below 6000 ft.
8. `funciones/exportar_csv.py`: columns and format of the CSV.
9. `funciones/filtros.py`: one filter per function.
10. `funciones/simulacion.py` and `interfaz/mapa.py`: logic of the simulation and what is drawn on the map.
11. `interfaz/ventana.py` and `interfaz/estilo.py`: construction of the window, colours and fonts.

## Applied criteria

Each constant is in the module that uses it, with a comment that explains the criterion.

| Criterion | Reason |
| --- | --- |
| Standard pressure: 1013–1013.5 hPa in CAT048; 1012.8 and 1013.6 hPa in CAT021 | The range is the one of the assignment. In ADS-B the BPS goes in steps of 0.8 hPa and never falls in 1013–1013.5: 1012.8 and 1013.6 are its standard pressure (`qnh.py`) |
| The 6000 ft threshold is compared with FL × 100 without correction | It has to be decided whether to correct before having the corrected altitude (`qnh.UMBRAL_QNH_FT`) |
| Below 6000 ft, without any stored non-standard BP: empty corrected altitude | Without a QNH from the aircraft there is nothing to correct with |
| At 6000 ft or more: empty corrected altitude | Above the transition altitude no correction is made; the column is only filled when there is a corrected altitude |
| The stored BP is cleared when climbing through 6000 ft; a non-standard BP is stored at any altitude | When passing the transition altitude the aircraft sets the standard pressure; a non-standard BP is always the QNH it has set |
| An FL with V = 1 or G = 1 is corrected the same way | The assignment does not exclude them; V and G stay in their CSV columns |
| CAT048 is transformed to WGS84 with the uncorrected FL | It is the height given by the radar; the corrected altitude only exists below 6000 ft |
| CAT048 without FL: transformed with height 0 and `H_NO_FL` = 1 | The transformation needs a height; `H_NO_FL` marks that H does not come from an FL (`decodificar.ALTURA_SI_NO_HAY_FL_M`) |
| CAT021 has no WGS84 height: `H` and `H_NO_FL` empty | I021/140 (Geometric Height) is not decoded; LAT and LON already come in I021/131 |
| Messages without position are discarded: 6,025 CAT048 and 890 CAT021 in `asterix_combinado.ast` | Without a position, the mandatory geographic filter cannot be applied |
| A single CSV for the combined file, with the CAT column | All the CSVs have the same columns; CAT gives the category of each row |
| From I021/040 only the GBS bit is read | In CAT021 the assignment asks for the data items in green, and I021/040 is not; the GBS is needed to discard the aircraft on ground |
| TYP = 0 (no detection) is a pure target | Like PSR, SSR and PSR+SSR, it does not come from a Mode S interrogation (`filtros.TIPOS_BLANCO_PURO`) |
| Fixed transponder: only Mode 3/A 7777 | It is the code of the reference transponder on the ground (`filtros.MODO_3A_TRANSPONDER_FIJO`). The `I048_020_RAB` column stays in the CSV because it is a subfield of I048/020, which is decoded |
