"""
Lógica de la simulación (sin ventana ni mapa): avanza segundo a segundo, guarda la última posición
de cada avión, su estado en tierra / en vuelo y los eventos.
En el mapa un avión es (categoría, TA); en el tráfico es solo su TA, lo vea radar, ADS-B o los dos.
"""

from funciones import filtros
from funciones.exportar_csv import valor

CATEGORIA_048 = 48
CATEGORIA_021 = 21

# El radar da una vuelta cada 4 s. Con 12 s (3 vueltas) una vuelta perdida no hace parpadear al avión
SEGUNDOS_PARA_CADUCAR = 12

# Puntos de la estela (unos 60 s de radar)
POSICIONES_ESTELA = 15

# None = desconocido
EN_TIERRA = "on ground"
EN_VUELO = "airborne"

# STAT de I048/230: 1 y 3 = en tierra, 0 y 2 = en vuelo. De 4 a 7 no dicen dónde está
STAT_EN_TIERRA = (1, 3)
STAT_EN_VUELO = (0, 2)

# Con un solo mensaje bastaría un STAT raro para sacar un despegue o aterrizaje falso
MENSAJES_PARA_CAMBIAR_ESTADO = 2

# Tipos de evento
NUEVO_CONTACTO = "New contact"
DESPEGA = "Takeoff"
ATERRIZA = "Landing"
PERDIDA_CONTACTO = "Contact lost"
EVENTOS_GUARDADOS = 300

NOMBRE_SISTEMA = {CATEGORIA_048: "Radar", CATEGORIA_021: "ADS-B"}
VISTO_POR_AMBOS = "Both"

# Tendencia vertical
SUBE = "↑"
BAJA = "↓"
NIVELADO = "→"
NOMBRE_TENDENCIA = {SUBE: "climbing", BAJA: "descending", NIVELADO: "level"}
UMBRAL_TENDENCIA_FT_MIN = 300   # +-300 ft/min
SEGUNDOS_TENDENCIA = 10
# Al menos una vuelta de antena entre los dos FL, si no 1/4 de FL ya parece que sube
SEGUNDOS_MINIMOS_TENDENCIA = 4
PIES_POR_FL = 100
SEGUNDOS_POR_MINUTO = 60


# =============================================================================
# Preparar y avanzar
# =============================================================================

def tiempo_de_fila(fila):
    """Hora del mensaje en segundos desde medianoche."""
    return valor(fila, "TIME_S")


