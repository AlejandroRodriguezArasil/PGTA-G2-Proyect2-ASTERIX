"""
Todo lo que se dibuja en el mapa de la simulación: iconos, marcadores con su etiqueta, estelas,
la zona del filtro y el texto del avión seleccionado. Qué aviones hay lo decide simulacion.py.
"""

import math

import PIL
import requests
import tkintermapview
from PIL import Image, ImageDraw, ImageEnhance, ImageOps, ImageTk

from funciones import filtros
from funciones import geo
from funciones import simulacion
from funciones.exportar_csv import valor
from interfaz import estilo

CATEGORIA_048 = 48
CATEGORIA_021 = 21

# La política de OpenStreetMap pide un User-Agent propio (bloquea el "TkinterMapView" de la
# librería), poner la atribución y no bajar teselas en masa. Aquí solo se piden las que se ven.
SERVIDOR_TESELAS = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
ZOOM_MAXIMO_SERVIDOR = 19
USER_AGENT = "ASTERIXDecoder-PGTA-G2/1.0 (UPC university project)"
ATRIBUCION_MAPA = "© OpenStreetMap contributors"
TIEMPO_MAXIMO_TESELA_S = 10

# Factores de Pillow para el mapa oscuro (1 = sin cambio)
CONTRASTE_MAPA_OSCURO = 0.85
BRILLO_MAPA_OSCURO = 0.9

# Tamaños en píxeles
TAMANO_SILUETA = 22
TAMANO_SILUETA_RESALTADA = 30
TAMANO_ANTENA = 26
TAMANO_ESTACION = 18
TAMANO_BLANCO_PURO = 10
TAMANO_BLANCO_PURO_RESALTADO = 14
TAMANO_LEYENDA = 16
ANCHO_ESTELA = 2
ANCHO_ZONA_FILTRO = 3
FUENTE_ETIQUETA = (estilo.FAMILIA, estilo.TAMANO_ETIQUETA_MAPA, "bold")

# Las siluetas giradas se crean una vez al principio, de 10 en 10 grados
PASO_GIRO_DEG = 10
NUMERO_GIROS = 36

# Para el rumbo de las siluetas ADS-B
DISTANCIA_MINIMA_RUMBO_M = 100
METROS_POR_GRADO = 111320       # 1 grado de latitud, aprox.

# Mitad derecha de la silueta mirando al norte, en un cuadrado de lado 1 (la y crece hacia abajo).
# La otra mitad se saca por simetría
SILUETA_MITAD_DERECHA = [
    (0.50, 0.03), (0.56, 0.11), (0.57, 0.37), (0.95, 0.58), (0.95, 0.66),
    (0.57, 0.55), (0.55, 0.80), (0.70, 0.90), (0.70, 0.95), (0.50, 0.91),
]
ESCALA_DIBUJO = 4       # se dibuja más grande y luego se reduce, así los bordes quedan suaves

# Según el TYP de I048/020
TIPO_BLANCO_PURO_ETIQUETA = {0: "No det.", 1: "PSR", 2: "SSR", 3: "PSR+SSR"}

# Los grados van pegados al número (41.43291°), las otras unidades con espacio
UNIDAD_GRADOS = "°"

ESQUINA_NOROESTE = (geo.LATITUD_MAXIMA_DEG, geo.LONGITUD_MINIMA_DEG)
ESQUINA_SURESTE = (geo.LATITUD_MINIMA_DEG, geo.LONGITUD_MAXIMA_DEG)


# =============================================================================
# Mapa que se identifica con nuestro User-Agent y que se puede oscurecer
# =============================================================================

def oscurecer_tesela(imagen):
    """
    Pasa una tesela de OpenStreetMap a la versión oscura: gris, invertida, con menos contraste
    y teñida de azul. Invertirla sin más quedaba como un negativo y los nombres deslumbraban.
    """
    gris = imagen.convert("L")
    invertida = ImageOps.invert(gris)
    # Bajando contraste y brillo los aviones son lo más claro del mapa
    suave = ImageEnhance.Contrast(invertida).enhance(CONTRASTE_MAPA_OSCURO)
    apagada = ImageEnhance.Brightness(suave).enhance(BRILLO_MAPA_OSCURO)
    return ImageOps.colorize(apagada, black=estilo.MAPA_OSCURO_NEGRO, mid=estilo.MAPA_OSCURO_MEDIO,
                             white=estilo.MAPA_OSCURO_BLANCO)


