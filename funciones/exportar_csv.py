"""
exportar_csv.py

Paso 5 del flujo: CSV.
    lectura -> decodificación -> coordenadas -> QNH -> CSV

Define las 97 columnas, cómo se guarda una fila en memoria (una tupla con un
valor por columna) y cómo se escribe el CSV con el formato pedido en la D9:
    - delimitador punto y coma (;) y separador decimal coma (,)
    - una columna por subcampo y una fila por mensaje, en el orden del fichero
    - celda vacía cuando el mensaje no trae ese dato

Todos los CSV tienen las mismas columnas, sea cual sea el fichero (duda 11).
"""

import csv

SEPARADOR_CSV = ";"

# Columnas en el orden en que aparecen en el CSV.
COLUMNAS = [
    # --- Comunes a CAT048 y CAT021 ---
    "CAT",
    "SAC", "SIC",                       # I048/010 - I021/010
    "TIME", "TIME_S",                   # I048/140 - I021/073
    "LAT", "LON", "H",                  # WGS84: calculada (CAT048) o I021/131 + FL (CAT021)
    "H_SIN_FL",                         # 1 si no había FL para calcular H (dudas 8 y 9)
    "TA",                               # I048/220 - I021/080
    "TI",                               # I048/240 - I021/170
    "MODE3A",                           # I048/070 - I021/070
    "FL",                               # I048/090 - I021/145
    "BP",                               # BDS 4.0 de I048/250 - BPS del RE de CAT021
    "ALT_CORREGIDA_FT",                 # corrección QNH (D14)

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

    # --- CAT048: I048/250 BDS 4.0, 5.0 y 6.0 (el BP va en la columna común) ---
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

    # --- CAT021: I021/040 Target Report Descriptor ---
    "I021_040_ATP", "I021_040_ARC", "I021_040_RC", "I021_040_RAB",
    "I021_040_DCR", "I021_040_GBS", "I021_040_SIM", "I021_040_TST",
    "I021_040_SAA", "I021_040_CL",
    "I021_040_IPC", "I021_040_NOGO", "I021_040_CPR", "I021_040_LDPJ", "I021_040_RCF",
]

# Valores calculados: se escriben con un número fijo de decimales.
# Los valores decodificados se escriben exactos, sin redondear.
DECIMALES_FIJOS = {
    "LAT": 8,
    "LON": 8,
    "H": 2,
    "ALT_CORREGIDA_FT": 2,
}


def formatear_valor(columna, valor):
    """Convierte un valor al texto de su celda: vacío si no hay dato y coma decimal."""
    if valor is None:
        return ""
    if isinstance(valor, float):
        if columna in DECIMALES_FIJOS:
            decimales = DECIMALES_FIJOS[columna]
            redondeado = round(valor, decimales)
            if redondeado == 0:
                redondeado = 0.0    # evita que se escriba "-0,00" con valores como -0,0001
            texto = format(redondeado, "." + str(decimales) + "f")
        else:
            texto = repr(valor)    # valor exacto, con todas sus cifras
        return texto.replace(".", ",")
    return str(valor)


# -----------------------------------------------------------------------------
# Cómo se guarda una fila en memoria
# -----------------------------------------------------------------------------
# Al decodificar, cada mensaje es un diccionario (columna -> valor). Para guardarlo se
# pasa a una tupla con los 97 valores en el orden de COLUMNAS (None si no hay dato),
# que ocupa menos RAM que el diccionario (R13). Un valor se lee con valor(fila, "FL").

# Posición de cada columna dentro de la tupla: "CAT" -> 0, "SAC" -> 1, ...
INDICE_COLUMNA = {}
for posicion_columna in range(len(COLUMNAS)):
    INDICE_COLUMNA[COLUMNAS[posicion_columna]] = posicion_columna

PASO_PROGRESO = 1           # se informa del progreso de la exportación cada 1 %


def fila_a_tupla(fila_diccionario):
    """Convierte una fila decodificada (diccionario) en la tupla que se guarda en memoria."""
    valores = []
    for columna in COLUMNAS:
        valores.append(fila_diccionario.get(columna))
    return tuple(valores)


def valor(fila, columna):
    """Devuelve el valor de una columna de una fila guardada (None si no hay dato)."""
    return fila[INDICE_COLUMNA[columna]]


def formatear_fila(fila):
    """Devuelve la lista de textos de las celdas de una fila (CSV y tabla de la ventana)."""
    celdas = []
    for posicion in range(len(COLUMNAS)):
        celdas.append(formatear_valor(COLUMNAS[posicion], fila[posicion]))
    return celdas


# -----------------------------------------------------------------------------
# Exportar (R18, R35 y R38)
# -----------------------------------------------------------------------------

def exportar(ruta, filas, informar_progreso=None):
    """
    Escribe en 'ruta' un CSV con la cabecera y todas las filas de la lista, en su orden.
    informar_progreso, si se da, es una función que recibe el porcentaje (0-100).
    """
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
