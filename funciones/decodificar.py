"""
decodificar.py

Motor de decodificación: une los pasos del flujo para un fichero completo.
    lectura -> decodificación -> coordenadas -> QNH -> (filas en memoria)
    (lector)  (cat048/cat021)   (geo)         (qnh)

Lo usa main.py (la aplicación). Para cada bloque del fichero lee sus registros,
los decodifica según su categoría, aplica los descartes obligatorios y calcula
las columnas extra (posición WGS84 y altitud corregida). Cada registro que se
queda produce una fila (diccionario columna -> valor), y decodificar_fichero la
guarda en la lista que devuelve, ya como tupla (ver exportar_csv.py).

Descartes obligatorios (no entran en la tabla ni en el CSV):
    - CAT048 y CAT021 fuera de 40,9-41,7° N y 1,5-2,6° E (filtro geográfico del enunciado)
    - CAT021 con GBS = 1, en tierra
    - mensajes sin posición: sin ella no se puede aplicar el filtro geográfico obligatorio
"""

import time

from funciones import lector
from funciones import cat048
from funciones import cat021
from funciones import geo
from funciones import qnh
from funciones import exportar_csv

CATEGORIA_048 = 48
CATEGORIA_021 = 21
PIES_POR_FL = 100
PASO_PROGRESO = 1           # se informa del progreso cada 1 %

# CAT048 sin FL: no se conoce la altura del blanco, y la transformación necesita una.
# Se usa 0 m y la columna H_NO_FL lo marca con un 1.
ALTURA_SI_NO_HAY_FL_M = 0.0

def crear_recuentos():
    """Contadores que se muestran en el resumen final."""
    return {
        "registros_048": 0,
        "registros_021": 0,
        "descartados_048_sin_posicion": 0,
        "descartados_048_fuera_de_zona": 0,
        "descartados_021_en_tierra": 0,
        "descartados_021_sin_posicion": 0,
        "descartados_021_fuera_de_zona": 0,
        "filas_048": 0,
        "filas_048_sin_fl": 0,
        "filas_021": 0,
        "bloques_desincronizados": 0,
        "lectura_parada": "",       # si se para antes del final: lector.BLOQUE_CORTADO o lector.LEN_NO_VALIDO
        "octeto_parada": 0,         # octeto donde empieza el bloque en el que se ha parado
        "segundos": 0.0,
    }


def procesar_registro_048(datos, posicion, lista_frn, estado_qnh, recuentos):
    """
    Decodifica un registro CAT048 y calcula sus columnas extra.
    Devuelve (fila, posicion_siguiente); fila es None si el mensaje se descarta.
    """
    fila, posicion = cat048.decodificar_registro(datos, posicion, lista_frn)

    # Sin I048/040 no hay posición ni, por tanto, filtro geográfico: se descarta
    if "I048_040_RHO_NM" not in fila:
        recuentos["descartados_048_sin_posicion"] += 1
        return None, posicion

    # Altura para la transformación: FL x 100 ft sin corregir, el dato que da el radar
    # (la altitud corregida solo existe por debajo de 6000 ft). Sin FL, ALTURA_SI_NO_HAY_FL_M.
    if "FL" in fila:
        altura_m = fila["FL"] * PIES_POR_FL * geo.GeoUtils.FEET2METERS
        fila["H_NO_FL"] = 0
    else:
        altura_m = ALTURA_SI_NO_HAY_FL_M
        fila["H_NO_FL"] = 1

    latitud, longitud, altura_wgs84 = geo.posicion_wgs84_048(fila["I048_040_RHO_NM"],
                                                            fila["I048_040_THETA_DEG"],
                                                            altura_m)

    # Filtro geográfico del enunciado
    if not geo.dentro_de_zona(latitud, longitud):
        recuentos["descartados_048_fuera_de_zona"] += 1
        return None, posicion

    fila["LAT"] = latitud
    fila["LON"] = longitud
    fila["H"] = altura_wgs84

    # Corrección QNH, solo con los mensajes que se quedan
    fila["ALT_CORRECTED_FT"] = qnh.corregir_altitud(estado_qnh, fila.get("TA"), fila.get("FL"),
                                                    fila.get("BP"), CATEGORIA_048)
    return fila, posicion


def procesar_registro_021(datos, posicion, lista_frn, estado_qnh, recuentos):
    """
    Decodifica un registro CAT021 y calcula su altitud corregida.
    Devuelve (fila, posicion_siguiente); fila es None si el mensaje se descarta.
    LAT y LON vienen ya en WGS84 (I021/131). CAT021 no tiene altura WGS84: no se decodifica
    I021/140 (Geometric Height), así que H y H_NO_FL quedan vacías.
    """
    fila, posicion, motivo = cat021.decodificar_registro(datos, posicion, lista_frn)

    # Los descartes de CAT021 se hacen dentro de cat021.py (en tierra, sin posición, fuera de zona)
    if fila is None:
        recuentos["descartados_021_" + motivo] += 1
        return None, posicion

    # Corrección QNH, solo con los mensajes que se quedan
    fila["ALT_CORRECTED_FT"] = qnh.corregir_altitud(estado_qnh, fila.get("TA"), fila.get("FL"),
                                                    fila.get("BP"), CATEGORIA_021)
    return fila, posicion


