"""
bds.py

Paso 2 del flujo: DECODIFICACIÓN de los registros BDS que van dentro de I048/250.
    lectura -> decodificación -> coordenadas -> QNH -> CSV

Solo se decodifican los BDS 4.0, 5.0 y 6.0 (D10), con las tablas de
ICAO 9871 (2.ª ed.), Apéndice A:
    BDS 4.0  Selected vertical intention    Tabla A-2-64
    BDS 5.0  Track and turn report          Tabla A-2-80
    BDS 6.0  Heading and speed report       Tabla A-2-96

Cada registro BDS son 56 bits. En las tablas de ICAO los bits se numeran
del 1 al 56 empezando por el MSB, y aquí se usa la misma numeración.

Cada campo va precedido de un bit STATUS: si vale 0, el valor no es válido y
la celda se deja vacía (no se escribe en la fila).
Los campos con signo usan complemento a dos (ICAO 9871, §A.2.2.2).
"""

from funciones.lector import con_signo

BITS_REGISTRO_BDS = 56

# Escalas (LSB) de ICAO 9871
LSB_ALTITUD_SELECCIONADA_FT = 16        # BDS 4.0: 16 ft
LSB_PRESION_HPA = 0.1                   # BDS 4.0: 0,1 mb (1 mb = 1 hPa)
PRESION_BASE_HPA = 800                  # BDS 4.0: el campo es "BP menos 800 mb"
LSB_ALABEO_DEG = 45 / 256               # BDS 5.0 roll angle
LSB_ANGULO_DEG = 90 / 512               # BDS 5.0 true track angle y BDS 6.0 magnetic heading
LSB_VELOCIDAD_2_KT = 2                  # BDS 5.0 ground speed y true airspeed: 1024/512 kt
LSB_VARIACION_DERROTA_DEG_S = 8 / 256   # BDS 5.0 track angle rate
LSB_IAS_KT = 1                          # BDS 6.0 indicated airspeed
LSB_MACH = 0.004                        # BDS 6.0 mach: 2,048/512
LSB_VELOCIDAD_VERTICAL_FT_MIN = 32      # BDS 6.0 BAR e IVV: 8192/256 ft/min


def bit(registro, numero_bit):
    """Devuelve el bit numero_bit (1 = MSB, 56 = LSB) del registro BDS."""
    return (registro >> (BITS_REGISTRO_BDS - numero_bit)) & 0x01


def campo(registro, bit_inicio, bit_fin):
    """Devuelve el valor sin signo de los bits bit_inicio a bit_fin (ambos incluidos)."""
    numero_bits = bit_fin - bit_inicio + 1
    mascara = (1 << numero_bits) - 1
    return (registro >> (BITS_REGISTRO_BDS - bit_fin)) & mascara


def angulo_0_360(angulo_deg):
    """
    Pasa un ángulo de -180..+180° a 0..360°.
    ICAO da el true track angle (BDS 5.0) y el magnetic heading (BDS 6.0) con
    signo: un valor negativo es hacia el oeste (ejemplo de la tabla: 315° = -45°).
    Sumarle 360 da el mismo ángulo en 0..360°, que se puede comparar
    directamente con los rumbos de pista del P3 (244° y 064°).
    """
    if angulo_deg < 0:
        return angulo_deg + 360
    return angulo_deg


