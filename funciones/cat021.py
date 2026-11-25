"""
Decodificación de CAT021 (ADS-B, v2.1): los 8 DI en verde del enunciado.
De I021/040 solo se lee el GBS, para quitar los que están en tierra.
Primero se localizan los DI y solo se decodifica todo si el mensaje no se descarta, que va bastante más rápido.
"""

from funciones.lector import leer_entero, con_signo, longitud_fx, decodificar_caracteres_6_bits, formatear_hora
from funciones import geo

# LSB de CAT021 v2.1
LSB_TIEMPO_S = 1 / 128                  # I021/073: 1/128 s
LSB_LATITUD_LONGITUD_DEG = 180 / 2 ** 30   # I021/131: 180/2^30 grados
LSB_FL = 0.25                           # I021/145: 1/4 FL
LSB_PRESION_HPA = 0.1                   # RE, BPS: 0,1 hPa
PRESION_BASE_HPA = 800                  # RE, BPS: el campo es "BP menos 800 hPa"

# Motivos de descarte, decodificar.py los cuenta para el resumen
MOTIVO_EN_TIERRA = "en_tierra"
MOTIVO_SIN_POSICION = "sin_posicion"
MOTIVO_FUERA_DE_ZONA = "fuera_de_zona"

# FRN de los DI que se usan
FRN_I021_010 = 1
FRN_I021_040 = 2
FRN_I021_131 = 7
FRN_I021_080 = 11
FRN_I021_073 = 12
FRN_I021_070 = 19
FRN_I021_145 = 21
FRN_I021_170 = 29
FRN_RE = 48


# =============================================================================
# DI que se decodifican
# =============================================================================

def decode_i021_010(datos, posicion, fila):
    """I021/010: SAC y SIC."""
    fila["SAC"] = datos[posicion]          # bits 16-9
    fila["SIC"] = datos[posicion + 1]      # bits 8-1


def leer_gbs_i021_040(datos, posicion):
    """
    Devuelve el bit GBS de I021/040 (1 = en tierra), el bit 7 de la primera extensión.
    Si la extensión no viene es que todos sus bits son 0, así que GBS = 0.
    """
    if longitud_fx(datos, posicion) < 2:
        return 0
    return (datos[posicion + 1] >> 6) & 0x01


def decode_i021_131(datos, posicion, fila):
    """Posición WGS-84 de alta resolución (I021/131): LAT y LON en grados."""
    # bits 64-33: latitud en complemento a dos, LSB 180/2^30 grados
    latitud = con_signo(leer_entero(datos, posicion, 4), 32)
    # bits 32-1: longitud, igual
    longitud = con_signo(leer_entero(datos, posicion + 4, 4), 32)
    fila["LAT"] = latitud * LSB_LATITUD_LONGITUD_DEG
    fila["LON"] = longitud * LSB_LATITUD_LONGITUD_DEG


def decode_i021_080(datos, posicion, fila):
    """I021/080 Target Address, en hexadecimal."""
    direccion_modo_s = leer_entero(datos, posicion, 3)   # bits 24-1
    fila["TA"] = format(direccion_modo_s, "06X")


def decode_i021_073(datos, posicion, fila):
    """Hora de recepción de la posición (I021/073)."""
    # bits 24-1: segundos desde medianoche, LSB 1/128 s
    segundos = leer_entero(datos, posicion, 3) * LSB_TIEMPO_S
    fila["TIME_S"] = segundos
    fila["TIME"] = formatear_hora(segundos)


def decode_i021_070(datos, posicion, fila):
    """Modo 3/A (I021/070) en octal."""
    valor = leer_entero(datos, posicion, 2)
    codigo = valor & 0x0FFF                    # bits 12-1 (16-13 son spare)
    fila["MODE3A"] = format(codigo, "04o")


def decode_i021_145(datos, posicion, fila):
    """I021/145 Flight Level, sin corregir por QNH."""
    # complemento a dos, LSB 1/4 FL
    nivel_vuelo = con_signo(leer_entero(datos, posicion, 2), 16)
    fila["FL"] = nivel_vuelo * LSB_FL


def decode_i021_170(datos, posicion, fila):
    """I021/170: callsign, con la misma tabla de 6 bits que I048/240."""
    fila["TI"] = decodificar_caracteres_6_bits(datos, posicion)