def decodificar_bloque(datos, inicio_bloque, longitud_bloque, categoria, estados_qnh, recuentos):
    """
    Decodifica todos los registros de un bloque y devuelve la lista de filas que se quedan.
    Un bloque puede tener varios registros: se leen uno detrás de otro hasta llegar al LEN.
    Cada registro debe acabar dentro del bloque y el último justo en el LEN; si no, el
    bloque está desincronizado: se cuenta y se sigue con el bloque siguiente.
    """
    filas = []
    fin_bloque = inicio_bloque + longitud_bloque
    posicion = inicio_bloque + lector.LONGITUD_CABECERA_BLOQUE

    try:
        while posicion < fin_bloque:
            lista_frn, posicion = lector.leer_fspec(datos, posicion)

            if categoria == CATEGORIA_048:
                recuentos["registros_048"] += 1
                fila, posicion = procesar_registro_048(datos, posicion, lista_frn,
                                                       estados_qnh[CATEGORIA_048], recuentos)
            else:
                recuentos["registros_021"] += 1
                fila, posicion = procesar_registro_021(datos, posicion, lista_frn,
                                                       estados_qnh[CATEGORIA_021], recuentos)

            if posicion > fin_bloque:
                # El registro se sale del bloque: alguna longitud no cuadra
                recuentos["bloques_desincronizados"] += 1
                return filas

            if fila is not None:
                filas.append(fila)

    except (IndexError, ValueError):
        # Un DI se sale de los datos o el FSPEC indica un FRN que no existe
        recuentos["bloques_desincronizados"] += 1

    return filas


def decodificar_fichero(ruta_ast, informar_progreso=None):
    """
    Decodifica un fichero ASTERIX completo una sola vez y devuelve (filas, recuentos):
        filas:     lista de tuplas, una por mensaje que se queda, en el orden del fichero
        recuentos: diccionario con los contadores del resumen
    informar_progreso, si se da, es una función que recibe el porcentaje del fichero leído (0-100)
    y los registros leídos hasta ahora. La ventana la usa para mover la barra de progreso.
    Lanza ValueError si el fichero no es ASTERIX. Si se corta en mitad del último bloque o un bloque
    tiene un LEN no válido, lee hasta el bloque anterior y lo indica en recuentos["lectura_parada"]
    (el motivo) y recuentos["octeto_parada"] (dónde).
    """
    instante_inicio = time.time()

    datos = lector.leer_fichero(ruta_ast)
    if len(datos) == 0:
        raise ValueError("the file is empty")

    filas = []
    recuentos = crear_recuentos()
    estados_qnh = {CATEGORIA_048: qnh.crear_estado(), CATEGORIA_021: qnh.crear_estado()}

    posicion = 0
    siguiente_aviso = 0
    while posicion < len(datos):
        # Bloque que no se puede leer (fichero cortado o LEN no válido): se para aquí, se queda todo
        # lo leído y el resumen lo avisa. Si es el primero, no es un fichero ASTERIX y
        # leer_cabecera_bloque lo rechaza.
        problema = lector.problema_bloque(datos, posicion)
        if posicion > 0 and problema != "":
            recuentos["lectura_parada"] = problema
            recuentos["octeto_parada"] = posicion
            break
        categoria, longitud_bloque = lector.leer_cabecera_bloque(datos, posicion)

        # Un bloque de otra categoría no es un error: se salta entero
        if categoria == CATEGORIA_048 or categoria == CATEGORIA_021:
            filas_bloque = decodificar_bloque(datos, posicion, longitud_bloque, categoria,
                                              estados_qnh, recuentos)
            for fila in filas_bloque:
                if fila["CAT"] == CATEGORIA_048:
                    recuentos["filas_048"] += 1
                    if fila["H_NO_FL"] == 1:
                        recuentos["filas_048_sin_fl"] += 1
                else:
                    recuentos["filas_021"] += 1
                filas.append(exportar_csv.fila_a_tupla(fila))

        posicion = posicion + longitud_bloque

        if informar_progreso is not None:
            porcentaje = posicion * 100 // len(datos)
            if porcentaje >= siguiente_aviso:
                registros_leidos = recuentos["registros_048"] + recuentos["registros_021"]
                informar_progreso(porcentaje, registros_leidos)
                siguiente_aviso = porcentaje + PASO_PROGRESO

    if recuentos["registros_048"] + recuentos["registros_021"] == 0:
        raise ValueError("it contains no CAT048 or CAT021 records")

    recuentos["segundos"] = time.time() - instante_inicio
    return filas, recuentos