class MapaOSM(tkintermapview.TkinterMapView):
    """
    TkinterMapView con nuestro User-Agent (la librería lo tiene fijo en request_image, por eso
    se sobrescribe) y con modo oscuro. Las teselas oscuras se guardan ya oscurecidas en la caché.
    """

    def __init__(self, padre, **opciones):
        # Tiene que ir antes del super(): al crearse ya empieza a pedir teselas
        self.oscuro = False
        super().__init__(padre, **opciones)
        self.poner_teselas_vacias()

    def poner_teselas_vacias(self):
        """Cambia las teselas de relleno por unas del color del mapa (en oscuro se veían cuadros claros)."""
        if self.oscuro:
            vacia = Image.new("RGB", (self.tile_size, self.tile_size), estilo.TESELA_VACIA_OSCURO)
            no_encontrada = vacia
        else:
            vacia = Image.new("RGB", (self.tile_size, self.tile_size), estilo.TESELA_VACIA_CLARO)
            no_encontrada = Image.new("RGB", (self.tile_size, self.tile_size), estilo.TESELA_NO_ENCONTRADA_CLARO)
        self.empty_tile_image = ImageTk.PhotoImage(vacia)
        self.not_loaded_tile_image = ImageTk.PhotoImage(no_encontrada)

    def cambiar_modo(self, oscuro):
        """Cambia entre oscuro y claro; vacía la caché y vuelve a pedir las teselas."""
        self.oscuro = oscuro
        self.poner_teselas_vacias()
        self.tile_image_cache = {}
        self.draw_initial_array()

    def request_image(self, zoom, x, y, db_cursor=None):
        """
        Versión de request_image de tkintermapview 1.29 con nuestro User-Agent, un timeout y el
        oscurecido. Sin la parte de base de datos ni la capa superpuesta (no se usan).
        Se llama desde el hilo de teselas de la librería; las variables se llaman como en el original.
        """
        try:
            oscuro = self.oscuro        # si cambia el modo mientras llega, no se guarda
            url = self.tile_server.replace("{x}", str(x)).replace("{y}", str(y)).replace("{z}", str(zoom))
            respuesta = requests.get(url, stream=True, headers={"User-Agent": USER_AGENT},
                                     timeout=TIEMPO_MAXIMO_TESELA_S)
            image = Image.open(respuesta.raw)
            if oscuro:
                image = oscurecer_tesela(image)

            # Ventana cerrada o modo cambiado mientras llegaba
            if self.running and oscuro == self.oscuro:
                image_tk = ImageTk.PhotoImage(image)
            else:
                return self.empty_tile_image

            self.tile_image_cache[f"{zoom}{x}{y}"] = image_tk
            return image_tk

        except PIL.UnidentifiedImageError:
            # No existe tesela ahí
            self.tile_image_cache[f"{zoom}{x}{y}"] = self.empty_tile_image
            return self.empty_tile_image

        except requests.exceptions.ConnectionError:
            # Sin internet los aviones se siguen viendo
            return self.empty_tile_image

        except Exception:
            # Timeout u otro error, que el mapa siga funcionando
            return self.empty_tile_image


# =============================================================================
# Iconos
# =============================================================================

def puntos_silueta(tamano):
    """Polígono de la silueta entera, escalado a 'tamano' píxeles."""
    puntos = []
    for x, y in SILUETA_MITAD_DERECHA:
        puntos.append((x * tamano, y * tamano))
    # Mitad izquierda reflejada, de la cola a la nariz
    for x, y in reversed(SILUETA_MITAD_DERECHA[1:-1]):
        puntos.append(((1 - x) * tamano, y * tamano))
    return puntos


def dibujar_silueta(color, tamano, color_borde, ancho_borde):
    """Silueta mirando al norte con fondo transparente."""
    grande = tamano * ESCALA_DIBUJO
    imagen = Image.new("RGBA", (grande, grande), (0, 0, 0, 0))
    dibujo = ImageDraw.Draw(imagen)
    dibujo.polygon(puntos_silueta(grande), fill=color, outline=color_borde, width=ancho_borde * ESCALA_DIBUJO)
    return imagen.resize((tamano, tamano), Image.LANCZOS)