def decode_i021_re(datos, posicion, fila):
    """
    Reserved Expansion Field. Solo se lee el BPS (bit 8 del Items Indicator, el 2º octeto);
    si viene, es el primer subcampo.
    """
    indicador_items = datos[posicion + 1]
    if indicador_items & 0x80:
        # bits 12-1 = presión menos 800 hPa, LSB 0,1 hPa (16-13 son spare).
        # Se redondea a 1 decimal para quitar los restos de coma flotante
        valor = leer_entero(datos, posicion + 2, 2) & 0x0FFF
        fila["BP"] = round(PRESION_BASE_HPA + valor * LSB_PRESION_HPA, 1)


# =============================================================================
# Longitud de cada DI (para localizarlos y saltar los que no se usan)
# =============================================================================

# FRN -> octetos de los DI de longitud fija
LONGITUD_FIJA_021 = {
    1: 2,     # I021/010 Data Source Identification
    3: 2,     # I021/161 Track Number
    4: 1,     # I021/015 Service Identification
    5: 3,     # I021/071 Time of Applicability for Position
    6: 6,     # I021/130 Position in WGS-84 co-ordinates
    7: 8,     # I021/131 Position in WGS-84 co-ordinates, high res.
    8: 3,     # I021/072 Time of Applicability for Velocity
    9: 2,     # I021/150 Air Speed
    10: 2,    # I021/151 True Air Speed
    11: 3,    # I021/080 Target Address
    12: 3,    # I021/073 Time of Message Reception of Position
    13: 4,    # I021/074 Time of Message Reception of Position - High Precision
    14: 3,    # I021/075 Time of Message Reception of Velocity
    15: 4,    # I021/076 Time of Message Reception of Velocity - High Precision
    16: 2,    # I021/140 Geometric Height
    18: 1,    # I021/210 MOPS Version
    19: 2,    # I021/070 Mode 3/A Code
    20: 2,    # I021/230 Roll Angle
    21: 2,    # I021/145 Flight Level
    22: 2,    # I021/152 Magnetic Heading
    23: 1,    # I021/200 Target Status
    24: 2,    # I021/155 Barometric Vertical Rate
    25: 2,    # I021/157 Geometric Vertical Rate
    26: 4,    # I021/160 Airborne Ground Vector
    27: 2,    # I021/165 Track Angle Rate
    28: 3,    # I021/077 Time of Report Transmission
    29: 6,    # I021/170 Target Identification
    30: 1,    # I021/020 Emitter Category
    32: 2,    # I021/146 Selected Altitude
    33: 2,    # I021/148 Final State Selected Altitude
    35: 1,    # I021/016 Service Management
    36: 1,    # I021/008 Aircraft Operational Status
    38: 1,    # I021/132 Message Amplitude
    40: 7,    # I021/260 ACAS Resolution Advisory Report
    41: 1,    # I021/400 Receiver ID
}

FRN_I021_090 = 17    # Quality Indicators: longitud variable con FX
FRN_I021_220 = 31    # Met Information: compuesto
FRN_I021_110 = 34    # Trajectory Intent: compuesto
FRN_I021_271 = 37    # Surface Capabilities and Characteristics: caso especial
FRN_I021_250 = 39    # Mode S MB Data: repetitivo
FRN_I021_295 = 42    # Data Ages: compuesto
FRN_SP = 49          # Special Purpose Field: longitud explícita


def longitud_i021_220(datos, posicion):
    """Longitud de I021/220 Met Information: WS, WD y TMP son 2 octetos y TRB 1."""
    primario = datos[posicion]
    longitud = longitud_fx(datos, posicion)
    if primario & 0x80:
        longitud = longitud + 2
    if primario & 0x40:
        longitud = longitud + 2
    if primario & 0x20:
        longitud = longitud + 2
    if primario & 0x10:
        longitud = longitud + 1
    return longitud


def longitud_i021_110(datos, posicion):
    """Trajectory Intent (I021/110): TIS va con FX y TID es REP + 15 octetos por repetición."""
    primario = datos[posicion]
    longitud = longitud_fx(datos, posicion)
    if primario & 0x80:
        longitud = longitud + longitud_fx(datos, posicion + longitud)
    if primario & 0x40:
        repeticiones = datos[posicion + longitud]
        longitud = longitud + 1 + 15 * repeticiones
    return longitud


