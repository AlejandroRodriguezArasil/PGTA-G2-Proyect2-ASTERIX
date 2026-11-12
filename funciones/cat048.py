"""
cat048.py

Paso 2 del flujo: DECODIFICACIÓN de CAT048 (radar monorradar, especificación v1.31).
    lectura -> decodificación -> coordenadas -> QNH -> CSV

Recorre los DI de un registro en el orden de su FSPEC:
    - los 14 DI que pide el enunciado se decodifican (una función por DI)
    - los 14 DI que el enunciado deja fuera se saltan sin decodificarlos,
      sumando su longitud (CAT048 v1.31, §5.2 y Tabla 2 - Standard UAP)

Cada función decode_i048_xxx recibe los datos, la posición donde empieza el DI
y la fila (diccionario columna -> valor). Rellena sus columnas en la fila y
devuelve la posición donde empieza el DI siguiente.

Numeración de bits: como en la especificación, en un DI de n octetos el bit
n x 8 es el MSB del primer octeto y el bit 1 es el LSB del último.
"""

from funciones.lector import leer_entero, con_signo, longitud_fx, decodificar_caracteres_6_bits, formatear_hora
from funciones import bds

# Escalas (LSB) de la especificación CAT048 v1.31
LSB_TIEMPO_S = 1 / 128                  # I048/140: 1/128 s
LSB_RHO_NM = 1 / 256                    # I048/040: 1/256 NM
LSB_THETA_DEG = 360 / 2 ** 16           # I048/040 e I048/200: 360/2^16 grados
LSB_FL = 0.25                           # I048/090: 1/4 FL
LSB_RUNLENGTH_DEG = 360 / 2 ** 13       # I048/130 SRL y PRL: 360/2^13 grados
LSB_RPD_NM = 1 / 256                    # I048/130 RPD: 1/256 NM
LSB_APD_DEG = 360 / 2 ** 14             # I048/130 APD: 360/2^14 grados
LSB_VELOCIDAD_KT = 3600 / 2 ** 14       # I048/200: 2^-14 NM/s = 3600/2^14 kt

# Códigos de registro BDS que se decodifican en I048/250 (octeto BDS1/BDS2)
CODIGO_BDS_40 = 0x40
CODIGO_BDS_50 = 0x50
CODIGO_BDS_60 = 0x60
OCTETOS_POR_BDS = 8                     # 7 octetos de datos + 1 octeto BDS1/BDS2


# =============================================================================
# DI que se decodifican
# =============================================================================

def decode_i048_010(datos, posicion, fila):
    """
    I048/010 Data Source Identifier. 2 octetos fijos. CAT048 v1.31, §5.2.1.
    Columnas: SAC, SIC.
    """
    fila["SAC"] = datos[posicion]          # bits 16-9: System Area Code
    fila["SIC"] = datos[posicion + 1]      # bits 8-1: System Identification Code
    return posicion + 2


def decode_i048_140(datos, posicion, fila):
    """
    I048/140 Time of Day. 3 octetos fijos. CAT048 v1.31, §5.2.17.
    Columnas: TIME_S (segundos desde medianoche UTC) y TIME (hh:mm:ss,sss).
    """
    # bits 24-1: tiempo desde medianoche, LSB = 1/128 s
    segundos = leer_entero(datos, posicion, 3) * LSB_TIEMPO_S
    fila["TIME_S"] = segundos
    fila["TIME"] = formatear_hora(segundos)
    return posicion + 3