def dibujar_antena(color, tamano):
    """
    Antena del transponder fijo. Se pinta dos veces (gruesa y oscura, y encima fina) para que
    tenga borde y se vea en los dos mapas.
    """
    grande = tamano * ESCALA_DIBUJO
    imagen = Image.new("RGBA", (grande, grande), (0, 0, 0, 0))
    dibujo = ImageDraw.Draw(imagen)
    centro_x = grande / 2
    punta_y = grande * 0.32
    pasadas = [(estilo.BORDE_ICONO, 4 * ESCALA_DIBUJO), (color, 2 * ESCALA_DIBUJO)]
    for tono, grosor in pasadas:
        # mástil y patas
        dibujo.line([(centro_x, punta_y), (centro_x, grande * 0.95)], fill=tono, width=grosor)
        dibujo.line([(centro_x, grande * 0.55), (grande * 0.30, grande * 0.95)], fill=tono, width=grosor)
        dibujo.line([(centro_x, grande * 0.55), (grande * 0.70, grande * 0.95)], fill=tono, width=grosor)
        radio_punta = grande * 0.07 + grosor / 4
        dibujo.ellipse((centro_x - radio_punta, punta_y - radio_punta, centro_x + radio_punta,
                        punta_y + radio_punta), fill=tono)
        # ondas a los dos lados
        for radio in (grande * 0.18, grande * 0.32):
            caja = (centro_x - radio, punta_y - radio, centro_x + radio, punta_y + radio)
            dibujo.arc(caja, start=-45, end=45, fill=tono, width=grosor)
            dibujo.arc(caja, start=135, end=225, fill=tono, width=grosor)
    return imagen.resize((tamano, tamano), Image.LANCZOS)


def dibujar_triangulo(color, tamano):
    """Triángulo del radar de Barcelona."""
    imagen = Image.new("RGBA", (tamano, tamano), (0, 0, 0, 0))
    dibujo = ImageDraw.Draw(imagen)
    dibujo.polygon([(tamano / 2, 1), (tamano - 2, tamano - 2), (1, tamano - 2)],
                   fill=color, outline=estilo.BORDE_ICONO, width=2)
    return imagen


def dibujar_punto(color, tamano, color_borde, ancho_borde):
    """Punto para los blancos puros (no tienen rumbo)."""
    grande = tamano * ESCALA_DIBUJO
    imagen = Image.new("RGBA", (grande, grande), (0, 0, 0, 0))
    ImageDraw.Draw(imagen).ellipse((0, 0, grande - 1, grande - 1), fill=color, outline=color_borde,
                                   width=ancho_borde * ESCALA_DIBUJO)
    return imagen.resize((tamano, tamano), Image.LANCZOS)


def dibujar_icono_tabla(color, tamano):
    """Icono de la pestaña Datos."""
    grande = tamano * ESCALA_DIBUJO
    imagen = Image.new("RGBA", (grande, grande), (0, 0, 0, 0))
    dibujo = ImageDraw.Draw(imagen)
    grosor = 2 * ESCALA_DIBUJO
    dibujo.rounded_rectangle((grande * 0.1, grande * 0.15, grande * 0.9, grande * 0.85), radius=grande * 0.12,
                             outline=color, width=grosor)
    dibujo.line([(grande * 0.1, grande * 0.4), (grande * 0.9, grande * 0.4)], fill=color, width=grosor)
    dibujo.line([(grande * 0.5, grande * 0.4), (grande * 0.5, grande * 0.85)], fill=color, width=grosor)
    return imagen.resize((tamano, tamano), Image.LANCZOS)


def dibujar_icono_avion(color, tamano):
    """Icono de la pestaña Simulación, la silueta girada 45 grados."""
    return dibujar_silueta(color, tamano, color, 1).rotate(-45, resample=Image.BICUBIC)


def dibujar_rectangulo(color, tamano):
    """Rectángulo de la leyenda (zona del filtro)."""
    imagen = Image.new("RGBA", (tamano, tamano), (0, 0, 0, 0))
    ImageDraw.Draw(imagen).rectangle((1, 4, tamano - 2, tamano - 5), outline=color, width=2)
    return imagen


def dibujar_linea(color, tamano):
    """Línea de la estela para la leyenda."""
    imagen = Image.new("RGBA", (tamano, tamano), (0, 0, 0, 0))
    ImageDraw.Draw(imagen).line([(1, tamano / 2), (tamano - 2, tamano / 2)], fill=color, width=3)
    return imagen