def decode_bds40(registro, fila):
    """
    BDS 4.0 Selected vertical intention. ICAO 9871, Tabla A-2-64.
    Columnas: BDS40_MCP_ALT, BDS40_FMS_ALT, BP, BDS40_VNAV, BDS40_ALT_HOLD,
              BDS40_APPROACH, BDS40_ALT_SOURCE.
    """
    if bit(registro, 1):
        # bits 2-13: MCP/FCU selected altitude, LSB = 16 ft
        fila["BDS40_MCP_ALT"] = campo(registro, 2, 13) * LSB_ALTITUD_SELECCIONADA_FT
    if bit(registro, 14):
        # bits 15-26: FMS selected altitude, LSB = 16 ft
        fila["BDS40_FMS_ALT"] = campo(registro, 15, 26) * LSB_ALTITUD_SELECCIONADA_FT
    if bit(registro, 27):
        # bits 28-39: barometric pressure setting menos 800 mb, LSB = 0,1 mb.
        # Se redondea a 1 decimal (la resolución del dato) para que no salgan
        # restos de coma flotante como 1013,2000000000001.
        presion = PRESION_BASE_HPA + campo(registro, 28, 39) * LSB_PRESION_HPA
        fila["BP"] = round(presion, 1)
    # bits 40-47: reservados
    if bit(registro, 48):
        # bit 48: status de los bits de modo MCP/FCU (49, 50 y 51)
        fila["BDS40_VNAV"] = bit(registro, 49)
        fila["BDS40_ALT_HOLD"] = bit(registro, 50)
        fila["BDS40_APPROACH"] = bit(registro, 51)
    # bits 52-53: reservados
    if bit(registro, 54):
        # bits 55-56: fuente de la altitud objetivo (0 desconocida, 1 avión, 2 FCU/MCP, 3 FMS)
        fila["BDS40_ALT_SOURCE"] = campo(registro, 55, 56)


def decode_bds50(registro, fila):
    """
    BDS 5.0 Track and turn report. ICAO 9871, Tabla A-2-80.
    Columnas: BDS50_RA, BDS50_TTA, BDS50_GS, BDS50_TAR, BDS50_TAS.
    """
    if bit(registro, 1):
        # bits 2-11: roll angle; bit 2 = signo (1 = ala izquierda abajo), LSB = 45/256 grados
        fila["BDS50_RA"] = con_signo(campo(registro, 2, 11), 10) * LSB_ALABEO_DEG
    if bit(registro, 12):
        # bits 13-23: true track angle; bit 13 = signo (1 = oeste), LSB = 90/512 grados
        angulo = con_signo(campo(registro, 13, 23), 11) * LSB_ANGULO_DEG
        fila["BDS50_TTA"] = angulo_0_360(angulo)
    if bit(registro, 24):
        # bits 25-34: ground speed, LSB = 1024/512 = 2 kt
        fila["BDS50_GS"] = campo(registro, 25, 34) * LSB_VELOCIDAD_2_KT
    if bit(registro, 35):
        # bits 36-45: track angle rate; bit 36 = signo, LSB = 8/256 grados/s
        fila["BDS50_TAR"] = con_signo(campo(registro, 36, 45), 10) * LSB_VARIACION_DERROTA_DEG_S
    if bit(registro, 46):
        # bits 47-56: true airspeed, LSB = 2 kt
        fila["BDS50_TAS"] = campo(registro, 47, 56) * LSB_VELOCIDAD_2_KT


def decode_bds60(registro, fila):
    """
    BDS 6.0 Heading and speed report. ICAO 9871, Tabla A-2-96.
    Columnas: BDS60_HDG, BDS60_IAS, BDS60_MACH, BDS60_BAR, BDS60_IVV.
    """
    if bit(registro, 1):
        # bits 2-12: magnetic heading; bit 2 = signo (1 = oeste), LSB = 90/512 grados
        angulo = con_signo(campo(registro, 2, 12), 11) * LSB_ANGULO_DEG
        fila["BDS60_HDG"] = angulo_0_360(angulo)
    if bit(registro, 13):
        # bits 14-23: indicated airspeed, LSB = 1 kt
        fila["BDS60_IAS"] = campo(registro, 14, 23) * LSB_IAS_KT
    if bit(registro, 24):
        # bits 25-34: mach, LSB = 2,048/512 = 0,004.
        # Se redondea a 3 decimales (la resolución del dato) para evitar restos de coma flotante.
        fila["BDS60_MACH"] = round(campo(registro, 25, 34) * LSB_MACH, 3)
    if bit(registro, 35):
        # bits 36-45: barometric altitude rate; bit 36 = signo (1 = bajando), LSB = 32 ft/min
        fila["BDS60_BAR"] = con_signo(campo(registro, 36, 45), 10) * LSB_VELOCIDAD_VERTICAL_FT_MIN
    if bit(registro, 46):
        # bits 47-56: inertial vertical velocity; bit 47 = signo (1 = bajando), LSB = 32 ft/min
        fila["BDS60_IVV"] = con_signo(campo(registro, 47, 56), 10) * LSB_VELOCIDAD_VERTICAL_FT_MIN