def decode_i048_020(datos, posicion, fila):
    """
    I048/020 Target Report Descriptor. 1 octeto + extensiones con FX. CAT048 v1.31, §5.2.2.
    Columnas: TYP, SIM, RDP, SPI, RAB (primer octeto);
              TST, ERR, XPP, ME, MI, FOE_FRI (extensión 1);
              ADSB_EP, ADSB_VAL, SCN_EP, SCN_VAL, PAI_EP, PAI_VAL (extensión 2).
    """
    longitud = longitud_fx(datos, posicion)

    octeto = datos[posicion]
    fila["I048_020_TYP"] = (octeto >> 5) & 0x07     # bits 8-6: tipo de detección
    fila["I048_020_SIM"] = (octeto >> 4) & 0x01     # bit 5: simulado
    fila["I048_020_RDP"] = (octeto >> 3) & 0x01     # bit 4: cadena RDP 1 o 2
    fila["I048_020_SPI"] = (octeto >> 2) & 0x01     # bit 3: Special Position Identification
    fila["I048_020_RAB"] = (octeto >> 1) & 0x01     # bit 2: 1 = report from field monitor

    if longitud >= 2:
        octeto = datos[posicion + 1]
        fila["I048_020_TST"] = (octeto >> 7) & 0x01      # bit 8: mensaje de test
        fila["I048_020_ERR"] = (octeto >> 6) & 0x01      # bit 7: Extended Range
        fila["I048_020_XPP"] = (octeto >> 5) & 0x01      # bit 6: X-Pulse
        fila["I048_020_ME"] = (octeto >> 4) & 0x01       # bit 5: emergencia militar
        fila["I048_020_MI"] = (octeto >> 3) & 0x01       # bit 4: identificación militar
        fila["I048_020_FOE_FRI"] = (octeto >> 1) & 0x03  # bits 3-2: Modo 4

    if longitud >= 3:
        octeto = datos[posicion + 2]
        fila["I048_020_ADSB_EP"] = (octeto >> 7) & 0x01  # bit 8
        fila["I048_020_ADSB_VAL"] = (octeto >> 6) & 0x01 # bit 7
        fila["I048_020_SCN_EP"] = (octeto >> 5) & 0x01   # bit 6
        fila["I048_020_SCN_VAL"] = (octeto >> 4) & 0x01  # bit 5
        fila["I048_020_PAI_EP"] = (octeto >> 3) & 0x01   # bit 4
        fila["I048_020_PAI_VAL"] = (octeto >> 2) & 0x01  # bit 3 (el bit 2 es spare)

    # Si hubiera más extensiones, no están definidas en la v1.31: se saltan.
    return posicion + longitud


def decode_i048_040(datos, posicion, fila):
    """
    I048/040 Measured Position in Slant Polar Co-ordinates. 4 octetos fijos. CAT048 v1.31, §5.2.4.
    Columnas: I048_040_RHO_NM, I048_040_THETA_DEG.
    """
    rho = leer_entero(datos, posicion, 2)          # bits 32-17: RHO, LSB = 1/256 NM
    theta = leer_entero(datos, posicion + 2, 2)    # bits 16-1: THETA, LSB = 360/2^16 grados
    fila["I048_040_RHO_NM"] = rho * LSB_RHO_NM
    fila["I048_040_THETA_DEG"] = theta * LSB_THETA_DEG
    return posicion + 4


def decode_i048_070(datos, posicion, fila):
    """
    I048/070 Mode-3/A Code in Octal Representation. 2 octetos fijos. CAT048 v1.31, §5.2.10.
    Columnas: I048_070_V, I048_070_G, I048_070_L, MODE3A (4 dígitos octales).
    """
    valor = leer_entero(datos, posicion, 2)
    fila["I048_070_V"] = (valor >> 15) & 0x01      # bit 16: 1 = código no validado
    fila["I048_070_G"] = (valor >> 14) & 0x01      # bit 15: 1 = garbled
    fila["I048_070_L"] = (valor >> 13) & 0x01      # bit 14: 1 = no extraído en el último scan
    codigo = valor & 0x0FFF                        # bits 12-1: A4 A2 A1 B4 B2 B1 C4 C2 C1 D4 D2 D1
    fila["MODE3A"] = format(codigo, "04o")         # 3 bits por dígito: se escribe en octal
    return posicion + 2


def decode_i048_090(datos, posicion, fila):
    """
    I048/090 Flight Level in Binary Representation. 2 octetos fijos. CAT048 v1.31, §5.2.12.
    Columnas: I048_090_V, I048_090_G, FL.
    """
    valor = leer_entero(datos, posicion, 2)
    fila["I048_090_V"] = (valor >> 15) & 0x01      # bit 16: 1 = código no validado
    fila["I048_090_G"] = (valor >> 14) & 0x01      # bit 15: 1 = garbled
    # bits 14-1: nivel de vuelo en complemento a dos, LSB = 1/4 FL
    nivel_vuelo = con_signo(valor & 0x3FFF, 14)
    fila["FL"] = nivel_vuelo * LSB_FL
    return posicion + 2