def crear_iconos(app):
    """Crea todos los iconos al principio (hace falta que la ventana ya exista)."""
    colores = {CATEGORIA_048: estilo.RADAR, CATEGORIA_021: estilo.ADSB}
    app.siluetas = {}
    for categoria in colores:
        normal = dibujar_silueta(colores[categoria], TAMANO_SILUETA, estilo.BORDE_ICONO, 1)
        resaltada = dibujar_silueta(colores[categoria], TAMANO_SILUETA_RESALTADA, estilo.RESALTADO, 2)
        for giro in range(NUMERO_GIROS):
            # rotate() gira al revés que el rumbo, por eso el signo menos
            angulo = -giro * PASO_GIRO_DEG
            app.siluetas[(categoria, False, giro)] = ImageTk.PhotoImage(
                normal.rotate(angulo, resample=Image.BICUBIC))
            app.siluetas[(categoria, True, giro)] = ImageTk.PhotoImage(
                resaltada.rotate(angulo, resample=Image.BICUBIC))

    antena = dibujar_antena(estilo.TRANSPONDER_FIJO, TAMANO_ANTENA)
    estacion = dibujar_triangulo(estilo.ESTACION_RADAR, TAMANO_ESTACION)
    blanco_puro = dibujar_punto(estilo.BLANCO_PURO, TAMANO_BLANCO_PURO, estilo.BORDE_ICONO, 1)
    blanco_puro_resaltado = dibujar_punto(estilo.BLANCO_PURO, TAMANO_BLANCO_PURO_RESALTADO, estilo.RESALTADO, 2)
    app.iconos = {
        "transponder_fijo": ImageTk.PhotoImage(antena),
        "estacion": ImageTk.PhotoImage(estacion),
        "blanco_puro": ImageTk.PhotoImage(blanco_puro),
        "blanco_puro_resaltado": ImageTk.PhotoImage(blanco_puro_resaltado),
    }
    # El punto se centra en un cuadrado como el de los demás iconos de la leyenda
    punto_leyenda = Image.new("RGBA", (TAMANO_LEYENDA, TAMANO_LEYENDA), (0, 0, 0, 0))
    margen = (TAMANO_LEYENDA - TAMANO_BLANCO_PURO) // 2
    punto_leyenda.paste(blanco_puro, (margen, margen))
    app.imagenes_leyenda = {
        "radar": dibujar_silueta(estilo.RADAR, TAMANO_LEYENDA, estilo.BORDE_ICONO, 1),
        "adsb": dibujar_silueta(estilo.ADSB, TAMANO_LEYENDA, estilo.BORDE_ICONO, 1),
        "blanco_puro": punto_leyenda,
        "resaltado": dibujar_silueta(estilo.RADAR, TAMANO_LEYENDA, estilo.RESALTADO, 2),
        "transponder_fijo": dibujar_antena(estilo.TRANSPONDER_FIJO, TAMANO_LEYENDA),
        "estacion": dibujar_triangulo(estilo.ESTACION_RADAR, TAMANO_LEYENDA),
        "zona": dibujar_rectangulo(estilo.ZONA_FILTRO, TAMANO_LEYENDA),
        "estela": dibujar_linea(estilo.ESTELA_RADAR, TAMANO_LEYENDA),
    }


# =============================================================================
# Elementos fijos: servidor de teselas, zona del filtro y radar de BCN
# =============================================================================

def configurar_mapa(app):
    """Pone el servidor de teselas y dibuja la zona del filtro y el radar."""
    app.mapa.set_tile_server(SERVIDOR_TESELAS, max_zoom=ZOOM_MAXIMO_SERVIDOR)

    esquinas = [
        (geo.LATITUD_MAXIMA_DEG, geo.LONGITUD_MINIMA_DEG),
        (geo.LATITUD_MAXIMA_DEG, geo.LONGITUD_MAXIMA_DEG),
        (geo.LATITUD_MINIMA_DEG, geo.LONGITUD_MAXIMA_DEG),
        (geo.LATITUD_MINIMA_DEG, geo.LONGITUD_MINIMA_DEG),
    ]
    app.mapa.set_polygon(esquinas, outline_color=estilo.ZONA_FILTRO, fill_color=None, border_width=ANCHO_ZONA_FILTRO)

    latitud_radar = geo.RADAR_BCN.Lat * geo.GeoUtils.RADS2DEGS
    longitud_radar = geo.RADAR_BCN.Lon * geo.GeoUtils.RADS2DEGS
    app.mapa.set_marker(latitud_radar, longitud_radar, text="Radar BCN", icon=app.iconos["estacion"],
                        font=FUENTE_ETIQUETA, text_color=color_etiquetas(app))


