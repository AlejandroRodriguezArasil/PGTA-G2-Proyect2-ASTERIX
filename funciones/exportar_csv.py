"""
Las 82 columnas del CSV, cómo se guarda cada fila en memoria (una tupla) y la exportación.
El CSV va con ";" de separador y coma decimal; celda vacía si el mensaje no trae el dato.
"""

import csv

SEPARADOR_CSV = ";"

# En el mismo orden que salen en el CSV
COLUMNAS = [
    # --- Comunes a CAT048 y CAT021 ---
    "CAT",
    "SAC", "SIC",                       # I048/010 - I021/010
    "TIME", "TIME_S",                   # I048/140 - I021/073
    "LAT", "LON",                       # calculadas en CAT048, de I021/131 en CAT021
    "H",                                # altura WGS84, solo CAT048
    "H_NO_FL",                         # 1 si no había FL y H se calculó con altura 0
    "TA",                               # I048/220 - I021/080
    "TI",                               # I048/240 - I021/170
    "MODE3A",                           # I048/070 - I021/070
    "FL",                               # I048/090 - I021/145
    "BP",                               # BDS 4.0 (I048/250) - BPS del RE de CAT021
    "ALT_CORRECTED_FT",                 # sale de qnh.py

    # --- CAT048: I048/020 Target Report Descriptor ---
    "I048_020_TYP", "I048_020_SIM", "I048_020_RDP", "I048_020_SPI", "I048_020_RAB",
    "I048_020_TST", "I048_020_ERR", "I048_020_XPP", "I048_020_ME", "I048_020_MI",
    "I048_020_FOE_FRI",
    "I048_020_ADSB_EP", "I048_020_ADSB_VAL", "I048_020_SCN_EP", "I048_020_SCN_VAL",
    "I048_020_PAI_EP", "I048_020_PAI_VAL",

    # --- CAT048: I048/040, I048/070 e I048/090 ---
    "I048_040_RHO_NM", "I048_040_THETA_DEG",
    "I048_070_V", "I048_070_G", "I048_070_L",
    "I048_090_V", "I048_090_G",

    # --- CAT048: I048/130 Radar Plot Characteristics ---
    "I048_130_SRL", "I048_130_SRR", "I048_130_SAM", "I048_130_PRL",
    "I048_130_PAM", "I048_130_RPD", "I048_130_APD",

    # --- CAT048: I048/250 BDS 4.0, 5.0 y 6.0 (el BP está arriba) ---
    "BDS40_MCP_ALT", "BDS40_FMS_ALT", "BDS40_VNAV", "BDS40_ALT_HOLD",
    "BDS40_APPROACH", "BDS40_ALT_SOURCE",
    "BDS50_RA", "BDS50_TTA", "BDS50_GS", "BDS50_TAR", "BDS50_TAS",
    "BDS60_HDG", "BDS60_IAS", "BDS60_MACH", "BDS60_BAR", "BDS60_IVV",

    # --- CAT048: I048/161, I048/200, I048/170 e I048/230 ---
    "I048_161_TRACK_NUMBER",
    "I048_200_GS_KT", "I048_200_HDG_DEG",
    "I048_170_CNF", "I048_170_RAD", "I048_170_DOU", "I048_170_MAH", "I048_170_CDM",
    "I048_170_TRE", "I048_170_GHO", "I048_170_SUP", "I048_170_TCC",
    "I048_230_COM", "I048_230_STAT", "I048_230_SI", "I048_230_MSSC",
    "I048_230_ARC", "I048_230_AIC", "I048_230_B1A", "I048_230_B1B",
]

# Lo calculado se redondea a estos decimales; lo decodificado se escribe tal cual.
DECIMALES_FIJOS = {
    "LAT": 8,
    "LON": 8,
    "H": 2,
    "ALT_CORRECTED_FT": 2,
}


def formatear_valor(columna, valor):
    """Texto de la celda: vacío si no hay dato, y con coma decimal."""
    if valor is None:
        return ""
    if isinstance(valor, float):
        if columna in DECIMALES_FIJOS:
            decimales = DECIMALES_FIJOS[columna]
            redondeado = round(valor, decimales)
            if redondeado == 0:
                redondeado = 0.0    # si no, -0,0001 sale como "-0,00"
            texto = format(redondeado, "." + str(decimales) + "f")
        else:
            texto = repr(valor)    # con todas las cifras
        return texto.replace(".", ",")
    return str(valor)


# -----------------------------------------------------------------------------
# Filas en memoria
# -----------------------------------------------------------------------------
# Cada mensaje se guarda como tupla en el orden de COLUMNAS (gasta menos RAM que un
# diccionario). Para leer un valor: valor(fila, "FL").

# "CAT" -> 0, "SAC" -> 1, ...
INDICE_COLUMNA = {}
for posicion_columna in range(len(COLUMNAS)):
    INDICE_COLUMNA[COLUMNAS[posicion_columna]] = posicion_columna

PASO_PROGRESO = 1           # aviso de progreso cada 1 %


def fila_a_tupla(fila_diccionario):
    """Pasa el diccionario de un mensaje a tupla."""
    valores = []
    for columna in COLUMNAS:
        valores.append(fila_diccionario.get(columna))
    return tuple(valores)


def valor(fila, columna):
    """Valor de una columna de la fila (None si no hay dato)."""
    return fila[INDICE_COLUMNA[columna]]


def formatear_fila(fila):
    """Celdas de una fila ya en texto; sirve para el CSV y para la tabla."""
    celdas = []
    for posicion in range(len(COLUMNAS)):
        celdas.append(formatear_valor(COLUMNAS[posicion], fila[posicion]))
    return celdas


# -----------------------------------------------------------------------------
# Exportar
# -----------------------------------------------------------------------------

def exportar(ruta, filas, informar_progreso=None):
    """Escribe el CSV. Si se pasa informar_progreso, se le va llamando con el % hecho."""
    total = len(filas)
    siguiente_aviso = 0
    with open(ruta, "w", newline="", encoding="utf-8") as fichero:
        escritor = csv.writer(fichero, delimiter=SEPARADOR_CSV)
        escritor.writerow(COLUMNAS)
        for numero_fila in range(total):
            escritor.writerow(formatear_fila(filas[numero_fila]))
            if informar_progreso is not None:
                porcentaje = numero_fila * 100 // total
                if porcentaje >= siguiente_aviso:
                    informar_progreso(porcentaje)
                    siguiente_aviso = porcentaje + PASO_PROGRESO
    if informar_progreso is not None:
        informar_progreso(100)