def identificador_avion(fila):
    """(CAT, TA), o (CAT, "TN" + track number) si no hay TA. None si no hay ninguno."""
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
    Crea el diccionario con el estado de la simulación a partir de las filas filtradas.
    Las filas se ordenan por TIME_S porque en el fichero no vienen del todo en orden.
    """
    filas_validas = []
    mensajes_por_categoria = {CATEGORIA_048: 0, CATEGORIA_021: 0}
    for fila in filas:
        if valor(fila, "TIME_S") is not None and valor(fila, "LAT") is not None:
            if identificador_avion(fila) is not None:
                filas_validas.append(fila)
                mensajes_por_categoria[valor(fila, "CAT")] += 1
    filas_ordenadas = sorted(filas_validas, key=tiempo_de_fila)   # a igual hora se queda el orden del fichero

    estado = {"filas": filas_ordenadas, "indice": 0, "inicio": 0, "fin": 0, "segundo": 0,
              "aviones": {}, "trafico": {}, "eventos": [], "numero_eventos": 0,
              "despegues": 0, "aterrizajes": 0, "silencio": False,
              "mensajes_por_categoria": mensajes_por_categoria}
    if len(filas_ordenadas) > 0:
        estado["inicio"] = int(tiempo_de_fila(filas_ordenadas[0]))
        estado["fin"] = int(tiempo_de_fila(filas_ordenadas[-1])) + 1
        ir_a_segundo(estado, estado["inicio"])
    return estado


def procesar_hasta(estado, segundo):
    """Procesa las filas hasta ese segundo y devuelve los aviones que han cambiado."""
    cambiados = set()
    filas = estado["filas"]
    while estado["indice"] < len(filas) and tiempo_de_fila(filas[estado["indice"]]) <= segundo:
        fila = filas[estado["indice"]]
        identificador = identificador_avion(fila)
        if identificador not in estado["aviones"]:
            # rumbo_dibujo y posicion_rumbo son para girar la silueta ADS-B en mapa.py
            estado["aviones"][identificador] = {"fila": None, "tiempo": 0, "estela": [],
                                                "rumbo_dibujo": None, "posicion_rumbo": None,
                                                "historial_fl": [], "tendencia": ""}
        avion = estado["aviones"][identificador]
        avion["fila"] = fila
        avion["tiempo"] = tiempo_de_fila(fila)
        avion["estela"].append((valor(fila, "LAT"), valor(fila, "LON")))
        if len(avion["estela"]) > POSICIONES_ESTELA:
            avion["estela"].pop(0)
        guardar_fl(avion)
        # En silencio la tendencia se calcula una vez al final (ir_a_segundo), no en cada mensaje
        if not estado["silencio"]:
            avion["tendencia"] = calcular_tendencia(identificador, avion)
        actualizar_trafico(estado, identificador, fila)
        cambiados.add(identificador)
        estado["indice"] = estado["indice"] + 1
    return cambiados


def quitar_caducados(estado):
    """
    Quita los aviones que llevan demasiado sin mensajes y devuelve cuáles.
    Si ya no lo ve ningún sistema, se anota la pérdida de contacto.
    """
    caducados = []
    for identificador in estado["aviones"]:
        if estado["segundo"] - estado["aviones"][identificador]["tiempo"] > SEGUNDOS_PARA_CADUCAR:
            caducados.append(identificador)

    for identificador in caducados:
        del estado["aviones"][identificador]
        categoria = identificador[0]
        direccion_modo_s = identificador[1]
        if direccion_modo_s not in estado["trafico"]:
            continue                                # blanco puro, transponder fijo o sin TA
        avion_trafico = estado["trafico"][direccion_modo_s]
        if categoria == CATEGORIA_048:
            avion_trafico["estado_radar"] = None    # el último STAT ya no vale
        if (otra_categoria(categoria), direccion_modo_s) not in estado["aviones"]:
            anotar_evento(estado, PERDIDA_CONTACTO, estado["segundo"], avion_trafico["nombre"], categoria,
                          direccion_modo_s)
            del estado["trafico"][direccion_modo_s]
    return caducados


def avanzar_un_segundo(estado):
    """Avanza 1 s. Devuelve (cambiados, caducados)."""
    estado["segundo"] = estado["segundo"] + 1
    cambiados = procesar_hasta(estado, estado["segundo"])
    caducados = quitar_caducados(estado)
    for identificador in caducados:
        cambiados.discard(identificador)
    return cambiados, caducados


def ir_a_segundo(estado, segundo):
    """
    Salta a una hora: repite la simulación desde el principio en silencio, sin anotar eventos,
    para que los aviones queden como si se hubiera reproducido. Luego vacía los eventos.
    """
    estado["indice"] = 0
    estado["aviones"] = {}
    estado["trafico"] = {}
    estado["silencio"] = True
    paso = estado["inicio"]
    while paso < segundo:
        estado["segundo"] = paso
        procesar_hasta(estado, paso)
        quitar_caducados(estado)
        paso = paso + 1
    estado["segundo"] = segundo
    procesar_hasta(estado, segundo)
    quitar_caducados(estado)
    estado["silencio"] = False

    estado["eventos"] = []
    estado["numero_eventos"] = 0
    estado["despegues"] = 0
    estado["aterrizajes"] = 0
    for identificador in estado["aviones"]:
        avion = estado["aviones"][identificador]
        avion["tendencia"] = calcular_tendencia(identificador, avion)


def ha_terminado(estado):
    """True si la simulación ha llegado al final de los datos."""
    return estado["segundo"] >= estado["fin"]


def otra_categoria(categoria):
    """21 si es 48 y al revés."""
    if categoria == CATEGORIA_048:
        return CATEGORIA_021
    return CATEGORIA_048


# =============================================================================
# Tendencia vertical
# =============================================================================

def guardar_fl(avion):
    """Guarda el FL con su hora y tira los de hace más de SEGUNDOS_TENDENCIA."""
    nivel_vuelo = valor(avion["fila"], "FL")
    if nivel_vuelo is None:
        return
    historial = avion["historial_fl"]
    historial.append((avion["tiempo"], nivel_vuelo))
    while avion["tiempo"] - historial[0][0] > SEGUNDOS_TENDENCIA:
        historial.pop(0)


def clasificar_tendencia(pies_por_minuto):
    """Pasa la velocidad vertical (ft/min) a flecha."""
    if pies_por_minuto > UMBRAL_TENDENCIA_FT_MIN:
        return SUBE
    if pies_por_minuto < -UMBRAL_TENDENCIA_FT_MIN:
        return BAJA
    return NIVELADO


def calcular_tendencia(identificador, avion):
    """
    Tendencia vertical ("" si no se sabe). En radar se usa BAR o IVV del BDS 6.0 si vienen;
    si no, y siempre en ADS-B, lo que ha cambiado el FL en los últimos segundos, en ft/min.
    """
    fila = avion["fila"]
    if identificador[0] == CATEGORIA_048:
        velocidad_vertical = valor(fila, "BDS60_BAR")
        if velocidad_vertical is None:
            velocidad_vertical = valor(fila, "BDS60_IVV")
        if velocidad_vertical is not None:
            return clasificar_tendencia(velocidad_vertical)

    historial = avion["historial_fl"]
    if len(historial) < 2:
        return ""
    tiempo_antiguo, fl_antiguo = historial[0]
    tiempo_reciente, fl_reciente = historial[-1]
    segundos = tiempo_reciente - tiempo_antiguo
    if segundos < SEGUNDOS_MINIMOS_TENDENCIA:
        return ""
    pies_por_minuto = (fl_reciente - fl_antiguo) * PIES_POR_FL / segundos * SEGUNDOS_POR_MINUTO
    return clasificar_tendencia(pies_por_minuto)


# =============================================================================
# Tráfico: estado en tierra / en vuelo y eventos
# =============================================================================

def es_del_trafico(identificador, fila):
    """Tiene que tener TA y no ser blanco puro ni el transponder fijo."""
    if identificador[1].startswith("TN"):
        return False
    if filtros.es_blanco_puro(fila) or filtros.es_transponder_fijo(fila):
        return False
    return True


def nuevo_avion_trafico(nombre):
    """Avión nuevo del tráfico. candidato es el estado que aún falta confirmar."""
    return {"estado": None, "candidato": None, "repeticiones": 0, "estado_radar": None, "nombre": nombre}


def actualizar_trafico(estado, identificador, fila):
    """Actualiza el nombre y el estado del avión del tráfico con este mensaje."""
    if not es_del_trafico(identificador, fila):
        return
    categoria = identificador[0]
    direccion_modo_s = identificador[1]
    callsign = valor(fila, "TI")

    if direccion_modo_s not in estado["trafico"]:
        if callsign is not None and callsign != "":
            nombre = callsign
        else:
            nombre = direccion_modo_s
        estado["trafico"][direccion_modo_s] = nuevo_avion_trafico(nombre)
        anotar_evento(estado, NUEVO_CONTACTO, tiempo_de_fila(fila), nombre, categoria, direccion_modo_s)

    avion_trafico = estado["trafico"][direccion_modo_s]
    if callsign is not None and callsign != "":
        avion_trafico["nombre"] = callsign      # a veces el callsign llega más tarde que la TA
    observado = estado_observado(categoria, fila, avion_trafico)
    cambiar_estado(estado, avion_trafico, observado, fila, categoria, direccion_modo_s)


def estado_observado(categoria, fila, avion_trafico):
    """
    Si el mensaje dice en tierra, en vuelo o nada (None). En CAT048 sale del STAT; el ADS-B
    siempre es en vuelo (los de tierra se descartan al decodificar), salvo si el radar ya lo ve.
    """
    if categoria == CATEGORIA_048:
        stat = valor(fila, "I048_230_STAT")
        if stat in STAT_EN_TIERRA:
            avion_trafico["estado_radar"] = EN_TIERRA
            return EN_TIERRA
        if stat in STAT_EN_VUELO:
            avion_trafico["estado_radar"] = EN_VUELO
            return EN_VUELO
        return None
    if avion_trafico["estado_radar"] is not None:
        return None
    return EN_VUELO


def cambiar_estado(estado, avion_trafico, observado, fila, categoria, direccion_modo_s):
    """
    Máquina de estados del avión. Un estado distinto del actual tiene que repetirse
    MENSAJES_PARA_CAMBIAR_ESTADO veces seguidas para aceptarlo. Tierra -> vuelo es un despegue
    y vuelo -> tierra un aterrizaje; el primer estado (desde None) no da evento.
    """
    if observado is None:
        return
    if observado == avion_trafico["estado"]:
        avion_trafico["candidato"] = None
        avion_trafico["repeticiones"] = 0
        return
    if observado == avion_trafico["candidato"]:
        avion_trafico["repeticiones"] = avion_trafico["repeticiones"] + 1
    else:
        avion_trafico["candidato"] = observado
        avion_trafico["repeticiones"] = 1
    if avion_trafico["repeticiones"] < MENSAJES_PARA_CAMBIAR_ESTADO:
        return

    anterior = avion_trafico["estado"]
    avion_trafico["estado"] = observado
    avion_trafico["candidato"] = None
    avion_trafico["repeticiones"] = 0
    if anterior == EN_TIERRA and observado == EN_VUELO:
        anotar_evento(estado, DESPEGA, tiempo_de_fila(fila), avion_trafico["nombre"], categoria, direccion_modo_s)
    elif anterior == EN_VUELO and observado == EN_TIERRA:
        anotar_evento(estado, ATERRIZA, tiempo_de_fila(fila), avion_trafico["nombre"], categoria, direccion_modo_s)


def anotar_evento(estado, tipo, segundo, nombre, categoria, direccion_modo_s):
    """Añade un evento y suma los despegues y aterrizajes. En silencio no hace nada."""
    if estado["silencio"]:
        return
    estado["numero_eventos"] = estado["numero_eventos"] + 1
    estado["eventos"].append({"numero": estado["numero_eventos"], "segundo": segundo, "tipo": tipo,
                              "nombre": nombre, "sistema": NOMBRE_SISTEMA[categoria], "ta": direccion_modo_s})
    if len(estado["eventos"]) > EVENTOS_GUARDADOS:
        estado["eventos"].pop(0)
    if tipo == DESPEGA:
        estado["despegues"] = estado["despegues"] + 1
    elif tipo == ATERRIZA:
        estado["aterrizajes"] = estado["aterrizajes"] + 1


def esta_en_tierra(estado, direccion_modo_s):
    """True si el avión con esa TA está en tierra (confirmado)."""
    if direccion_modo_s not in estado["trafico"]:
        return False
    return estado["trafico"][direccion_modo_s]["estado"] == EN_TIERRA


def texto_estado_avion(estado, identificador):
    """Texto del estado para el panel del avión seleccionado ("-" si no es tráfico)."""
    direccion_modo_s = identificador[1]
    if direccion_modo_s not in estado["trafico"]:
        return "-"
    estado_avion = estado["trafico"][direccion_modo_s]["estado"]
    if estado_avion is None:
        return "unknown"
    return estado_avion


def texto_tendencia(tendencia):
    """Flecha más el nombre, p. ej. "↑ climbing"."""
    if tendencia == "":
        return "-"
    return tendencia + " " + NOMBRE_TENDENCIA[tendencia]


def eventos_nuevos(estado, ultimo_mostrado):
    """Los eventos que la ventana todavía no ha mostrado, en orden."""
    nuevos = []
    for evento in reversed(estado["eventos"]):
        if evento["numero"] <= ultimo_mostrado:
            break
        nuevos.append(evento)
    nuevos.reverse()
    return nuevos


# =============================================================================
# Textos del tráfico: nivel al estilo de control aéreo y filas de las listas
# =============================================================================

def texto_nivel(fila, tendencia, con_prefijo):
    """
    Nivel como en control aéreo: "A025" con altitud corregida, "FL045" si no, "---" si no hay nada.
    Sin prefijo (para las etiquetas del mapa) queda "025".
    """
    altitud_corregida = valor(fila, "ALT_CORRECTED_FT")
    nivel_vuelo = valor(fila, "FL")
    if altitud_corregida is not None:
        prefijo = "A"
        cientos = int(round(altitud_corregida / PIES_POR_FL))
    elif nivel_vuelo is not None:
        prefijo = "FL"
        cientos = int(round(nivel_vuelo))
    else:
        return "---"
    texto = format(cientos, "03d") + tendencia
    if con_prefijo:
        return prefijo + texto
    return texto


def filas_trafico(estado, categorias_visibles):
    """
    Filas de las listas En vuelo y En tierra (TA -> (nombre, valores)), solo con los sistemas visibles.
    Si lo ven los dos, el nivel se coge del radar.
    """
    en_vuelo = {}
    en_tierra = {}
    aviones = estado["aviones"]
    for direccion_modo_s in estado["trafico"]:
        avion_trafico = estado["trafico"][direccion_modo_s]
        if avion_trafico["estado"] is None:
            continue
        sistemas_que_lo_ven = []
        avion_referencia = None
        for categoria in (CATEGORIA_048, CATEGORIA_021):
            identificador = (categoria, direccion_modo_s)
            if categoria in categorias_visibles and identificador in aviones:
                sistemas_que_lo_ven.append(categoria)
                if avion_referencia is None:
                    avion_referencia = aviones[identificador]
        if len(sistemas_que_lo_ven) == 0:
            continue

        nombre = avion_trafico["nombre"]
        if avion_trafico["estado"] == EN_VUELO:
            nivel = texto_nivel(avion_referencia["fila"], avion_referencia["tendencia"], True)
            en_vuelo[direccion_modo_s] = (nombre, (nombre, nivel, texto_visto_por(sistemas_que_lo_ven)))
        else:
            en_tierra[direccion_modo_s] = (nombre, (nombre,))
    return en_vuelo, en_tierra


def texto_visto_por(categorias):
    """Texto de la columna "Seen by"."""
    if len(categorias) == 2:
        return VISTO_POR_AMBOS
    return NOMBRE_SISTEMA[categorias[0]]