def color_etiquetas(app):
    """Color de las etiquetas según el mapa."""
    if app.mapa.oscuro:
        return estilo.ETIQUETA_MAPA_OSCURO
    return estilo.ETIQUETA_MAPA_CLARO


def cambiar_aspecto_mapa(app, oscuro):
    """Cambia a mapa oscuro o claro y repinta las etiquetas que ya están."""
    app.mapa.cambiar_modo(oscuro)
    color = color_etiquetas(app)
    for marcador in app.mapa.canvas_marker_list:
        marcador.text_color = color
        if marcador.canvas_text is not None:
            app.mapa.canvas.itemconfig(marcador.canvas_text, fill=color)


def encuadrar_zona(app):
    """Centra el mapa en la zona del filtro geográfico."""
    app.mapa.fit_bounding_box(ESQUINA_NOROESTE, ESQUINA_SURESTE)


def centrar_en(app, latitud, longitud):
    """
    Centra el mapa sin cambiar el zoom, moviendo las esquinas (en coordenadas de tesela) y con
    draw_move, como al arrastrar. set_position rehace todas las teselas y con "Seguir" se notaba.
    """
    mapa = app.mapa
    destino_x, destino_y = tkintermapview.decimal_to_osm(latitud, longitud, round(mapa.zoom))
    centro_x = (mapa.upper_left_tile_pos[0] + mapa.lower_right_tile_pos[0]) / 2
    centro_y = (mapa.upper_left_tile_pos[1] + mapa.lower_right_tile_pos[1]) / 2
    mover_x = destino_x - centro_x
    mover_y = destino_y - centro_y
    mapa.upper_left_tile_pos = (mapa.upper_left_tile_pos[0] + mover_x, mapa.upper_left_tile_pos[1] + mover_y)
    mapa.lower_right_tile_pos = (mapa.lower_right_tile_pos[0] + mover_x, mapa.lower_right_tile_pos[1] + mover_y)
    mapa.check_map_border_crossing()
    mapa.draw_move()


def centrar_en_avion(app, avion):
    """Centra el mapa en el avión."""
    centrar_en(app, valor(avion["fila"], "LAT"), valor(avion["fila"], "LON"))


# =============================================================================
# Aviones
# =============================================================================

def sistema_visible(app, categoria):
    """Mira si el selector Sistema deja ver esa categoría."""
    sistema = app.selector_sistema.get()
    if sistema == "Radar":
        return categoria == CATEGORIA_048
    if sistema == "ADS-B":
        return categoria == CATEGORIA_021
    return True


def pareja_otro_sistema(identificador):
    """El mismo avión visto por el otro sistema (None si no tiene TA)."""
    categoria = identificador[0]
    nombre = identificador[1]
    if nombre.startswith("TN"):
        return None
    if categoria == CATEGORIA_048:
        return (CATEGORIA_021, nombre)
    return (CATEGORIA_048, nombre)


def avion_en_mapa_por_ta(app, direccion_modo_s):
    """Busca la silueta de esa TA en el mapa, primero la de radar. None si no está."""
    for categoria in (CATEGORIA_048, CATEGORIA_021):
        if (categoria, direccion_modo_s) in app.marcadores:
            return (categoria, direccion_modo_s)
    return None


def rumbo_para_dibujar(identificador, avion):
    """
    Rumbo para girar la silueta (grados desde el norte) o None. En radar es el de I048/200; en
    ADS-B no lo decodificamos, así que se saca de hacia dónde se ha movido (solo para dibujar).
    """
    if identificador[0] == CATEGORIA_048:
        return valor(avion["fila"], "I048_200_HDG_DEG")

    # Solo se recalcula si se ha movido 100 m o más, si no la silueta daba bandazos
    latitud, longitud = avion["estela"][-1]
    if avion["posicion_rumbo"] is None:
        avion["posicion_rumbo"] = (latitud, longitud)
        return None
    latitud_anterior, longitud_anterior = avion["posicion_rumbo"]
    # Aproximación plana, la longitud se multiplica por cos(latitud)
    hacia_el_este = (longitud - longitud_anterior) * math.cos(math.radians(latitud)) * METROS_POR_GRADO
    hacia_el_norte = (latitud - latitud_anterior) * METROS_POR_GRADO
    if math.hypot(hacia_el_este, hacia_el_norte) >= DISTANCIA_MINIMA_RUMBO_M:
        avion["rumbo_dibujo"] = math.degrees(math.atan2(hacia_el_este, hacia_el_norte)) % 360
        avion["posicion_rumbo"] = (latitud, longitud)
    return avion["rumbo_dibujo"]


