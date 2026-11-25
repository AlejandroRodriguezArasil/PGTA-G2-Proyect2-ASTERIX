"""
Corrección QNH de la altitud para los vuelos por debajo de 6000 ft:
altitud = FL x 100 + (BP - 1013,25) x 30 ft
Se guarda el último BP no estándar de cada avión (por TA), uno para CAT048 y otro para CAT021.
"""

QNH_ESTANDAR_HPA = 1013.25
PIES_POR_HPA = 30               # 1 hPa son unos 30 ft
PIES_POR_FL = 100

# Altitud de transición. Se mira con el FL sin corregir, porque la corregida todavía
# no se tiene cuando hay que decidir.
UMBRAL_QNH_FT = 6000

# Rango de presión estándar en CAT048 (el BDS 4.0 va de 0,1 en 0,1 hPa)
PRESION_ESTANDAR_048_MINIMA_HPA = 1013.0
PRESION_ESTANDAR_048_MAXIMA_HPA = 1013.5

# En ADS-B el BPS va de 0,8 en 0,8 hPa y no cae nunca entre 1013 y 1013,5,
# así que la estándar sale como 1012,8 o 1013,6.
PRESIONES_ESTANDAR_021_HPA = (1012.8, 1013.6)


def crear_estado():
    """Diccionarios por TA con el BP guardado y el FL x 100 del mensaje anterior."""
    return {"bp_guardado": {}, "altitud_anterior": {}}


def es_presion_estandar(bp_hpa, categoria):
    """Mira si el BP es la presión estándar (el criterio cambia entre CAT048 y CAT021)."""
    if categoria == 48:
        return PRESION_ESTANDAR_048_MINIMA_HPA <= bp_hpa <= PRESION_ESTANDAR_048_MAXIMA_HPA
    return bp_hpa in PRESIONES_ESTANDAR_021_HPA


def corregir_altitud(estado, direccion_modo_s, nivel_vuelo, bp_hpa, categoria):
    """
    Altitud corregida en ft, o None si no toca corregir (la celda queda vacía).
    Si el BP del mensaje es el estándar se usa el último BP no estándar guardado de ese avión.
    """
    # sin TA no sabemos qué BP tenía guardado
    if direccion_modo_s is None:
        return None

    bp_guardado = estado["bp_guardado"]
    altitud_anterior = estado["altitud_anterior"]

    # Si acaba de subir por encima de 6000 ft se olvida su BP: al volver a bajar
    # tendrá que mandar un QNH nuevo.
    if nivel_vuelo is not None:
        altitud_actual = nivel_vuelo * PIES_POR_FL
        anterior = altitud_anterior.get(direccion_modo_s)
        if anterior is not None and anterior < UMBRAL_QNH_FT <= altitud_actual:
            bp_guardado.pop(direccion_modo_s, None)
        altitud_anterior[direccion_modo_s] = altitud_actual

    # Un BP no estándar es el QNH del avión, se guarda esté a la altitud que esté
    if bp_hpa is not None and not es_presion_estandar(bp_hpa, categoria):
        bp_guardado[direccion_modo_s] = bp_hpa

    if nivel_vuelo is None:
        return None
    altitud_sin_corregir = nivel_vuelo * PIES_POR_FL

    # a 6000 ft o más no se corrige
    if altitud_sin_corregir >= UMBRAL_QNH_FT:
        return None

    # todavía no ha llegado ningún QNH de este avión
    if direccion_modo_s not in bp_guardado:
        return None

    return altitud_sin_corregir + (bp_guardado[direccion_modo_s] - QNH_ESTANDAR_HPA) * PIES_POR_HPA