def decode_i048_130(datos, posicion, fila):
    """
    I048/130 Radar Plot Characteristics. Compuesto. CAT048 v1.31, §5.2.16.
    Primario: bits 8-2 indican qué subcampos vienen (SRL SRR SAM PRL PAM RPD APD), bit 1 FX.
    Cada subcampo ocupa 1 octeto, en ese orden.
    Columnas: I048_130_SRL, SRR, SAM, PRL, PAM, RPD, APD.
    """
    longitud_primario = longitud_fx(datos, posicion)
    primario = datos[posicion]
    posicion = posicion + longitud_primario
    # La v1.31 solo define subcampos en el primer octeto del primario.

    if primario & 0x80:     # bit 8: SRL, SSR plot runlength, LSB = 360/2^13 grados
        fila["I048_130_SRL"] = datos[posicion] * LSB_RUNLENGTH_DEG
        posicion = posicion + 1
    if primario & 0x40:     # bit 7: SRR, número de respuestas SSR recibidas
        fila["I048_130_SRR"] = datos[posicion]
        posicion = posicion + 1
    if primario & 0x20:     # bit 6: SAM, amplitud SSR en dBm, con signo
        fila["I048_130_SAM"] = con_signo(datos[posicion], 8)
        posicion = posicion + 1
    if primario & 0x10:     # bit 5: PRL, PSR plot runlength, LSB = 360/2^13 grados
        fila["I048_130_PRL"] = datos[posicion] * LSB_RUNLENGTH_DEG
        posicion = posicion + 1
    if primario & 0x08:     # bit 4: PAM, amplitud PSR en dBm, con signo
        fila["I048_130_PAM"] = con_signo(datos[posicion], 8)
        posicion = posicion + 1
    if primario & 0x04:     # bit 3: RPD, diferencia de rango PSR-SSR, LSB = 1/256 NM, con signo
        fila["I048_130_RPD"] = con_signo(datos[posicion], 8) * LSB_RPD_NM
        posicion = posicion + 1
    if primario & 0x02:     # bit 2: APD, diferencia de azimut PSR-SSR, LSB = 360/2^14 grados, con signo
        fila["I048_130_APD"] = con_signo(datos[posicion], 8) * LSB_APD_DEG
        posicion = posicion + 1
    return posicion


def decode_i048_220(datos, posicion, fila):
    """
    I048/220 Aircraft Address. 3 octetos fijos. CAT048 v1.31, §5.2.22.
    Columna: TA (dirección Modo S de 24 bits en hexadecimal, 6 caracteres).
    """
    direccion_modo_s = leer_entero(datos, posicion, 3)   # bits 24-1
    fila["TA"] = format(direccion_modo_s, "06X")
    return posicion + 3


def decode_i048_240(datos, posicion, fila):
    """
    I048/240 Aircraft Identification. 6 octetos fijos. CAT048 v1.31, §5.2.24.
    Columna: TI (8 caracteres de 6 bits; bit 48 = MSB del carácter 1).
    """
    fila["TI"] = decodificar_caracteres_6_bits(datos, posicion)
    return posicion + 6


def decode_i048_250(datos, posicion, fila):
    """
    I048/250 BDS Register Data (Mode S MB Data). Repetitivo: 1 + 8 x REP octetos.
    CAT048 v1.31, §5.2.25.
    Cada repetición: 56 bits de datos (bits 64-9) + BDS1 (bits 8-5) + BDS2 (bits 4-1).
    Solo se decodifican los BDS 4.0, 5.0 y 6.0, los que pide el enunciado; el resto se salta.
    Columnas: BP y las BDS40_*, BDS50_* y BDS60_* (ver bds.py).
    """
    repeticiones = datos[posicion]        # REP: número de registros BDS
    posicion = posicion + 1
    for numero_registro in range(repeticiones):
        datos_bds = leer_entero(datos, posicion, 7)    # los 56 bits del registro
        codigo_bds = datos[posicion + 7]               # BDS1 en los 4 bits altos, BDS2 en los bajos
        if codigo_bds == CODIGO_BDS_40:
            bds.decode_bds40(datos_bds, fila)
        elif codigo_bds == CODIGO_BDS_50:
            bds.decode_bds50(datos_bds, fila)
        elif codigo_bds == CODIGO_BDS_60:
            bds.decode_bds60(datos_bds, fila)
        posicion = posicion + OCTETOS_POR_BDS
    return posicion


