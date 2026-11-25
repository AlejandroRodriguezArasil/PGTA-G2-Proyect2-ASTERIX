"""
Lectura del .ast: bloques (CAT + LEN + registros) y FSPEC de cada registro.
LEN es la longitud del bloque entero, con los 3 octetos de cabecera incluidos.
También están aquí las funciones de bits que usan cat048, cat021 y bds.
"""

LONGITUD_CABECERA_BLOQUE = 3   # CAT (1 octeto) + LEN (2 octetos)
BIT_FX = 0x01                  # el FX es el bit 1 del octeto
FRN_POR_OCTETO_FSPEC = 7       # bits 8 a 2 de cada octeto del FSPEC

# Lo que puede devolver problema_bloque
BLOQUE_CORTADO = "cortado"     # el bloque no cabe entero en el fichero
LEN_NO_VALIDO = "len"          # LEN menor que la cabecera


def leer_fichero(ruta):
    """Lee el fichero entero en bytes."""
    with open(ruta, "rb") as fichero:
        datos = fichero.read()
    return datos


def leer_entero(datos, posicion, numero_octetos):
    """Entero sin signo de numero_octetos octetos a partir de posicion (MSB primero)."""
    return int.from_bytes(datos[posicion:posicion + numero_octetos], "big")


def con_signo(valor, numero_bits):
    """Pasa un valor en complemento a dos de numero_bits bits a entero con signo (con 14 bits, 0x3FFC es -4)."""
    bit_de_signo = 1 << (numero_bits - 1)
    if valor & bit_de_signo:
        return valor - (1 << numero_bits)
    return valor


def longitud_fx(datos, posicion):
    """Longitud de un campo con FX: se van contando octetos mientras el bit 1 valga 1."""
    longitud = 1
    while datos[posicion + longitud - 1] & BIT_FX:
        longitud = longitud + 1
    return longitud


def problema_bloque(datos, posicion):
    """Mira si el bloque se puede leer: devuelve "" si está bien, o BLOQUE_CORTADO / LEN_NO_VALIDO."""
    if posicion + LONGITUD_CABECERA_BLOQUE > len(datos):
        return BLOQUE_CORTADO

    longitud_bloque = leer_entero(datos, posicion + 1, 2)
    if longitud_bloque < LONGITUD_CABECERA_BLOQUE:
        return LEN_NO_VALIDO
    if posicion + longitud_bloque > len(datos):
        return BLOQUE_CORTADO
    return ""


def leer_cabecera_bloque(datos, posicion):
    """Lee CAT y LEN y devuelve (categoria, longitud_bloque). Si no es un bloque válido, ValueError."""
    problema = problema_bloque(datos, posicion)
    if problema == BLOQUE_CORTADO:
        raise ValueError("the block at byte " + str(posicion) + " does not fit in the file")
    if problema == LEN_NO_VALIDO:
        raise ValueError("block with LEN = " + str(leer_entero(datos, posicion + 1, 2))
                         + " at byte " + str(posicion))

    categoria = datos[posicion]
    longitud_bloque = leer_entero(datos, posicion + 1, 2)
    return categoria, longitud_bloque


def leer_fspec(datos, posicion):
    """
    Lee el FSPEC y devuelve (lista_frn, posicion_siguiente).
    En cada octeto el bit 8 es el primer FRN y el bit 1 es FX (si vale 1, sigue otro octeto).
    """
    lista_frn = []
    numero_octeto = 0
    while True:
        octeto = datos[posicion]
        posicion = posicion + 1

        # bits 8 a 2 (0x80 es el bit 8)
        for numero_bit in range(FRN_POR_OCTETO_FSPEC):
            mascara = 0x80 >> numero_bit
            if octeto & mascara:
                frn = numero_octeto * FRN_POR_OCTETO_FSPEC + numero_bit + 1
                lista_frn.append(frn)

        numero_octeto = numero_octeto + 1
        if not octeto & BIT_FX:
            break

    return lista_frn, posicion


def decodificar_caracteres_6_bits(datos, posicion):
    """
    Callsign de I048/240 e I021/170: 8 caracteres de 6 bits (1-26 A-Z, 32 espacio, 48-57 0-9).
    Lo que no está en la tabla sale como '?', y los espacios del final se quitan porque son relleno.
    """
    valor = leer_entero(datos, posicion, 6)   # carácter 1 en los bits 48-43
    texto = ""
    for numero_caracter in range(8):
        desplazamiento = 42 - 6 * numero_caracter
        codigo = (valor >> desplazamiento) & 0x3F
        if 1 <= codigo <= 26:
            texto = texto + chr(ord("A") + codigo - 1)
        elif codigo == 32:
            texto = texto + " "
        elif 48 <= codigo <= 57:
            texto = texto + chr(codigo)
        else:
            texto = texto + "?"
    return texto.rstrip(" ")


def formatear_hora(segundos):
    """Segundos desde medianoche -> "hh:mm:ss,sss", con coma decimal."""
    milisegundos_totales = round(segundos * 1000)
    horas = milisegundos_totales // 3600000
    minutos = (milisegundos_totales // 60000) % 60
    segundos_enteros = (milisegundos_totales // 1000) % 60
    milisegundos = milisegundos_totales % 1000
    return "%02d:%02d:%02d,%03d" % (horas, minutos, segundos_enteros, milisegundos)