def icono_de_avion(app, identificador, avion):
    """Antena, punto o silueta girada, según qué sea."""
    resaltado = identificador in app.aviones_resaltados
    if filtros.es_transponder_fijo(avion["fila"]):
        return app.iconos["transponder_fijo"]
    if filtros.es_blanco_puro(avion["fila"]):
        if resaltado:
            return app.iconos["blanco_puro_resaltado"]
        return app.iconos["blanco_puro"]

    rumbo = rumbo_para_dibujar(identificador, avion)
    if rumbo is None:
        giro = 0
    else:
        giro = int(round(rumbo / PASO_GIRO_DEG)) % NUMERO_GIROS
    return app.siluetas[(identificador[0], resaltado, giro)]


def texto_velocidad(fila):
    """GS en nudos (I048/200 o BDS 5.0). En ADS-B no hay y devuelve ""."""
    velocidad = valor(fila, "I048_200_GS_KT")
    if velocidad is None:
        velocidad = valor(fila, "BDS50_GS")
    if velocidad is None:
        return ""
    return str(int(round(velocidad)))


def lleva_etiqueta(app, identificador):
    """
    Si el avión lo ve también el radar, la etiqueta va solo en la silueta de radar (si no se
    pisan). En tierra no llevan, se amontonan en el aeropuerto, salvo el seleccionado.
    """
    direccion_modo_s = identificador[1]
    if identificador[0] == CATEGORIA_021 and (CATEGORIA_048, direccion_modo_s) in app.marcadores:
        return False
    if simulacion.esta_en_tierra(app.estado_simulacion, direccion_modo_s):
        return app.avion_seleccionado is not None and app.avion_seleccionado[1] == direccion_modo_s
    return True


def texto_etiqueta(app, identificador, avion):
    """
    Etiqueta tipo radar: callsign en la primera línea y nivel con tendencia y GS en la segunda
    ("045↑ 210"). Los blancos puros llevan tipo y Modo 3/A, p. ej. "PSR 45".
    """
    if app.casilla_etiquetas.get() == 0:
        return ""
    fila = avion["fila"]
    if filtros.es_transponder_fijo(fila):
        # Está en LEBL y su etiqueta se montaba con la de "Radar BCN", así que solo si está seleccionado
        if app.avion_seleccionado == identificador:
            return filtros.MODO_3A_TRANSPONDER_FIJO
        return ""
    if filtros.es_blanco_puro(fila):
        tipo = TIPO_BLANCO_PURO_ETIQUETA[valor(fila, "I048_020_TYP")]
        if valor(fila, "MODE3A") is not None:
            return tipo + " " + valor(fila, "MODE3A")
        return tipo + " " + str(valor(fila, "I048_161_TRACK_NUMBER"))
    if not lleva_etiqueta(app, identificador):
        return ""

    if valor(fila, "TI") is not None and valor(fila, "TI") != "":
        nombre = valor(fila, "TI")
    elif valor(fila, "TA") is not None:
        nombre = valor(fila, "TA")
    else:
        nombre = "TN " + str(valor(fila, "I048_161_TRACK_NUMBER"))
    segunda_linea = simulacion.texto_nivel(fila, avion["tendencia"], False)
    velocidad = texto_velocidad(fila)
    if velocidad != "":
        segunda_linea = segunda_linea + " " + velocidad
    return nombre + "\n" + segunda_linea


def dibujar_avion(app, identificador, avion):
    """Crea o mueve el marcador del avión, y su estela."""
    fila = avion["fila"]
    latitud = valor(fila, "LAT")
    longitud = valor(fila, "LON")
    etiqueta = texto_etiqueta(app, identificador, avion)
    icono = icono_de_avion(app, identificador, avion)

    if identificador in app.marcadores:
        marcador = app.marcadores[identificador]
        if marcador.icon is not icono:
            marcador.change_icon(icono)
        if marcador.text != etiqueta:
            marcador.text = etiqueta          # lo pinta el set_position de abajo
        marcador.set_position(latitud, longitud)
    else:
        marcador = app.mapa.set_marker(latitud, longitud, text=etiqueta, icon=icono,
                                       font=FUENTE_ETIQUETA, text_color=color_etiquetas(app),
                                       command=app.al_pulsar_avion, data=identificador)
        app.marcadores[identificador] = marcador

    dibujar_estela(app, identificador, avion)