def decode_i048_161(datos, posicion, fila):
    """
    I048/161 Track Number. 2 octetos fijos. CAT048 v1.31, §5.2.18.
    Columna: I048_161_TRACK_NUMBER (bits 12-1; los bits 16-13 son spare).
    """
    valor = leer_entero(datos, posicion, 2)
    fila["I048_161_TRACK_NUMBER"] = valor & 0x0FFF
    return posicion + 2


def decode_i048_200(datos, posicion, fila):
    """
    I048/200 Calculated Track Velocity in Polar Co-ordinates. 4 octetos fijos. CAT048 v1.31, §5.2.20.
    Columnas: I048_200_GS_KT, I048_200_HDG_DEG.
    """
    velocidad = leer_entero(datos, posicion, 2)    # bits 32-17: groundspeed, LSB = 2^-14 NM/s
    rumbo = leer_entero(datos, posicion + 2, 2)    # bits 16-1: heading, LSB = 360/2^16 grados
    fila["I048_200_GS_KT"] = velocidad * LSB_VELOCIDAD_KT
    fila["I048_200_HDG_DEG"] = rumbo * LSB_THETA_DEG
    return posicion + 4


def decode_i048_170(datos, posicion, fila):
    """
    I048/170 Track Status. 1 octeto + extensiones con FX. CAT048 v1.31, §5.2.19.
    Columnas: CNF, RAD, DOU, MAH, CDM (primer octeto); TRE, GHO, SUP, TCC (extensión 1).
    """
    longitud = longitud_fx(datos, posicion)

    octeto = datos[posicion]
    fila["I048_170_CNF"] = (octeto >> 7) & 0x01    # bit 8: 0 confirmada, 1 tentativa
    fila["I048_170_RAD"] = (octeto >> 5) & 0x03    # bits 7-6: sensor que mantiene la traza
    fila["I048_170_DOU"] = (octeto >> 4) & 0x01    # bit 5: baja confianza plot-traza
    fila["I048_170_MAH"] = (octeto >> 3) & 0x01    # bit 4: maniobra horizontal
    fila["I048_170_CDM"] = (octeto >> 1) & 0x03    # bits 3-2: subiendo / bajando / mantiene

    if longitud >= 2:
        octeto = datos[posicion + 1]
        fila["I048_170_TRE"] = (octeto >> 7) & 0x01    # bit 8: fin de traza
        fila["I048_170_GHO"] = (octeto >> 6) & 0x01    # bit 7: traza fantasma
        fila["I048_170_SUP"] = (octeto >> 5) & 0x01    # bit 6: mantenida con datos de otro nodo
        fila["I048_170_TCC"] = (octeto >> 4) & 0x01    # bit 5: tipo de transformación de coordenadas

    return posicion + longitud


def decode_i048_230(datos, posicion, fila):
    """
    I048/230 Communications/ACAS Capability and Flight Status. 2 octetos fijos. CAT048 v1.31, §5.2.23.
    Columnas: COM, STAT, SI, MSSC, ARC, AIC, B1A, B1B.
    """
    valor = leer_entero(datos, posicion, 2)
    fila["I048_230_COM"] = (valor >> 13) & 0x07    # bits 16-14: capacidad de comunicaciones
    fila["I048_230_STAT"] = (valor >> 10) & 0x07   # bits 13-11: estado de vuelo (1 y 3 = en tierra)
    fila["I048_230_SI"] = (valor >> 9) & 0x01      # bit 10: SI/II (el bit 9 es spare)
    fila["I048_230_MSSC"] = (valor >> 7) & 0x01    # bit 8: Mode-S Specific Service Capability
    fila["I048_230_ARC"] = (valor >> 6) & 0x01     # bit 7: resolución de altitud (0 = 100 ft, 1 = 25 ft)
    fila["I048_230_AIC"] = (valor >> 5) & 0x01     # bit 6: capacidad de identificación
    fila["I048_230_B1A"] = (valor >> 4) & 0x01     # bit 5: BDS 1,0 bit 16
    fila["I048_230_B1B"] = valor & 0x0F            # bits 4-1: BDS 1,0 bits 37-40
    return posicion + 2


