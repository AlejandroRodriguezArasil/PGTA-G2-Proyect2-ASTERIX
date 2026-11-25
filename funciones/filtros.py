"""
Filtros sobre las filas ya decodificadas. Cada uno recibe una lista de filas y devuelve
otra con las que pasan (las mismas tuplas, sin copiarlas), así se pueden encadenar.
"""

from funciones.exportar_csv import valor

CATEGORIA_048 = 48
ESTADOS_EN_TIERRA = (1, 3)      # STAT de I048/230: 1 y 3 son "aircraft on ground"
PIES_POR_FL = 100

# Blanco puro: TYP de I048/020 de 0 a 3 (sin detección, PSR, SSR, PSR+SSR), o sea,
# nada que venga de Modo S. El 0 también cuenta.
TIPOS_BLANCO_PURO = (0, 1, 2, 3)

# El transponder fijo de tierra se reconoce solo por el 7777 (el bit RAB no se mira)
MODO_3A_TRANSPONDER_FIJO = "7777"


def filtrar_por_categoria(filas, categoria):
    """Deja solo las filas de la categoría pedida (48 o 21)."""
    resultado = []
    for fila in filas:
        if valor(fila, "CAT") == categoria:
            resultado.append(fila)
    return resultado


def es_blanco_puro(fila):
    """Blanco puro = CAT048 con TYP entre 0 y 3 (el mapa también lo usa)."""
    if valor(fila, "CAT") != CATEGORIA_048:
        return False
    return valor(fila, "I048_020_TYP") in TIPOS_BLANCO_PURO


def quitar_blancos_puros(filas):
    """Quita los blancos puros (solo hay en CAT048)."""
    resultado = []
    for fila in filas:
        if not es_blanco_puro(fila):
            resultado.append(fila)
    return resultado


def es_transponder_fijo(fila):
    """True si el Modo 3/A es 7777. Se usa también en el mapa."""
    return valor(fila, "MODE3A") == MODO_3A_TRANSPONDER_FIJO


def quitar_transponder_fijo(filas):
    """Quita los mensajes del transponder fijo, en las dos categorías."""
    resultado = []
    for fila in filas:
        if not es_transponder_fijo(fila):
            resultado.append(fila)
    return resultado


def quitar_en_tierra(filas):
    """
    Quita los CAT048 con STAT 1 o 3. Los CAT021 en tierra ya se tiran al decodificar (bit GBS),
    y si no viene I048/230 la fila se queda.
    """
    resultado = []
    for fila in filas:
        if valor(fila, "CAT") == CATEGORIA_048 and valor(fila, "I048_230_STAT") in ESTADOS_EN_TIERRA:
            continue
        resultado.append(fila)
    return resultado


def solo_con_fl(filas):
    """Deja solo las filas con FL (pensado para el P3)."""
    resultado = []
    for fila in filas:
        if valor(fila, "FL") is not None:
            resultado.append(fila)
    return resultado


def altitud_de_fila(fila):
    """La altitud corregida si la hay; si no, FL x 100 (None si no hay ninguna)."""
    altitud_corregida = valor(fila, "ALT_CORRECTED_FT")
    if altitud_corregida is not None:
        return altitud_corregida
    nivel_vuelo = valor(fila, "FL")
    if nivel_vuelo is not None:
        return nivel_vuelo * PIES_POR_FL
    return None


def filtrar_altitud_maxima(filas, altitud_maxima_ft):
    """Se queda con las filas a altitud_maxima_ft o menos; las que no tienen altitud se quitan."""
    resultado = []
    for fila in filas:
        altitud = altitud_de_fila(fila)
        if altitud is not None and altitud <= altitud_maxima_ft:
            resultado.append(fila)
    return resultado


def buscar_aeronave(filas, texto):
    """Busca el texto en TI, TA o MODE3A sin mirar mayúsculas ("RYR" saca todos los Ryanair)."""
    texto = texto.strip().upper()
    resultado = []
    for fila in filas:
        for columna in ("TI", "TA", "MODE3A"):
            contenido = valor(fila, columna)
            if contenido is not None and texto in contenido.upper():
                resultado.append(fila)
                break
    return resultado


def hay_filtros_activos(opciones):
    """Dice si hay algún filtro puesto."""
    if opciones["categoria"] is not None:
        return True
    if opciones["quitar_blancos_puros"] or opciones["quitar_transponder_fijo"]:
        return True
    if opciones["quitar_en_tierra"] or opciones["solo_con_fl"]:
        return True
    if opciones["altitud_maxima_ft"] is not None or opciones["aeronave"] != "":
        return True
    return False


def describir_filtros(opciones):
    """Texto con los filtros activos para enseñarlo en la ventana."""
    partes = []
    if opciones["categoria"] is not None:
        partes.append("CAT0" + str(opciones["categoria"]))
    if opciones["quitar_blancos_puros"]:
        partes.append("no pure targets")
    if opciones["quitar_transponder_fijo"]:
        partes.append("no fixed transponder")
    if opciones["quitar_en_tierra"]:
        partes.append("no aircraft on ground")
    if opciones["solo_con_fl"]:
        partes.append("FL only")
    if opciones["altitud_maxima_ft"] is not None:
        partes.append("altitude ≤ " + format(opciones["altitud_maxima_ft"], "g") + " ft")
    if opciones["aeronave"] != "":
        partes.append("aircraft \"" + opciones["aeronave"] + "\"")
    return ", ".join(partes)


def aplicar_filtros(filas, opciones):
    """
    Aplica uno detrás de otro los filtros que estén activos en 'opciones'
    (el diccionario que monta la ventana).
    """
    resultado = filas
    if opciones["categoria"] is not None:
        resultado = filtrar_por_categoria(resultado, opciones["categoria"])
    if opciones["quitar_blancos_puros"]:
        resultado = quitar_blancos_puros(resultado)
    if opciones["quitar_transponder_fijo"]:
        resultado = quitar_transponder_fijo(resultado)
    if opciones["quitar_en_tierra"]:
        resultado = quitar_en_tierra(resultado)
    if opciones["solo_con_fl"]:
        resultado = solo_con_fl(resultado)
    if opciones["altitud_maxima_ft"] is not None:
        resultado = filtrar_altitud_maxima(resultado, opciones["altitud_maxima_ft"])
    if opciones["aeronave"] != "":
        resultado = buscar_aeronave(resultado, opciones["aeronave"])
    return resultado
