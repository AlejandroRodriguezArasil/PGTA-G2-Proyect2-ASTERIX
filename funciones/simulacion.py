"""
simulacion.py

Lógica de la simulación de trayectorias, sin nada de ventana ni mapa.
Lo que se dibuja está en mapa.py y los botones en main.py (sección 6).

Cómo funciona:
    1. preparar() ordena por hora (TIME_S) las filas que hay que simular. En el
       fichero los mensajes no van en orden de tiempo (retrocesos de hasta 0,7 s
       en CAT048 y 2 s en CAT021), así que hay que ordenarlos. La lista ordenada
       solo guarda referencias a las mismas tuplas, no las copia.
    2. avanzar_un_segundo() suma 1 s a la hora de la simulación y procesa los
       mensajes con TIME_S <= esa hora. Cada mensaje actualiza la última posición
       conocida de su avión.
    3. Un avión que lleva más de SEGUNDOS_PARA_CADUCAR sin mensajes desaparece.

Un avión es la pareja (categoría, dirección Modo S). Si el mensaje no trae
dirección (TA), se usa (categoría, track number). Radar y ADS-B nunca se juntan:
el mismo avión visto por los dos sistemas son dos aviones de la simulación.
"""

from funciones.exportar_csv import valor

# El radar refresca cada 4 s. Con 12 s sin mensajes (3 vueltas de antena) el avión desaparece;
# así una vuelta perdida suelta (huecos de 7 u 11 s en los datos) no lo hace parpadear.
SEGUNDOS_PARA_CADUCAR = 12

# Posiciones que se guardan para dibujar la estela de cada avión (unos 60 s de radar)
POSICIONES_ESTELA = 15


def tiempo_de_fila(fila):
    """Hora del mensaje en segundos desde medianoche (se usa para ordenar)."""
    return valor(fila, "TIME_S")


def identificador_avion(fila):
    """
    Devuelve el identificador de avión de una fila: (CAT, TA) o, si no hay TA,
    (CAT, "TN" + track number). Si no hay ninguno de los dos, devuelve None.
    """
    categoria = valor(fila, "CAT")
    direccion_modo_s = valor(fila, "TA")
    if direccion_modo_s is not None:
        return (categoria, direccion_modo_s)
    numero_traza = valor(fila, "I048_161_TRACK_NUMBER")
    if numero_traza is not None:
        return (categoria, "TN" + str(numero_traza))
    return None


def preparar(filas):
    """
    Prepara la simulación de las filas indicadas (las filtradas en la pestaña Datos).
    Devuelve el estado de la simulación, un diccionario con:
        filas:    las filas ordenadas por hora
        indice:   posición de la siguiente fila por procesar
        inicio:   primer segundo de los datos
        fin:      último segundo de los datos
        segundo:  hora actual de la simulación (segundos desde medianoche)
        aviones:  identificador -> {"fila", "tiempo", "estela", ...} de cada avión a la vista
        mensajes_por_categoria: {48: n, 21: n}, para avisar si un sistema no tiene mensajes
    """
    filas_validas = []
    mensajes_por_categoria = {48: 0, 21: 0}
    for fila in filas:
        if valor(fila, "TIME_S") is not None and valor(fila, "LAT") is not None:
            if identificador_avion(fila) is not None:
                filas_validas.append(fila)
                mensajes_por_categoria[valor(fila, "CAT")] += 1
    filas_ordenadas = sorted(filas_validas, key=tiempo_de_fila)   # orden estable: a igual hora, el del fichero

    estado = {"filas": filas_ordenadas, "indice": 0, "inicio": 0, "fin": 0, "segundo": 0, "aviones": {},
              "mensajes_por_categoria": mensajes_por_categoria}
    if len(filas_ordenadas) > 0:
        estado["inicio"] = int(tiempo_de_fila(filas_ordenadas[0]))
        estado["fin"] = int(tiempo_de_fila(filas_ordenadas[-1])) + 1
        ir_a_segundo(estado, estado["inicio"])
    return estado


def procesar_hasta(estado, segundo):
    """
    Procesa las filas con TIME_S <= segundo: cada una pasa a ser la última posición
    conocida de su avión. Devuelve el conjunto de aviones que han cambiado.
    """
    cambiados = set()
    filas = estado["filas"]
    while estado["indice"] < len(filas) and tiempo_de_fila(filas[estado["indice"]]) <= segundo:
        fila = filas[estado["indice"]]
        identificador = identificador_avion(fila)
        if identificador not in estado["aviones"]:
            # rumbo_dibujo y posicion_rumbo los usa mapa.py para orientar la silueta de ADS-B
            estado["aviones"][identificador] = {"fila": None, "tiempo": 0, "estela": [],
                                                "rumbo_dibujo": None, "posicion_rumbo": None}
        avion = estado["aviones"][identificador]
        avion["fila"] = fila
        avion["tiempo"] = tiempo_de_fila(fila)
        avion["estela"].append((valor(fila, "LAT"), valor(fila, "LON")))
        if len(avion["estela"]) > POSICIONES_ESTELA:
            avion["estela"].pop(0)
        cambiados.add(identificador)
        estado["indice"] = estado["indice"] + 1
    return cambiados


def quitar_caducados(estado):
    """Quita los aviones sin mensajes desde hace más de SEGUNDOS_PARA_CADUCAR. Devuelve la lista de los quitados."""
    caducados = []
    for identificador in estado["aviones"]:
        if estado["segundo"] - estado["aviones"][identificador]["tiempo"] > SEGUNDOS_PARA_CADUCAR:
            caducados.append(identificador)
    for identificador in caducados:
        del estado["aviones"][identificador]
    return caducados


def avanzar_un_segundo(estado):
    """
    Un salto de la simulación: la hora avanza 1 s.
    Devuelve (cambiados, caducados): los aviones con posición nueva y los que han desaparecido.
    """
    estado["segundo"] = estado["segundo"] + 1
    cambiados = procesar_hasta(estado, estado["segundo"])
    caducados = quitar_caducados(estado)
    for identificador in caducados:
        cambiados.discard(identificador)
    return cambiados, caducados


def ir_a_segundo(estado, segundo):
    """
    Salta a una hora concreta (también lo usa Reset): empieza desde la primera fila y procesa
    todo hasta esa hora sin dibujar. Cada avión queda en su última posición conocida antes de esa hora.
    """
    estado["indice"] = 0
    estado["aviones"] = {}
    estado["segundo"] = segundo
    procesar_hasta(estado, segundo)
    quitar_caducados(estado)


def ha_terminado(estado):
    """True si la simulación ha llegado al final de los datos."""
    return estado["segundo"] >= estado["fin"]
