"""
Motor de decodificación: recorre el fichero, decodifica cada registro y le añade posición y altitud corregida.
Se descartan los que están fuera de 40,9-41,7° N y 1,5-2,6° E, los CAT021 en tierra (GBS = 1)
y los que no tienen posición.
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
PASO_PROGRESO = 1           # en %

# CAT048 sin FL: la transformación necesita una altura, así que se pone 0 m y se marca H_NO_FL = 1
ALTURA_SI_NO_HAY_FL_M = 0.0

def crear_recuentos():
    """Contadores para el resumen final."""
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
        "lectura_parada": "",       # por qué se ha parado antes del final, si pasa
        "octeto_parada": 0,         # dónde empieza el bloque en el que se ha parado
        "segundos": 0.0,
    }


def procesar_registro_048(datos, posicion, lista_frn, estado_qnh, recuentos):
    """
    Decodifica un registro CAT048 y le añade LAT, LON, H y la altitud corregida.
    Devuelve (fila, posicion_siguiente), con fila = None si se descarta.
    """
    fila, posicion = cat048.decodificar_registro(datos, posicion, lista_frn)

    # sin I048/040 no hay posición y no se puede aplicar el filtro geográfico
    if "I048_040_RHO_NM" not in fila:
        recuentos["descartados_048_sin_posicion"] += 1
        return None, posicion

    # Para la transformación se usa el FL sin corregir (la altitud corregida
    # solo existe por debajo de 6000 ft)
    if "FL" in fila:
        altura_m = fila["FL"] * PIES_POR_FL * geo.GeoUtils.FEET2METERS
        fila["H_NO_FL"] = 0
    else:
        altura_m = ALTURA_SI_NO_HAY_FL_M
        fila["H_NO_FL"] = 1

    latitud, longitud, altura_wgs84 = geo.posicion_wgs84_048(fila["I048_040_RHO_NM"],
                                                            fila["I048_040_THETA_DEG"],
                                                            altura_m)

    if not geo.dentro_de_zona(latitud, longitud):
        recuentos["descartados_048_fuera_de_zona"] += 1
        return None, posicion

    fila["LAT"] = latitud
    fila["LON"] = longitud
    fila["H"] = altura_wgs84

    # el QNH solo se aplica a los que se quedan
    fila["ALT_CORRECTED_FT"] = qnh.corregir_altitud(estado_qnh, fila.get("TA"), fila.get("FL"),
                                                    fila.get("BP"), CATEGORIA_048)
    return fila, posicion


def procesar_registro_021(datos, posicion, lista_frn, estado_qnh, recuentos):
    """
    Igual que el de CAT048 pero solo hace falta la altitud corregida: LAT y LON ya vienen en WGS84.
    H y H_NO_FL se quedan vacías porque I021/140 no se decodifica.
    """
    fila, posicion, motivo = cat021.decodificar_registro(datos, posicion, lista_frn)

    # en CAT021 los descartes ya se hacen dentro de cat021.py
    if fila is None:
        recuentos["descartados_021_" + motivo] += 1
        return None, posicion

    # corrección QNH
    fila["ALT_CORRECTED_FT"] = qnh.corregir_altitud(estado_qnh, fila.get("TA"), fila.get("FL"),
                                                    fila.get("BP"), CATEGORIA_021)
    return fila, posicion


def decodificar_bloque(datos, inicio_bloque, longitud_bloque, categoria, estados_qnh, recuentos):
    """
    Decodifica los registros de un bloque y devuelve las filas que se quedan.
    Si un registro se pasa del LEN el bloque está desincronizado: se cuenta y se deja ahí.
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
                # se ha salido del bloque, alguna longitud no cuadra
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
    Decodifica el fichero entero y devuelve (filas, recuentos), con las filas ya como tuplas.
    informar_progreso(porcentaje, registros_leidos) es opcional; la ventana lo usa para la barra.
    Si el fichero se corta o un LEN está mal, se queda con lo leído hasta ahí y lo apunta en recuentos.
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
        # Si un bloque no se puede leer se para aquí y se guarda lo que haya. Si es el
        # primero, leer_cabecera_bloque lanza el error (no es un fichero ASTERIX)
        problema = lector.problema_bloque(datos, posicion)
        if posicion > 0 and problema != "":
            recuentos["lectura_parada"] = problema
            recuentos["octeto_parada"] = posicion
            break
        categoria, longitud_bloque = lector.leer_cabecera_bloque(datos, posicion)

        # los bloques de otras categorías se saltan enteros
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