def longitud_i021_271(datos, posicion):
    """
    I021/271 ocupa 1 o 2 octetos. Ojo: el bit 1 de la extensión no es FX (lo dice una nota
    de la especificación), por eso aquí no vale longitud_fx.
    """
    if datos[posicion] & 0x01:
        return 2
    return 1


def longitud_i021_295(datos, posicion):
    """Data Ages (I021/295): cada bit de presencia del primario es un subcampo de 1 octeto."""
    longitud_primario = longitud_fx(datos, posicion)
    numero_subcampos = 0
    for indice in range(longitud_primario):
        octeto = datos[posicion + indice]
        for numero_bit in range(7):
            mascara = 0x80 >> numero_bit
            if octeto & mascara:
                numero_subcampos = numero_subcampos + 1
    return longitud_primario + numero_subcampos


def longitud_item_021(frn, datos, posicion):
    """Longitud en octetos del DI con ese FRN."""
    if frn in LONGITUD_FIJA_021:
        return LONGITUD_FIJA_021[frn]
    if frn == FRN_I021_040 or frn == FRN_I021_090:
        return longitud_fx(datos, posicion)
    if frn == FRN_I021_220:
        return longitud_i021_220(datos, posicion)
    if frn == FRN_I021_110:
        return longitud_i021_110(datos, posicion)
    if frn == FRN_I021_271:
        return longitud_i021_271(datos, posicion)
    if frn == FRN_I021_250:
        return 1 + 8 * datos[posicion]          # REP + 8 octetos por repetición
    if frn == FRN_I021_295:
        return longitud_i021_295(datos, posicion)
    if frn == FRN_RE or frn == FRN_SP:
        return datos[posicion]                  # el primer octeto es la longitud total
    raise ValueError("FRN " + str(frn) + " does not exist in the CAT021 UAP")


# =============================================================================
# Registro completo
# =============================================================================

def localizar_items(datos, posicion, lista_frn):
    """Recorre el registro calculando solo longitudes. Devuelve ({FRN: posición}, posicion_siguiente)."""
    posiciones = {}
    for frn in lista_frn:
        posiciones[frn] = posicion
        posicion = posicion + longitud_item_021(frn, datos, posicion)
    return posiciones, posicion


def decodificar_registro(datos, posicion, lista_frn):
    """
    Decodifica un registro CAT021 ya con el FSPEC leído.
    Devuelve (fila, posicion_siguiente, None), o (None, posicion_siguiente, motivo) si se descarta.
    """
    posiciones, posicion_siguiente = localizar_items(datos, posicion, lista_frn)

    fila = {"CAT": 21}

    # GBS = 1: está en tierra, fuera
    if FRN_I021_040 in posiciones:
        if leer_gbs_i021_040(datos, posiciones[FRN_I021_040]) == 1:
            return None, posicion_siguiente, MOTIVO_EN_TIERRA

    # sin posición no se puede pasar el filtro geográfico, así que también se descarta
    if FRN_I021_131 not in posiciones:
        return None, posicion_siguiente, MOTIVO_SIN_POSICION
    decode_i021_131(datos, posiciones[FRN_I021_131], fila)
    if not geo.dentro_de_zona(fila["LAT"], fila["LON"]):
        return None, posicion_siguiente, MOTIVO_FUERA_DE_ZONA

    # el mensaje se queda, ahora sí se decodifica lo demás
    if FRN_I021_010 in posiciones:
        decode_i021_010(datos, posiciones[FRN_I021_010], fila)
    if FRN_I021_080 in posiciones:
        decode_i021_080(datos, posiciones[FRN_I021_080], fila)
    if FRN_I021_073 in posiciones:
        decode_i021_073(datos, posiciones[FRN_I021_073], fila)
    if FRN_I021_070 in posiciones:
        decode_i021_070(datos, posiciones[FRN_I021_070], fila)
    if FRN_I021_145 in posiciones:
        decode_i021_145(datos, posiciones[FRN_I021_145], fila)
    if FRN_I021_170 in posiciones:
        decode_i021_170(datos, posiciones[FRN_I021_170], fila)
    if FRN_RE in posiciones:
        decode_i021_re(datos, posiciones[FRN_RE], fila)

    return fila, posicion_siguiente, None
