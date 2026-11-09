"""
qnh.py

Paso 4 del flujo: corrección QNH.
    lectura -> decodificación -> coordenadas -> QNH -> CSV

El Modo C (FL) va referido a la presión estándar (1013,25 hPa), no al QNH.
Por eso los aviones que vuelan bajo pueden tener FL negativos. El enunciado pide
corregir el Modo C de los vuelos por debajo de la altitud de transición
(6000 ft) con:

    Altitud real = Modo C + (QNH actual - QNH estándar) x 30 ft
    con Modo C = FL x 100 ft y QNH estándar = 1013,25 hPa

El QNH actual es el BP que transmite el avión (BDS 4.0 en CAT048, BPS en CAT021).
Un BP dentro del rango estándar (duda 1) no es un QNH: es el avión que ya ha
puesto la presión estándar. El enunciado dice que en ese caso se sigue
corrigiendo con el BP anterior hasta los 6000 ft.

Ejemplo del enunciado (un avión despegando):
    FL 23,5,  BP 1018 -> 2350 + (1018 - 1013,25) x 30 = 2492,5 ft
    FL 24,75, BP 1013 -> 1013 es estándar, se usa el BP guardado (1018):
                         2475 + (1018 - 1013,25) x 30 = 2617,5 ft   (correcto)
                         con 1013 saldría 2467,5 ft                 (incorrecto)

Como hay que recordar el último BP de cada avión, se guarda un estado por
dirección Modo S (TA). Hay un estado para CAT048 y otro para CAT021, y solo
se actualiza con los mensajes que se quedan en el CSV.
"""

from funciones import decisiones

QNH_ESTANDAR_HPA = 1013.25      # QNH estándar de la fórmula
PIES_POR_HPA = 30               # 1 hPa equivale a 30 ft
PIES_POR_FL = 100               # Modo C: FL x 100 = altitud en ft


def crear_estado():
    """
    Estado de la corrección para una categoría:
        bp_guardado:      TA -> último BP no estándar recibido de ese avión
        altitud_anterior: TA -> FL x 100 del mensaje anterior de ese avión
    """
    return {"bp_guardado": {}, "altitud_anterior": {}}


def es_presion_estandar(bp_hpa, categoria):
    """True si el BP se considera presión estándar (duda 1)."""
    if categoria == 48:
        return decisiones.PRESION_ESTANDAR_048_MINIMA_HPA <= bp_hpa <= decisiones.PRESION_ESTANDAR_048_MAXIMA_HPA
    return bp_hpa in decisiones.PRESIONES_ESTANDAR_021_HPA


def corregir_altitud(estado, direccion_modo_s, nivel_vuelo, bp_hpa, categoria, fl_dudoso):
    """
    Devuelve la altitud corregida en ft, o None si no se corrige (celda vacía).

    estado:           el de la categoría del mensaje (crear_estado)
    direccion_modo_s: TA del mensaje (None si no viene)
    nivel_vuelo:      FL del mensaje (None si no viene)
    bp_hpa:           BP del mensaje (None si no viene)
    fl_dudoso:        True si el FL viene con V = 1 o G = 1 (solo CAT048)
    """
    # Sin dirección Modo S no se puede saber el BP anterior de ese avión.
    if direccion_modo_s is None:
        return None

    bp_guardado = estado["bp_guardado"]
    altitud_anterior = estado["altitud_anterior"]

    # 1. Si el avión acaba de cruzar 6000 ft hacia arriba (el mensaje anterior
    #    estaba por debajo y este a 6000 ft o más), se borra su BP guardado (duda 5).
    if nivel_vuelo is not None:
        altitud_actual = nivel_vuelo * PIES_POR_FL
        anterior = altitud_anterior.get(direccion_modo_s)
        if decisiones.BORRAR_BP_AL_CRUZAR_HACIA_ARRIBA and anterior is not None:
            if anterior < decisiones.UMBRAL_QNH_FT <= altitud_actual:
                bp_guardado.pop(direccion_modo_s, None)
        altitud_anterior[direccion_modo_s] = altitud_actual

    # 2. Un BP no estándar se guarda a cualquier altitud (duda 5).
    if bp_hpa is not None and not es_presion_estandar(bp_hpa, categoria):
        bp_guardado[direccion_modo_s] = bp_hpa

    # 3. Sin FL no hay nada que corregir.
    if nivel_vuelo is None:
        return None
    altitud_sin_corregir = nivel_vuelo * PIES_POR_FL

    # 4. A 6000 ft o más no se corrige (dudas 2 y 4).
    if altitud_sin_corregir >= decisiones.UMBRAL_QNH_FT:
        if decisiones.POR_ENCIMA_DEL_UMBRAL_CELDA_VACIA:
            return None
        return altitud_sin_corregir

    # 5. FL no validado o garbled (duda 6).
    if fl_dudoso and not decisiones.CORREGIR_FL_NO_VALIDADO_O_GARBLED:
        return None

    # 6. Sin ningún BP no estándar guardado (duda 3).
    if direccion_modo_s not in bp_guardado:
        if decisiones.SIN_BP_GUARDADO_CELDA_VACIA:
            return None
        return altitud_sin_corregir

    # 7. Se aplica la fórmula con el BP guardado.
    return altitud_sin_corregir + (bp_guardado[direccion_modo_s] - QNH_ESTANDAR_HPA) * PIES_POR_HPA
