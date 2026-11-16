"""
simulacion.py

Lógica de la simulación de trayectorias, sin nada de ventana ni mapa.
Lo que se dibuja está en interfaz/mapa.py, los paneles en interfaz/ventana.py y main.py
solo conecta los botones con estas funciones.

Cómo funciona:
    1. preparar() ordena por hora (TIME_S) las filas que hay que simular. En el
       fichero los mensajes no van en orden de tiempo (retrocesos de hasta 0,7 s
       en CAT048 y 2 s en CAT021), así que hay que ordenarlos. La lista ordenada
       solo guarda referencias a las mismas tuplas, no las copia.
    2. avanzar_un_segundo() suma 1 s a la hora de la simulación y procesa los
       mensajes con TIME_S <= esa hora. Cada mensaje actualiza la última posición
       conocida de su avión.
    3. Un avión que lleva más de SEGUNDOS_PARA_CADUCAR sin mensajes desaparece.

Hay dos formas de ver los aviones:
    - En el mapa, un avión es la pareja (categoría, dirección Modo S). Si el mensaje no
      trae dirección (TA), se usa (categoría, track number). Radar y ADS-B nunca se
      juntan: el mismo avión visto por los dos sistemas son dos siluetas.
    - En el tráfico (listas En vuelo / En tierra y eventos), un avión es su TA, lo vea
      un sistema o los dos. Los blancos puros (sin TA) y el transponder fijo no son tráfico.

Estado en tierra / en vuelo de cada avión del tráfico (ver estado_observado y cambiar_estado):
    - CAT048: el STAT de I048/230 (CAT048 v1.31, §5.2.23). 1 y 3 = en tierra; 0 y 2 = en vuelo;
      4 a 7 no dicen si está en tierra o en el aire. Sin I048/230 el mensaje no dice nada.
    - CAT021: los mensajes en tierra (GBS = 1) se descartan al decodificar, así que todo lo
      que llega de ADS-B está en vuelo.
    - Si el radar ve el avión con un STAT que dice tierra o vuelo, manda el radar.
    - Un estado nuevo solo se acepta tras MENSAJES_PARA_CAMBIAR_ESTADO mensajes seguidos
      que lo digan. Mientras no se acepta ninguno, el estado es desconocido (None).

Eventos (ver anotar_evento): nuevo contacto, despega, aterriza y pérdida de contacto. Solo
salen al reproducir o al avanzar 1 s: al saltar a otra hora (ir_a_segundo) el estado se
recalcula en silencio y la lista de eventos y los totales empiezan de cero.
"""

from funciones import filtros
from funciones.exportar_csv import valor

CATEGORIA_048 = 48
CATEGORIA_021 = 21

# El radar refresca cada 4 s. Con 12 s sin mensajes (3 vueltas de antena) el avión desaparece;
# así una vuelta perdida suelta (huecos de 7 u 11 s en los datos) no lo hace parpadear.
SEGUNDOS_PARA_CADUCAR = 12

# Posiciones que se guardan para dibujar la estela de cada avión (unos 60 s de radar)
POSICIONES_ESTELA = 15

# Estado de un avión del tráfico (el texto es el que se ve en el panel). None es "desconocido".
EN_TIERRA = "on ground"
EN_VUELO = "airborne"

# I048/230 STAT (CAT048 v1.31, §5.2.23): 0 = sin alerta en vuelo, 1 = sin alerta en tierra,
# 2 = alerta en vuelo, 3 = alerta en tierra. 4 a 7 (alerta o SPI sin decir dónde, no asignado,
# desconocido) no sirven para saber si está en tierra.
STAT_EN_TIERRA = (1, 3)
STAT_EN_VUELO = (0, 2)

# Un cambio de estado se confirma con 2 mensajes seguidos que digan el estado nuevo. El STAT de
# un solo mensaje puede venir cambiado (un parpadeo) y daría despegues y aterrizajes falsos.
MENSAJES_PARA_CAMBIAR_ESTADO = 2