def dibujar_estela(app, identificador, avion):
    """Dibuja o actualiza la estela."""
    if app.casilla_estelas.get() == 0 or len(avion["estela"]) < 2:
        return
    posiciones = list(avion["estela"])        # copia, la del avión se sigue modificando
    if identificador in app.estelas:
        app.estelas[identificador].set_position_list(posiciones)
    else:
        if identificador[0] == CATEGORIA_048:
            color = estilo.ESTELA_RADAR
        else:
            color = estilo.ESTELA_ADSB
        app.estelas[identificador] = app.mapa.set_path(posiciones, color=color, width=ANCHO_ESTELA)


def quitar_marcador(app, marcador):
    """
    Como marcador.delete() pero sin el canvas.update(), que repintaba toda la ventana
    en mitad de un salto.
    """
    if marcador in app.mapa.canvas_marker_list:
        app.mapa.canvas_marker_list.remove(marcador)
    app.mapa.canvas.delete(marcador.canvas_icon)
    app.mapa.canvas.delete(marcador.canvas_text)
    marcador.deleted = True


def borrar_estela(app, identificador):
    """Quita la estela de un avión."""
    if identificador in app.estelas:
        app.estelas[identificador].delete()
        del app.estelas[identificador]


def borrar_avion(app, identificador):
    """Borra marcador y estela."""
    if identificador in app.marcadores:
        quitar_marcador(app, app.marcadores[identificador])
        del app.marcadores[identificador]
    borrar_estela(app, identificador)


def borrar_todos(app):
    """Deja el mapa sin aviones."""
    identificadores = list(app.marcadores.keys()) + list(app.estelas.keys())
    for identificador in identificadores:
        borrar_avion(app, identificador)


def redibujar_todos(app, aviones):
    """
    Borra todo y vuelve a dibujar los aviones de los sistemas visibles. Las etiquetas se repasan
    al final porque al pintar la ADS-B todavía no se sabe si vendrá la de radar.
    """
    borrar_todos(app)
    for identificador in aviones:
        if sistema_visible(app, identificador[0]):
            dibujar_avion(app, identificador, aviones[identificador])
    actualizar_etiquetas(app, aviones)


def poner_etiqueta(app, identificador, aviones):
    """Recalcula la etiqueta y la cambia solo si es distinta."""
    marcador = app.marcadores[identificador]
    texto = texto_etiqueta(app, identificador, aviones[identificador])
    if marcador.text != texto:
        # Para ocultarla, "" y no None (con None tkintermapview ya no la vuelve a enseñar)
        marcador.set_text(texto)


def actualizar_etiquetas(app, aviones):
    """Repasa las etiquetas de todos los marcadores."""
    for identificador in app.marcadores:
        if identificador in aviones:
            poner_etiqueta(app, identificador, aviones)


def actualizar_etiquetas_de(app, aviones, direcciones):
    """
    Igual que la anterior pero solo para esas TA (las dos siluetas). Se usa en cada salto,
    porque la etiqueta puede pasar de una silueta a otra o quitarse al aterrizar.
    """
    for direccion_modo_s in direcciones:
        for categoria in (CATEGORIA_048, CATEGORIA_021):
            identificador = (categoria, direccion_modo_s)
            if identificador in app.marcadores and identificador in aviones:
                poner_etiqueta(app, identificador, aviones)


def actualizar_resaltado(app, aviones):
    """Resalta el avión seleccionado y su pareja del otro sistema."""
    app.aviones_resaltados = set()
    if app.avion_seleccionado is not None:
        app.aviones_resaltados.add(app.avion_seleccionado)
        pareja = pareja_otro_sistema(app.avion_seleccionado)
        if pareja is not None:
            app.aviones_resaltados.add(pareja)

    for identificador in app.marcadores:
        if identificador in aviones:
            marcador = app.marcadores[identificador]
            icono = icono_de_avion(app, identificador, aviones[identificador])
            if marcador.icon is not icono:
                marcador.change_icon(icono)


def categorias_visibles(app):
    """Tupla con las categorías visibles, p. ej. (48, 21)."""
    visibles = []
    for categoria in (CATEGORIA_048, CATEGORIA_021):
        if sistema_visible(app, categoria):
            visibles.append(categoria)
    return tuple(visibles)