# Tabla UAP de los DI que se decodifican (CAT048 v1.31, Tabla 2): FRN -> función.
DECODIFICADORES_048 = {
    1: decode_i048_010,
    2: decode_i048_140,
    3: decode_i048_020,
    4: decode_i048_040,
    5: decode_i048_070,
    6: decode_i048_090,
    7: decode_i048_130,
    8: decode_i048_220,
    9: decode_i048_240,
    10: decode_i048_250,
    11: decode_i048_161,
    13: decode_i048_200,
    14: decode_i048_170,
    21: decode_i048_230,
}


# =============================================================================
# DI que el enunciado deja fuera: se saltan sin decodificarlos
# =============================================================================

# DI de longitud fija que se saltan: FRN -> octetos (CAT048 v1.31, Tabla 2)
LONGITUD_FIJA_A_SALTAR = {
    12: 4,    # I048/042 Calculated Position in Cartesian Co-ordinates
    15: 4,    # I048/210 Track Quality
    17: 2,    # I048/080 Mode-3/A Code Confidence Indicator
    18: 4,    # I048/100 Mode-C Code and Confidence Indicator
    19: 2,    # I048/110 Height Measured by a 3D Radar
    22: 7,    # I048/260 ACAS Resolution Advisory Report
    23: 1,    # I048/055 Mode-1 Code in Octal Representation
    24: 2,    # I048/050 Mode-2 Code in Octal Representation
    25: 1,    # I048/065 Mode-1 Code Confidence Indicator
    26: 2,    # I048/060 Mode-2 Code Confidence Indicator
}

FRN_I048_030 = 16    # Warning/Error Conditions: longitud variable con FX
FRN_I048_120 = 20    # Radial Doppler Speed: compuesto
FRN_SP = 27          # Special Purpose Field: longitud explícita
FRN_RE = 28          # Reserved Expansion Field: longitud explícita


def saltar_i048_120(datos, posicion):
    """
    Salta I048/120 Radial Doppler Speed sin decodificarlo. CAT048 v1.31, §5.2.15.
    Primario con FX; bit 8 (CAL): subcampo de 2 octetos; bit 7 (RDS): REP + 6 octetos por repetición.
    """
    primario = datos[posicion]
    posicion = posicion + longitud_fx(datos, posicion)
    if primario & 0x80:
        posicion = posicion + 2
    if primario & 0x40:
        repeticiones = datos[posicion]
        posicion = posicion + 1 + 6 * repeticiones
    return posicion


def saltar_item_048(frn, datos, posicion):
    """Salta un DI que el enunciado no pide y devuelve la posición del DI siguiente."""
    if frn in LONGITUD_FIJA_A_SALTAR:
        return posicion + LONGITUD_FIJA_A_SALTAR[frn]
    if frn == FRN_I048_030:
        return posicion + longitud_fx(datos, posicion)
    if frn == FRN_I048_120:
        return saltar_i048_120(datos, posicion)
    if frn == FRN_SP or frn == FRN_RE:
        # Part 1, §4.3.5: el primer octeto da la longitud total, incluido él mismo
        return posicion + datos[posicion]
    raise ValueError("FRN " + str(frn) + " no existe en la UAP de CAT048")


# =============================================================================
# Registro completo
# =============================================================================

def decodificar_registro(datos, posicion, lista_frn):
    """
    Decodifica un registro CAT048 cuyo FSPEC ya se ha leído.
    'posicion' apunta al primer octeto después del FSPEC.
    Devuelve (fila, posicion_siguiente). posicion_siguiente es donde empieza el
    registro siguiente (o el final del bloque si era el último).
    """
    fila = {"CAT": 48}

    # El FSPEC dice qué DI vienen (lista_frn) y los DI van uno detrás de otro
    # en orden creciente de FRN, sin separadores. Por eso hay que recorrerlos
    # todos en orden: para saber dónde empieza un DI hay que conocer la longitud
    # de todos los anteriores.
    for frn in lista_frn:
        if frn in DECODIFICADORES_048:
            # DI que se decodifica: su función rellena la fila y devuelve
            # la posición donde empieza el DI siguiente.
            funcion = DECODIFICADORES_048[frn]
            posicion = funcion(datos, posicion, fila)
        else:
            # DI que el enunciado no pide: solo se calcula su longitud para pasar al siguiente.
            posicion = saltar_item_048(frn, datos, posicion)

    return fila, posicion