# Tipos de evento (el texto es el que se ve en la ventana de eventos)
NUEVO_CONTACTO = "New contact"
DESPEGA = "Takeoff"
ATERRIZA = "Landing"
PERDIDA_CONTACTO = "Contact lost"
EVENTOS_GUARDADOS = 300         # la lista guarda solo los últimos

# Nombre de cada sistema en la lista En vuelo (columna "Seen by") y en los eventos
NOMBRE_SISTEMA = {CATEGORIA_048: "Radar", CATEGORIA_021: "ADS-B"}
VISTO_POR_AMBOS = "Both"

# Tendencia vertical. En radar se usa la velocidad vertical del BDS 6.0 (BAR o, si no, IVV);
# si no la hay, y siempre en ADS-B, la variación del FL en los últimos SEGUNDOS_TENDENCIA.
SUBE = "↑"
BAJA = "↓"
NIVELADO = "→"
NOMBRE_TENDENCIA = {SUBE: "climbing", BAJA: "descending", NIVELADO: "level"}
UMBRAL_TENDENCIA_FT_MIN = 300   # por encima de +300 ft/min sube; por debajo de -300, baja
SEGUNDOS_TENDENCIA = 10
# Para calcularla con el FL, los dos mensajes que se comparan tienen que estar separados al menos
# una vuelta de antena (4 s): con menos, un cambio de 1/4 de FL ya parecería una subida.
SEGUNDOS_MINIMOS_TENDENCIA = 4
PIES_POR_FL = 100
SEGUNDOS_POR_MINUTO = 60


# =============================================================================
# Preparar y avanzar
# =============================================================================

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
        aviones:  identificador -> {"fila", "tiempo", "estela", ...} de cada avión del mapa
        trafico:  TA -> {"estado", "nombre", ...} de cada avión del tráfico (ver nuevo_avion_trafico)
        eventos:  los últimos EVENTOS_GUARDADOS eventos, del más antiguo al más reciente
        numero_eventos: eventos anotados desde el último salto de hora (la ventana lo usa para
                  saber cuáles le faltan por mostrar)
        despegues, aterrizajes: totales desde el último salto de hora
        silencio: True mientras se recalcula el estado al saltar de hora (no se anotan eventos)
        mensajes_por_categoria: {48: n, 21: n}, para avisar si un sistema no tiene mensajes
    """
    filas_validas = []
    mensajes_por_categoria = {CATEGORIA_048: 0, CATEGORIA_021: 0}
    for fila in filas:
        if valor(fila, "TIME_S") is not None and valor(fila, "LAT") is not None:
            if identificador_avion(fila) is not None:
                filas_validas.append(fila)
                mensajes_por_categoria[valor(fila, "CAT")] += 1
    filas_ordenadas = sorted(filas_validas, key=tiempo_de_fila)   # orden estable: a igual hora, el del fichero

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
    """
    Procesa las filas con TIME_S <= segundo: cada una pasa a ser la última posición
    conocida de su avión y pone al día el tráfico. Devuelve el conjunto de aviones que han cambiado.
    """
    cambiados = set()
    filas = estado["filas"]
    while estado["indice"] < len(filas) and tiempo_de_fila(filas[estado["indice"]]) <= segundo:
        fila = filas[estado["indice"]]
        identificador = identificador_avion(fila)
        if identificador not in estado["aviones"]:
            # rumbo_dibujo y posicion_rumbo los usa mapa.py para orientar la silueta de ADS-B
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
        # Al recalcular en silencio la tendencia no se calcula mensaje a mensaje: se calcula una
        # sola vez al final, para los aviones que quedan (ver ir_a_segundo)
        if not estado["silencio"]:
            avion["tendencia"] = calcular_tendencia(identificador, avion)
        actualizar_trafico(estado, identificador, fila)
        cambiados.add(identificador)
        estado["indice"] = estado["indice"] + 1
    return cambiados


def quitar_caducados(estado):
    """
    Quita los aviones sin mensajes desde hace más de SEGUNDOS_PARA_CADUCAR. Devuelve la lista de
    los quitados. Si un avión del tráfico ya no se ve por ningún sistema, es una pérdida de contacto.
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
            avion_trafico["estado_radar"] = None    # el radar ya no lo ve: su último STAT ya no vale
        if (otra_categoria(categoria), direccion_modo_s) not in estado["aviones"]:
            anotar_evento(estado, PERDIDA_CONTACTO, estado["segundo"], avion_trafico["nombre"], categoria,
                          direccion_modo_s)
            del estado["trafico"][direccion_modo_s]
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
    Salta a una hora concreta (también lo usan Reset y la barra de tiempo). Empieza desde la
    primera fila y repite la simulación segundo a segundo hasta esa hora, sin dibujar y sin anotar
    eventos: así cada avión queda igual que si se hubiera reproducido hasta ahí (en su última
    posición conocida, con su estado en tierra / en vuelo y sin los que ya habían desaparecido).
    Después la lista de eventos y los totales empiezan de cero.
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
    """La categoría del otro sistema: 21 para 48 y 48 para 21."""
    if categoria == CATEGORIA_048:
        return CATEGORIA_021
    return CATEGORIA_048


