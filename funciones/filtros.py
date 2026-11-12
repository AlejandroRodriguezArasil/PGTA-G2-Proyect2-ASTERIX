"""
filtros.py

Filtros sobre las filas ya decodificadas.

Cada filtro es una función que recibe una lista de filas y devuelve otra lista
con las que cumplen la condición, en el mismo orden. No se copian las filas:
la lista nueva apunta a las mismas tuplas, así que filtrar no gasta RAM extra.
Como cada filtro devuelve una lista, se pueden encadenar: eso es lo que
hace aplicar_filtros().

Los filtros nunca vuelven a leer el .ast: trabajan sobre la lista en memoria.
"""

from funciones.exportar_csv import valor

CATEGORIA_048 = 48
ESTADOS_EN_TIERRA = (1, 3)      # I048/230 STAT: 1 y 3 = "aircraft on ground" (CAT048 v1.31, §5.2.23)
PIES_POR_FL = 100

# Blanco puro: TYP de I048/020 = 0, 1, 2 o 3 (sin detección, PSR, SSR y PSR+SSR). Ninguno viene
# de una interrogación Modo S; TYP = 0 también cuenta, porque tampoco es una detección Modo S.
TIPOS_BLANCO_PURO = (0, 1, 2, 3)

# Transponder fijo: se identifica solo por su Modo 3/A 7777, el del transponder de referencia en
# tierra. El bit RAB de I048/020 no se usa para esto.
MODO_3A_TRANSPONDER_FIJO = "7777"


def filtrar_por_categoria(filas, categoria):
    """
    Categoría ASTERIX.
    Columna: CAT. Se quedan las filas cuya CAT es la indicada (48 o 21).
    """
    resultado = []
    for fila in filas:
        if valor(fila, "CAT") == categoria:
            resultado.append(fila)
    return resultado


def es_blanco_puro(fila):
    """
    True si el mensaje es un blanco puro: CAT048 con el TYP de I048/020 en TIPOS_BLANCO_PURO
    (0, 1, 2 o 3: sin detección, PSR, SSR y PSR+SSR).
    Los TYP 4 a 7 vienen de una interrogación Modo S y no lo son. También lo usa el mapa.
    """
    if valor(fila, "CAT") != CATEGORIA_048:
        return False
    return valor(fila, "I048_020_TYP") in TIPOS_BLANCO_PURO


def quitar_blancos_puros(filas):
    """
    Quitar blancos puros. Solo afecta a CAT048.
    Columna: I048_020_TYP. Criterio: es_blanco_puro().
    """
    resultado = []
    for fila in filas:
        if not es_blanco_puro(fila):
            resultado.append(fila)
    return resultado


def es_transponder_fijo(fila):
    """
    True si el mensaje es del transponder fijo: Modo 3/A igual a MODO_3A_TRANSPONDER_FIJO (7777).
    También lo usa el mapa.
    """
    return valor(fila, "MODE3A") == MODO_3A_TRANSPONDER_FIJO


def quitar_transponder_fijo(filas):
    """
    Quitar transponder fijo. CAT048 y CAT021.
    Columna: MODE3A. Criterio: es_transponder_fijo().
    """
    resultado = []
    for fila in filas:
        if not es_transponder_fijo(fila):
            resultado.append(fila)
    return resultado


def quitar_en_tierra(filas):
    """
    Quitar aeronaves en tierra (filtro optativo "Ground" del enunciado). Solo afecta a CAT048
    (los CAT021 en tierra ya se descartaron al decodificar, por el bit GBS).
    Columna: I048_230_STAT. Se quita la fila si STAT es 1 o 3 ("aircraft on ground").
    Si el mensaje no trae I048/230, se queda: no consta que esté en tierra.
    """
    resultado = []
    for fila in filas:
        if valor(fila, "CAT") == CATEGORIA_048 and valor(fila, "I048_230_STAT") in ESTADOS_EN_TIERRA:
            continue
        resultado.append(fila)
    return resultado


def solo_con_fl(filas):
    """
    Solo mensajes con FL (filtro adicional, lo usa el P3).
    Columna: FL. Se quedan las filas que tienen nivel de vuelo.
    """
    resultado = []
    for fila in filas:
        if valor(fila, "FL") is not None:
            resultado.append(fila)
    return resultado


def altitud_de_fila(fila):
    """
    Altitud en ft que usa el filtro de altitud máxima: ALT_CORREGIDA_FT si existe y,
    si no, FL x 100. Devuelve None si la fila no tiene ninguna de las dos.
    """
    altitud_corregida = valor(fila, "ALT_CORREGIDA_FT")
    if altitud_corregida is not None:
        return altitud_corregida
    nivel_vuelo = valor(fila, "FL")
    if nivel_vuelo is not None:
        return nivel_vuelo * PIES_POR_FL
    return None


def filtrar_altitud_maxima(filas, altitud_maxima_ft):
    """
    Altitud máxima (filtro adicional, lo usa el P3 con 6000 ft).
    Columnas: ALT_CORREGIDA_FT y, si está vacía, FL x 100.
    Se quedan las filas con altitud <= altitud_maxima_ft. Las que no tienen ninguna
    de las dos columnas se quitan, porque no se puede saber si cumplen.
    """
    resultado = []
    for fila in filas:
        altitud = altitud_de_fila(fila)
        if altitud is not None and altitud <= altitud_maxima_ft:
            resultado.append(fila)
    return resultado


def buscar_aeronave(filas, texto):
    """
    Aeronave (filtro optativo "trayectoria" del enunciado). CAT048 y CAT021.
    Columnas: TI (callsign), TA (dirección Modo S) y MODE3A.
    Se quedan las filas en las que el texto aparece dentro de alguna de las tres,
    sin distinguir mayúsculas. Por ejemplo, "RYR" encuentra todos los Ryanair.
    """
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
    """True si alguna de las opciones de filtro está activada."""
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
    """Texto corto con los filtros activos, por ejemplo "CAT048, sin aeronaves en tierra"."""
    partes = []
    if opciones["categoria"] is not None:
        partes.append("CAT0" + str(opciones["categoria"]))
    if opciones["quitar_blancos_puros"]:
        partes.append("sin blancos puros")
    if opciones["quitar_transponder_fijo"]:
        partes.append("sin transponder fijo")
    if opciones["quitar_en_tierra"]:
        partes.append("sin aeronaves en tierra")
    if opciones["solo_con_fl"]:
        partes.append("solo con FL")
    if opciones["altitud_maxima_ft"] is not None:
        partes.append("altitud ≤ " + format(opciones["altitud_maxima_ft"], "g").replace(".", ",") + " ft")
    if opciones["aeronave"] != "":
        partes.append("aeronave «" + opciones["aeronave"] + "»")
    return ", ".join(partes)


def aplicar_filtros(filas, opciones):
    """
    Aplica uno detrás de otro los filtros activos y devuelve las filas que quedan.
    'opciones' es el diccionario que arma la ventana:
        "categoria":               None (ambas), 48 o 21
        "quitar_blancos_puros":    True / False
        "quitar_transponder_fijo": True / False
        "quitar_en_tierra":        True / False
        "solo_con_fl":             True / False
        "altitud_maxima_ft":       None o un número
        "aeronave":                "" o el texto a buscar
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