def contar_en_mapa(app, aviones):
    """Cuenta (radar, ADS-B, blancos puros) en el mapa. El transponder fijo no cuenta."""
    radar = 0
    adsb = 0
    blancos_puros = 0
    for identificador in app.marcadores:
        if identificador not in aviones:
            continue
        fila = aviones[identificador]["fila"]
        if filtros.es_transponder_fijo(fila):
            continue
        if filtros.es_blanco_puro(fila):
            blancos_puros = blancos_puros + 1
        elif identificador[0] == CATEGORIA_048:
            radar = radar + 1
        else:
            adsb = adsb + 1
    return radar, adsb, blancos_puros


# =============================================================================
# Panel de información del avión seleccionado
# =============================================================================

def texto_numero(numero, decimales, unidad):
    """Número con punto decimal (la interfaz está en inglés) y unidad, o "-"."""
    if numero is None:
        return "-"
    texto = format(numero, "." + str(decimales) + "f")
    if unidad == UNIDAD_GRADOS:
        texto = texto + unidad
    elif unidad != "":
        texto = texto + " " + unidad
    return texto


def texto_o_guion(texto):
    """Pone "-" si no hay texto."""
    if texto is None or texto == "":
        return "-"
    return texto


def texto_informacion(avion, identificador, texto_estado):
    """Texto del panel del avión seleccionado, con los datos de su último mensaje."""
    fila = avion["fila"]
    lineas = []
    if filtros.es_transponder_fijo(fila):
        lineas.append("Fixed transponder (7777): ground")
        lineas.append("reference, always stationary.")
        lineas.append("")
    if identificador[0] == CATEGORIA_048:
        lineas.append("System          Radar (CAT048)")
    else:
        lineas.append("System          ADS-B (CAT021)")
    lineas.append("Status          " + texto_estado)
    lineas.append("Callsign        " + texto_o_guion(valor(fila, "TI")))
    lineas.append("Mode S address  " + texto_o_guion(valor(fila, "TA")))
    lineas.append("Mode 3/A        " + texto_o_guion(valor(fila, "MODE3A")))
    lineas.append("Flight level    " + texto_numero(valor(fila, "FL"), 2, ""))
    lineas.append("Corrected alt.  " + texto_numero(valor(fila, "ALT_CORRECTED_FT"), 0, "ft"))
    lineas.append("Vertical trend  " + simulacion.texto_tendencia(avion["tendencia"]))
    lineas.append("Latitude        " + texto_numero(valor(fila, "LAT"), 5, UNIDAD_GRADOS))
    lineas.append("Longitude       " + texto_numero(valor(fila, "LON"), 5, UNIDAD_GRADOS))
    lineas.append("Last message    " + str(valor(fila, "TIME")).replace(",", "."))
    lineas.append("")
    if identificador[0] == CATEGORIA_048:
        lineas.append("Speeds")
        lineas.append("  GS (BDS 5.0)      " + texto_numero(valor(fila, "BDS50_GS"), 0, "kt"))
        lineas.append("  GS (I048/200)     " + texto_numero(valor(fila, "I048_200_GS_KT"), 0, "kt"))
        lineas.append("  TAS               " + texto_numero(valor(fila, "BDS50_TAS"), 0, "kt"))
        lineas.append("  IAS               " + texto_numero(valor(fila, "BDS60_IAS"), 0, "kt"))
        lineas.append("  Mach              " + texto_numero(valor(fila, "BDS60_MACH"), 3, ""))
        lineas.append("Heading")
        lineas.append("  HDG (BDS 6.0)     " + texto_numero(valor(fila, "BDS60_HDG"), 1, UNIDAD_GRADOS))
        lineas.append("  TTA (BDS 5.0)     " + texto_numero(valor(fila, "BDS50_TTA"), 1, UNIDAD_GRADOS))
        lineas.append("  Heading I048/200  " + texto_numero(valor(fila, "I048_200_HDG_DEG"), 1, UNIDAD_GRADOS))
        lineas.append("Vertical rate")
        lineas.append("  BAR               " + texto_numero(valor(fila, "BDS60_BAR"), 0, "ft/min"))
        lineas.append("  IVV               " + texto_numero(valor(fila, "BDS60_IVV"), 0, "ft/min"))
    else:
        lineas.append("Speed and heading: not decoded in CAT021.")
    return "\n".join(lineas)