# =============================================================================
# Tendencia vertical
# =============================================================================

def guardar_fl(avion):
    """Guarda el FL del último mensaje con su hora y olvida los de hace más de SEGUNDOS_TENDENCIA."""
    nivel_vuelo = valor(avion["fila"], "FL")
    if nivel_vuelo is None:
        return
    historial = avion["historial_fl"]
    historial.append((avion["tiempo"], nivel_vuelo))
    while avion["tiempo"] - historial[0][0] > SEGUNDOS_TENDENCIA:
        historial.pop(0)


def clasificar_tendencia(pies_por_minuto):
    """Flecha de la tendencia según la velocidad vertical en ft/min."""
    if pies_por_minuto > UMBRAL_TENDENCIA_FT_MIN:
        return SUBE
    if pies_por_minuto < -UMBRAL_TENDENCIA_FT_MIN:
        return BAJA
    return NIVELADO


def calcular_tendencia(identificador, avion):
    """
    Tendencia vertical del avión: SUBE, BAJA, NIVELADO o "" si no se puede saber.
        - Radar con BDS 6.0: su velocidad vertical, BAR (barométrica) o, si no viene, IVV (inercial).
        - Si no (y siempre en ADS-B): la variación del FL entre el mensaje más antiguo y el más
          reciente de los últimos SEGUNDOS_TENDENCIA, pasada a ft/min.
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
    """True si el avión entra en el tráfico: tiene TA y no es un blanco puro ni el transponder fijo."""
    if identificador[1].startswith("TN"):
        return False
    if filtros.es_blanco_puro(fila) or filtros.es_transponder_fijo(fila):
        return False
    return True


def nuevo_avion_trafico(nombre):
    """
    Datos de un avión del tráfico:
        estado:       EN_TIERRA, EN_VUELO o None (desconocido)
        candidato:    estado nuevo que aún no se ha confirmado (None si no hay)
        repeticiones: mensajes seguidos que han dicho el candidato
        estado_radar: lo que dijo el último STAT útil del radar (None si el radar no lo ve)
        nombre:       callsign o, si no hay, la TA
    """
    return {"estado": None, "candidato": None, "repeticiones": 0, "estado_radar": None, "nombre": nombre}


def actualizar_trafico(estado, identificador, fila):
    """Pone al día el avión del tráfico de este mensaje: su nombre y su estado en tierra / en vuelo."""
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
        avion_trafico["nombre"] = callsign      # el callsign puede llegar después que la TA
    observado = estado_observado(categoria, fila, avion_trafico)
    cambiar_estado(estado, avion_trafico, observado, fila, categoria, direccion_modo_s)


def estado_observado(categoria, fila, avion_trafico):
    """
    Lo que dice este mensaje sobre si el avión está en tierra o en vuelo: EN_TIERRA, EN_VUELO o
    None si no dice nada.
        - CAT048: según el STAT de I048/230. 4 a 7, o sin I048/230, no dicen nada.
        - CAT021: en vuelo (los de tierra ya se descartaron), salvo que el radar lo esté viendo
          con un STAT útil: entonces manda el radar y el mensaje ADS-B no dice nada.
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
    Máquina de estados de un avión del tráfico (desconocido, en tierra, en vuelo):
        - un mensaje que no dice nada (observado None) no cambia nada;
        - un mensaje que dice el estado actual anula el candidato que hubiera;
        - un mensaje que dice otro estado suma una repetición a ese candidato (o lo empieza);
        - con MENSAJES_PARA_CAMBIAR_ESTADO repeticiones seguidas, el candidato pasa a ser el estado.
    Un cambio de en tierra a en vuelo es un despegue y uno de en vuelo a en tierra, un aterrizaje.
    El primer estado (desde desconocido) también se confirma, pero no es un evento.
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
    """
    Añade un evento a la lista (y cuenta los despegues y aterrizajes). La lista guarda solo los
    últimos EVENTOS_GUARDADOS. Mientras se recalcula en silencio (al saltar de hora) no se anota nada.
    Cada evento: numero (orden), segundo (hora del mensaje que lo provoca), tipo, nombre (callsign o
    TA), sistema (Radar o ADS-B) y ta (para seleccionar el avión al pulsar el evento).
    """
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
    """True si el avión del tráfico con esa TA está confirmado en tierra (False si no es tráfico)."""
    if direccion_modo_s not in estado["trafico"]:
        return False
    return estado["trafico"][direccion_modo_s]["estado"] == EN_TIERRA


