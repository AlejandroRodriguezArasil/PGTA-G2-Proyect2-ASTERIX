"""
lector.py

Paso 1 del flujo: LECTURA.
    lectura -> decodificación -> coordenadas -> QNH -> CSV

Lee el fichero .ast y separa sus piezas según la estructura general de
ASTERIX (Part 1, §4.3, y CAT048 v1.31, §4.6.2):

    bloque   = CAT (1 octeto) + LEN (2 octetos) + uno o varios registros
    registro = FSPEC + los DI presentes, en orden creciente de FRN

LEN es la longitud total del bloque e incluye los 3 octetos de CAT y LEN.

Aquí también están las funciones de bits que usan cat048.py, cat021.py y
bds.py (complemento a dos y campos con bit FX).
"""

LONGITUD_CABECERA_BLOQUE = 3   # CAT (1 octeto) + LEN (2 octetos)
BIT_FX = 0x01                  # bit 1 de un octeto: FX (Field Extension)
FRN_POR_OCTETO_FSPEC = 7       # cada octeto del FSPEC indica 7 FRN (bits 8 a 2)


def leer_fichero(ruta):
    """Devuelve todo el contenido del fichero .ast como bytes."""
    with open(ruta, "rb") as fichero:
        datos = fichero.read()
    return datos


def leer_entero(datos, posicion, numero_octetos):
    """Lee numero_octetos a partir de posicion como un entero sin signo (MSB primero)."""
    return int.from_bytes(datos[posicion:posicion + numero_octetos], "big")


def con_signo(valor, numero_bits):
    """
    Interpreta 'valor' como un número en complemento a dos de numero_bits bits.
    Part 1, §5: los valores negativos se representan en complemento a dos.
    Ejemplo: con 14 bits, 0x3FFC (16380) es -4.
    """
    bit_de_signo = 1 << (numero_bits - 1)
    if valor & bit_de_signo:
        return valor - (1 << numero_bits)
    return valor


def longitud_fx(datos, posicion):
    """
    Longitud en octetos de un campo de longitud variable con FX
    (Part 1, §4.3.4, "Extended length Data Fields"): se avanza octeto a
    octeto mientras el bit 1 (FX) valga 1.
    """
    longitud = 1
    while datos[posicion + longitud - 1] & BIT_FX:
        longitud = longitud + 1
    return longitud


def leer_cabecera_bloque(datos, posicion):
    """
    Lee CAT y LEN del bloque que empieza en 'posicion'.
    Devuelve (categoria, longitud_bloque).
    Lanza ValueError si los octetos no pueden ser un bloque ASTERIX.
    """
    if posicion + LONGITUD_CABECERA_BLOQUE > len(datos):
        raise ValueError("el fichero se corta en mitad de un bloque (octeto " + str(posicion) + ")")

    categoria = datos[posicion]
    longitud_bloque = leer_entero(datos, posicion + 1, 2)

    if longitud_bloque < LONGITUD_CABECERA_BLOQUE:
        raise ValueError("bloque con LEN = " + str(longitud_bloque) + " en el octeto " + str(posicion))
    if posicion + longitud_bloque > len(datos):
        raise ValueError("el LEN del bloque del octeto " + str(posicion) + " se sale del fichero")

    return categoria, longitud_bloque


def bloque_cortado(datos, posicion):
    """True si el bloque que empieza en 'posicion' no cabe entero en el fichero (el fichero se corta)."""
    if posicion + LONGITUD_CABECERA_BLOQUE > len(datos):
        return True
    return posicion + leer_entero(datos, posicion + 1, 2) > len(datos)


def leer_fspec(datos, posicion):
    """
    Lee el FSPEC de un registro y devuelve (lista_frn, posicion_siguiente).

    Part 1, §4.3.7: cada octeto del FSPEC tiene 7 bits de presencia y el bit FX.
    En el FSPEC los bits se numeran de izquierda a derecha, así que:
        octeto 1: bit 8 = FRN 1, bit 7 = FRN 2, ..., bit 2 = FRN 7, bit 1 = FX
        octeto 2: bit 8 = FRN 8, ..., bit 2 = FRN 14, bit 1 = FX
    Si FX = 1 sigue otro octeto de FSPEC; si FX = 0, el FSPEC termina.
    """
    lista_frn = []
    numero_octeto = 0
    while True:
        octeto = datos[posicion]
        posicion = posicion + 1

        # Se revisan los bits 8 a 2 del octeto: la máscara 0x80 es el bit 8
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
    Decodifica los 8 caracteres de 6 bits de I048/240 e I021/170 (6 octetos).
    Codificación: "Tabla codificación Target Identification" (ICAO, tabla 3-8):
        1-26  -> A-Z
        32    -> espacio
        48-57 -> 0-9
    Cualquier otro código no está en la tabla y se escribe como '?'.
    Los espacios del final son relleno y se quitan.
    """
    valor = leer_entero(datos, posicion, 6)   # 48 bits: carácter 1 en los bits 48-43
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
    """
    Pasa segundos desde medianoche a texto hh:mm:ss,sss (con coma decimal).
    Lo usan I048/140 e I021/073.
    """
    milisegundos_totales = round(segundos * 1000)
    horas = milisegundos_totales // 3600000
    minutos = (milisegundos_totales // 60000) % 60
    segundos_enteros = (milisegundos_totales // 1000) % 60
    milisegundos = milisegundos_totales % 1000
    return "%02d:%02d:%02d,%03d" % (horas, minutos, segundos_enteros, milisegundos)