def texto_estado_avion(estado, identificador):
    """
    Estado del avión del mapa para el panel "Avión seleccionado": "en vuelo", "en tierra",
    "desconocido" (aún no hay mensajes que lo digan) o "-" si no es tráfico (blanco puro,
    transponder fijo o sin TA).
    """
    direccion_modo_s = identificador[1]
    if direccion_modo_s not in estado["trafico"]:
        return "-"
    estado_avion = estado["trafico"][direccion_modo_s]["estado"]
    if estado_avion is None:
        return "unknown"
    return estado_avion


def texto_tendencia(tendencia):
    """La flecha de la tendencia con su nombre ("↑ sube"), o "-" si no se sabe."""
    if tendencia == "":
        return "-"
    return tendencia + " " + NOMBRE_TENDENCIA[tendencia]


def eventos_nuevos(estado, ultimo_mostrado):
    """Eventos con número mayor que ultimo_mostrado (los que la ventana aún no ha puesto), del más antiguo al más nuevo."""
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
    Nivel al estilo de control aéreo, en cientos de pies y con la flecha de tendencia:
        - "A025" si hay altitud corregida por QNH (2.500 ft);
        - "FL045" si no la hay (FL 45, referido a la presión estándar);
        - "---" si no hay ninguna de las dos.
    Sin prefijo (con_prefijo False, en las etiquetas del mapa) queda solo "025" o "045".
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
    Filas de las listas del panel de tráfico, una por TA. Solo cuentan los sistemas de
    categorias_visibles (las que deja ver el selector Sistema). Devuelve (en_vuelo, en_tierra):
    diccionarios TA -> (nombre para ordenar, valores de la fila).
        en vuelo:  (callsign, nivel, visto por)   por ejemplo ("RYR1FB", "FL045↑", "Both")
        en tierra: (callsign,)    en tierra solo lo ve el radar: el ADS-B en tierra se descarta
    El nivel y la tendencia salen del radar si se ve por radar y, si no, del ADS-B.
    Los aviones de estado desconocido no están en ninguna de las dos.
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
    """Columna "Seen by" de la lista En vuelo: "Radar", "ADS-B" o "Both" si lo ven los dos."""
    if len(categorias) == 2:
        return VISTO_POR_AMBOS
    return NOMBRE_SISTEMA[categorias[0]]
