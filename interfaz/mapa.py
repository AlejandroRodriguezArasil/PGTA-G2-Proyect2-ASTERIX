"""
mapa.py

Lo que se dibuja en el mapa de la pestaña Simulación (tkintermapview, teselas de OpenStreetMap):
    - el propio mapa (MapaOSM), que pide las teselas con nuestro User-Agent y, en modo oscuro, las oscurece
    - los iconos: siluetas de avión giradas según su rumbo, blancos puros, transponder fijo y
      radar de BCN; también los de las pestañas Datos y Simulación de la cabecera
    - la zona del filtro geográfico y el radar de Barcelona
    - el marcador de cada avión, su etiqueta tipo radar (callsign, nivel y velocidad) y su estela
    - mover el mapa para centrarlo en un avión (al pulsarlo en una lista o con "Seguir")
    - el texto del panel con la información del avión seleccionado

La lógica de la simulación (qué aviones hay y dónde) está en simulacion.py.
Cada avión tiene un solo marcador, que se crea cuando aparece, se mueve en cada
salto y se quita cuando caduca.
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

# Servidor de teselas de OpenStreetMap. Su política de uso
# (https://operations.osmfoundation.org/policies/tiles/) pide que cada aplicación se identifique
# con un User-Agent propio y bloquea los genéricos de las librerías, como el "TkinterMapView" de
# tkintermapview. También pide mostrar la atribución y no descargar teselas de forma masiva ni para
# usarlas sin conexión: aquí solo se descargan las que se ven y se guardan en memoria durante la sesión.
SERVIDOR_TESELAS = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
ZOOM_MAXIMO_SERVIDOR = 19
USER_AGENT = "ASTERIXDecoder-PGTA-G2/1.0 (UPC university project)"
ATRIBUCION_MAPA = "© OpenStreetMap contributors"
TIEMPO_MAXIMO_TESELA_S = 10     # si el servidor no responde en este tiempo, se deja de esperar esa tesela

# Mapa oscuro (oscurecer_tesela): factores de Pillow, donde 1 deja la imagen igual
CONTRASTE_MAPA_OSCURO = 0.85
BRILLO_MAPA_OSCURO = 0.9

# Tamaño de los iconos en píxeles
TAMANO_SILUETA = 22
TAMANO_SILUETA_RESALTADA = 30
TAMANO_ANTENA = 26
TAMANO_ESTACION = 18
TAMANO_BLANCO_PURO = 10
TAMANO_BLANCO_PURO_RESALTADO = 14
TAMANO_LEYENDA = 16           # la leyenda va dentro del mapa: iconos algo más pequeños
ANCHO_ESTELA = 2
ANCHO_ZONA_FILTRO = 3           # el límite del filtro geográfico, más grueso que las estelas
FUENTE_ETIQUETA = (estilo.FAMILIA, estilo.TAMANO_ETIQUETA_MAPA, "bold")

# Las siluetas se generan una sola vez, giradas cada PASO_GIRO_DEG grados, y se reutilizan
PASO_GIRO_DEG = 10
NUMERO_GIROS = 36

# Dirección de las siluetas ADS-B (ver rumbo_para_dibujar)
DISTANCIA_MINIMA_RUMBO_M = 100
METROS_POR_GRADO = 111320       # un grado de latitud, en metros (aproximado)

# Silueta de avión mirando al norte, en un cuadrado de lado 1 (x a la derecha, y hacia abajo).
# Solo la mitad derecha, de la nariz a la cola; la izquierda es simétrica.
SILUETA_MITAD_DERECHA = [
    (0.50, 0.03), (0.56, 0.11), (0.57, 0.37), (0.95, 0.58), (0.95, 0.66),
    (0.57, 0.55), (0.55, 0.80), (0.70, 0.90), (0.70, 0.95), (0.50, 0.91),
]
ESCALA_DIBUJO = 4       # se dibuja 4 veces más grande y se reduce, para que los bordes salgan suaves

# Etiqueta de los blancos puros según su TYP de I048/020 (CAT048 v1.31, §5.2.2), delante del
# Modo 3/A o, si no hay, del track number
TIPO_BLANCO_PURO_ETIQUETA = {0: "No det.", 1: "PSR", 2: "SSR", 3: "PSR+SSR"}

# Unidad de los ángulos del panel del avión: va pegada al número (41.43291°), las demás con un espacio
UNIDAD_GRADOS = "°"

# Esquinas de la zona del filtro geográfico
ESQUINA_NOROESTE = (geo.LATITUD_MAXIMA_DEG, geo.LONGITUD_MINIMA_DEG)
ESQUINA_SURESTE = (geo.LATITUD_MINIMA_DEG, geo.LONGITUD_MAXIMA_DEG)


# =============================================================================
# Mapa que se identifica con nuestro User-Agent y que se puede oscurecer
# =============================================================================

def oscurecer_tesela(imagen):
    """
    Convierte una tesela de OpenStreetMap (clara) en una oscura, del azul noche de la aplicación.
    Si solo se invirtiera, quedaría como un negativo fotográfico; con los pasos 3 a 5 queda en pocos
    tonos de azul, con la costa, las carreteras principales y los nombres a la vista, pero apagados
    para que no compitan con los aviones.
    """
    # 1. Gris: el color de OpenStreetMap (verde de los parques, naranja de las carreteras...) ya no hace falta
    gris = imagen.convert("L")
    # 2. Invertida: el suelo, que era casi blanco, pasa a casi negro, y los nombres, negros, pasan a claros
    invertida = ImageOps.invert(gris)
    # 3. Menos contraste, para que los nombres no deslumbren y el suelo no sea negro del todo
    suave = ImageEnhance.Contrast(invertida).enhance(CONTRASTE_MAPA_OSCURO)
    # 4. Un poco más oscura, para que los aviones sean lo más claro del mapa
    apagada = ImageEnhance.Brightness(suave).enhance(BRILLO_MAPA_OSCURO)
    # 5. Tono azul: cada gris pasa a un color entre MAPA_OSCURO_NEGRO, MAPA_OSCURO_MEDIO y MAPA_OSCURO_BLANCO
    return ImageOps.colorize(apagada, black=estilo.MAPA_OSCURO_NEGRO, mid=estilo.MAPA_OSCURO_MEDIO,
                             white=estilo.MAPA_OSCURO_BLANCO)


class MapaOSM(tkintermapview.TkinterMapView):
    """
    El mapa de tkintermapview, con dos cambios:
      - pide las teselas con nuestro User-Agent. tkintermapview 1.29 escribe el User-Agent
        "TkinterMapView" dentro de request_image y no permite cambiarlo, así que esta clase hija
        sobrescribe ese método;
      - en modo oscuro (self.oscuro), cada tesela se oscurece al descargarla (oscurecer_tesela). Se
        guarda ya oscurecida en la caché, así que se oscurece una sola vez y no frena la simulación.
    """

    def __init__(self, padre, **opciones):
        # Antes de crear el mapa: al crearse, tkintermapview ya empieza a pedir teselas
        self.oscuro = False             # al empezar, el mapa claro (el original de OpenStreetMap)
        super().__init__(padre, **opciones)
        self.poner_teselas_vacias()

    def poner_teselas_vacias(self):
        """
        Teselas que tkintermapview pone mientras una no ha llegado (empty_tile_image) o si no existe
        (not_loaded_tile_image). Las suyas son gris claro y blanca: en el mapa oscuro se verían como
        cuadros claros, así que se cambian por unas del color del mapa.
        """
        if self.oscuro:
            vacia = Image.new("RGB", (self.tile_size, self.tile_size), estilo.TESELA_VACIA_OSCURO)
            no_encontrada = vacia
        else:
            vacia = Image.new("RGB", (self.tile_size, self.tile_size), estilo.TESELA_VACIA_CLARO)
            no_encontrada = Image.new("RGB", (self.tile_size, self.tile_size), estilo.TESELA_NO_ENCONTRADA_CLARO)
        self.empty_tile_image = ImageTk.PhotoImage(vacia)
        self.not_loaded_tile_image = ImageTk.PhotoImage(no_encontrada)

    def cambiar_modo(self, oscuro):
        """Pasa a mapa oscuro o claro: vacía la caché de teselas y las vuelve a pedir todas."""
        self.oscuro = oscuro
        self.poner_teselas_vacias()
        self.tile_image_cache = {}
        self.draw_initial_array()

    def request_image(self, zoom, x, y, db_cursor=None):
        """
        Copia de TkinterMapView.request_image (tkintermapview 1.29, map_widget.py) con estos cambios:
          - la petición lleva USER_AGENT en lugar de "TkinterMapView";
          - la petición espera como mucho TIEMPO_MAXIMO_TESELA_S (el original no tenía límite);
          - en modo oscuro, la tesela se oscurece antes de mostrarla y guardarla;
          - se quita la lectura de teselas de una base de datos (es para usar el mapa sin conexión,
            que la política de OpenStreetMap no permite) y la capa superpuesta, que no se usa.
        Las variables tienen los nombres del original para poder compararlo.
        tkintermapview llama a este método desde su hilo de carga de teselas, no desde el de la ventana.
        """
        try:
            oscuro = self.oscuro        # el modo cuando se pide; si cambia mientras llega, no se guarda
            url = self.tile_server.replace("{x}", str(x)).replace("{y}", str(y)).replace("{z}", str(zoom))
            # El original ponía headers={"User-Agent": "TkinterMapView"} y no tenía timeout
            respuesta = requests.get(url, stream=True, headers={"User-Agent": USER_AGENT},
                                     timeout=TIEMPO_MAXIMO_TESELA_S)
            image = Image.open(respuesta.raw)
            if oscuro:
                image = oscurecer_tesela(image)

            # Si la ventana se ha cerrado, o se ha cambiado de mapa mientras llegaba, no se usa la imagen
            if self.running and oscuro == self.oscuro:
                image_tk = ImageTk.PhotoImage(image)
            else:
                return self.empty_tile_image

            # Caché en memoria, solo durante la sesión
            self.tile_image_cache[f"{zoom}{x}{y}"] = image_tk
            return image_tk

        except PIL.UnidentifiedImageError:
            # No hay tesela para esa posición
            self.tile_image_cache[f"{zoom}{x}{y}"] = self.empty_tile_image
            return self.empty_tile_image

        except requests.exceptions.ConnectionError:
            # Sin conexión: tesela vacía (gris); los aviones se siguen viendo
            return self.empty_tile_image

        except Exception:
            # Sin conexión, sin respuesta a tiempo u otro fallo: tesela vacía para que el mapa siga funcionando
            return self.empty_tile_image


# =============================================================================
# Iconos
# =============================================================================

def puntos_silueta(tamano):
    """Puntos del polígono de la silueta completa, escalados a un cuadrado de 'tamano' píxeles."""
    puntos = []
    for x, y in SILUETA_MITAD_DERECHA:
        puntos.append((x * tamano, y * tamano))
    # Mitad izquierda: los mismos puntos reflejados, de la cola a la nariz
    for x, y in reversed(SILUETA_MITAD_DERECHA[1:-1]):
        puntos.append(((1 - x) * tamano, y * tamano))
    return puntos


def dibujar_silueta(color, tamano, color_borde, ancho_borde):
    """Silueta de avión mirando al norte, con fondo transparente (imagen de Pillow)."""
    grande = tamano * ESCALA_DIBUJO
    imagen = Image.new("RGBA", (grande, grande), (0, 0, 0, 0))
    dibujo = ImageDraw.Draw(imagen)
    dibujo.polygon(puntos_silueta(grande), fill=color, outline=color_borde, width=ancho_borde * ESCALA_DIBUJO)
    return imagen.resize((tamano, tamano), Image.LANCZOS)


def dibujar_antena(color, tamano):
    """
    Icono del transponder fijo: una torre con dos ondas a cada lado. Se dibuja dos veces: primero
    más gruesa y del color del borde de los iconos, y encima, del color de la antena. Así lleva un
    contorno oscuro, como las siluetas, y se ve sobre el mapa oscuro y sobre el claro.
    """
    grande = tamano * ESCALA_DIBUJO
    imagen = Image.new("RGBA", (grande, grande), (0, 0, 0, 0))
    dibujo = ImageDraw.Draw(imagen)
    centro_x = grande / 2
    punta_y = grande * 0.32
    pasadas = [(estilo.BORDE_ICONO, 4 * ESCALA_DIBUJO), (color, 2 * ESCALA_DIBUJO)]
    for tono, grosor in pasadas:
        # Torre: mástil y patas
        dibujo.line([(centro_x, punta_y), (centro_x, grande * 0.95)], fill=tono, width=grosor)
        dibujo.line([(centro_x, grande * 0.55), (grande * 0.30, grande * 0.95)], fill=tono, width=grosor)
        dibujo.line([(centro_x, grande * 0.55), (grande * 0.70, grande * 0.95)], fill=tono, width=grosor)
        radio_punta = grande * 0.07 + grosor / 4
        dibujo.ellipse((centro_x - radio_punta, punta_y - radio_punta, centro_x + radio_punta,
                        punta_y + radio_punta), fill=tono)
        # Ondas: arcos a la derecha (de -45° a 45°) y a la izquierda (de 135° a 225°)
        for radio in (grande * 0.18, grande * 0.32):
            caja = (centro_x - radio, punta_y - radio, centro_x + radio, punta_y + radio)
            dibujo.arc(caja, start=-45, end=45, fill=tono, width=grosor)
            dibujo.arc(caja, start=135, end=225, fill=tono, width=grosor)
    return imagen.resize((tamano, tamano), Image.LANCZOS)


def dibujar_triangulo(color, tamano):
    """Triángulo con borde blanco: la estación radar de Barcelona."""
    imagen = Image.new("RGBA", (tamano, tamano), (0, 0, 0, 0))
    dibujo = ImageDraw.Draw(imagen)
    dibujo.polygon([(tamano / 2, 1), (tamano - 2, tamano - 2), (1, tamano - 2)],
                   fill=color, outline=estilo.BORDE_ICONO, width=2)
    return imagen


def dibujar_punto(color, tamano, color_borde, ancho_borde):
    """Punto redondo con borde: los blancos puros, que no tienen silueta ni rumbo."""
    grande = tamano * ESCALA_DIBUJO
    imagen = Image.new("RGBA", (grande, grande), (0, 0, 0, 0))
    ImageDraw.Draw(imagen).ellipse((0, 0, grande - 1, grande - 1), fill=color, outline=color_borde,
                                   width=ancho_borde * ESCALA_DIBUJO)
    return imagen.resize((tamano, tamano), Image.LANCZOS)


def dibujar_icono_tabla(color, tamano):
    """Icono de la pestaña Datos: una tabla con su fila de cabecera y una columna."""
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
    """Icono de la pestaña Simulación: la misma silueta de los aviones del mapa, girada hacia el noreste."""
    return dibujar_silueta(color, tamano, color, 1).rotate(-45, resample=Image.BICUBIC)


def dibujar_rectangulo(color, tamano):
    """Rectángulo vacío: la zona del filtro geográfico, para la leyenda."""
    imagen = Image.new("RGBA", (tamano, tamano), (0, 0, 0, 0))
    ImageDraw.Draw(imagen).rectangle((1, 4, tamano - 2, tamano - 5), outline=color, width=2)
    return imagen


def dibujar_linea(color, tamano):
    """Línea horizontal: la estela, para la leyenda."""
    imagen = Image.new("RGBA", (tamano, tamano), (0, 0, 0, 0))
    ImageDraw.Draw(imagen).line([(1, tamano / 2), (tamano - 2, tamano / 2)], fill=color, width=3)
    return imagen


def crear_iconos(app):
    """
    Crea todos los iconos una sola vez, con la ventana ya creada.
    Guarda: app.siluetas (categoría, resaltada, giro) -> imagen para el mapa,
            app.iconos (iconos fijos del mapa) y app.imagenes_leyenda (imágenes de Pillow para la leyenda).
    """
    colores = {CATEGORIA_048: estilo.RADAR, CATEGORIA_021: estilo.ADSB}
    app.siluetas = {}
    for categoria in colores:
        normal = dibujar_silueta(colores[categoria], TAMANO_SILUETA, estilo.BORDE_ICONO, 1)
        resaltada = dibujar_silueta(colores[categoria], TAMANO_SILUETA_RESALTADA, estilo.RESALTADO, 2)
        for giro in range(NUMERO_GIROS):
            # rotate() gira en sentido antihorario y el rumbo se mide en sentido horario
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
    # El punto de la leyenda va centrado en un cuadrado del tamaño de los demás iconos
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
    """Elige el servidor de teselas (OpenStreetMap) y dibuja la zona del filtro y el radar de BCN."""
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
    """Color de las etiquetas del mapa: claro sobre el mapa oscuro y oscuro sobre el claro."""
    if app.mapa.oscuro:
        return estilo.ETIQUETA_MAPA_OSCURO
    return estilo.ETIQUETA_MAPA_CLARO


def cambiar_aspecto_mapa(app, oscuro):
    """
    Selector Mapa: pasa al mapa oscuro o al claro (MapaOSM.cambiar_modo) y cambia el color de las
    etiquetas que ya están dibujadas (los aviones y "Radar BCN").
    """
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
    Centra el mapa en esa posición sin cambiar el zoom.
    tkintermapview guarda qué parte del mundo se ve con las esquinas superior izquierda e inferior
    derecha, en coordenadas de tesela. Aquí se desplazan las dos esquinas lo que haga falta para que
    el centro quede en la posición y se redibuja con draw_move, lo mismo que hace la librería al
    arrastrar el mapa con el ratón. set_position también centraría, pero vuelve a crear todas las
    teselas y, con "Seguir" a x60, se notaría.
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
    """Centra el mapa en la última posición del avión."""
    centrar_en(app, valor(avion["fila"], "LAT"), valor(avion["fila"], "LON"))


# =============================================================================
# Aviones
# =============================================================================

def sistema_visible(app, categoria):
    """True si el selector Radar / ADS-B / Ambos permite ver esa categoría."""
    sistema = app.selector_sistema.get()
    if sistema == "Radar":
        return categoria == CATEGORIA_048
    if sistema == "ADS-B":
        return categoria == CATEGORIA_021
    return True


def pareja_otro_sistema(identificador):
    """
    El mismo avión en el otro sistema: misma TA y la otra categoría.
    Un avión identificado por track number (sin TA) no tiene pareja: devuelve None.
    """
    categoria = identificador[0]
    nombre = identificador[1]
    if nombre.startswith("TN"):
        return None
    if categoria == CATEGORIA_048:
        return (CATEGORIA_021, nombre)
    return (CATEGORIA_048, nombre)


def avion_en_mapa_por_ta(app, direccion_modo_s):
    """
    Silueta del mapa de un avión del tráfico (por su TA): la de radar si está dibujada y, si no,
    la de ADS-B. Devuelve su identificador, o None si el avión no está en el mapa (ha desaparecido
    o el selector Sistema oculta los sistemas que lo ven).
    """
    for categoria in (CATEGORIA_048, CATEGORIA_021):
        if (categoria, direccion_modo_s) in app.marcadores:
            return (categoria, direccion_modo_s)
    return None


def rumbo_para_dibujar(identificador, avion):
    """
    Rumbo en grados (0 = norte, sentido horario) con el que se gira la silueta, o None si no se sabe.
        - Radar: el rumbo de I048/200.
        - ADS-B: no se decodifica su rumbo (el enunciado no pide esos DI), así que se usa la
          dirección en la que se ha movido. Es solo para dibujar: no va al CSV ni al panel.
    """
    if identificador[0] == CATEGORIA_048:
        return valor(avion["fila"], "I048_200_HDG_DEG")

    # La dirección solo se recalcula cuando el avión se ha movido al menos DISTANCIA_MINIMA_RUMBO_M
    # desde la posición con la que se calculó la última vez; si no, se mantiene la anterior. Así
    # dos posiciones casi iguales no hacen que la silueta dé bandazos.
    latitud, longitud = avion["estela"][-1]
    if avion["posicion_rumbo"] is None:
        avion["posicion_rumbo"] = (latitud, longitud)
        return None
    latitud_anterior, longitud_anterior = avion["posicion_rumbo"]
    # Distancia aproximada en un plano local: la diferencia de longitud se multiplica por cos(latitud)
    hacia_el_este = (longitud - longitud_anterior) * math.cos(math.radians(latitud)) * METROS_POR_GRADO
    hacia_el_norte = (latitud - latitud_anterior) * METROS_POR_GRADO
    if math.hypot(hacia_el_este, hacia_el_norte) >= DISTANCIA_MINIMA_RUMBO_M:
        avion["rumbo_dibujo"] = math.degrees(math.atan2(hacia_el_este, hacia_el_norte)) % 360
        avion["posicion_rumbo"] = (latitud, longitud)
    return avion["rumbo_dibujo"]


def icono_de_avion(app, identificador, avion):
    """
    Icono del avión: la antena si es el transponder fijo; un punto gris si es un blanco puro
    (no tiene silueta ni rumbo); si no, su silueta girada según su rumbo.
    """
    resaltado = identificador in app.aviones_resaltados
    if filtros.es_transponder_fijo(avion["fila"]):
        return app.iconos["transponder_fijo"]
    if filtros.es_blanco_puro(avion["fila"]):
        if resaltado:
            return app.iconos["blanco_puro_resaltado"]
        return app.iconos["blanco_puro"]

    rumbo = rumbo_para_dibujar(identificador, avion)
    if rumbo is None:
        giro = 0        # sin rumbo, la silueta se dibuja sin girar
    else:
        giro = int(round(rumbo / PASO_GIRO_DEG)) % NUMERO_GIROS
    return app.siluetas[(identificador[0], resaltado, giro)]


def texto_velocidad(fila):
    """
    Velocidad respecto al suelo (GS) en nudos, sin decimales: la de I048/200 o, si no viene, la
    del BDS 5.0. En ADS-B no hay, porque no se decodifica: devuelve "".
    """
    velocidad = valor(fila, "I048_200_GS_KT")
    if velocidad is None:
        velocidad = valor(fila, "BDS50_GS")
    if velocidad is None:
        return ""
    return str(int(round(velocidad)))


def lleva_etiqueta(app, identificador):
    """
    False si este avión del tráfico se dibuja sin etiqueta:
        - si también se ve por radar, solo lleva etiqueta la silueta de radar (las dos etiquetas
          casi se superponen y no se leería ninguna), así que la de ADS-B va sin texto;
        - los aviones en tierra van sin etiqueta, porque en el aeropuerto se amontonan y lo tapan;
          el avión seleccionado sí la lleva.
    """
    direccion_modo_s = identificador[1]
    if identificador[0] == CATEGORIA_021 and (CATEGORIA_048, direccion_modo_s) in app.marcadores:
        return False
    if simulacion.esta_en_tierra(app.estado_simulacion, direccion_modo_s):
        return app.avion_seleccionado is not None and app.avion_seleccionado[1] == direccion_modo_s
    return True


def texto_etiqueta(app, identificador, avion):
    """
    Etiqueta del marcador, como el bloque de datos de una pantalla radar de control:
        línea 1: callsign o, si no hay, la TA (o el track number si tampoco hay TA)
        línea 2: nivel en cientos de pies con su tendencia y la velocidad GS, por ejemplo "045↑ 210".
                 El nivel es el de simulacion.texto_nivel sin el prefijo A o FL, para que sea corto.
    Los blancos puros llevan su tipo y el Modo 3/A o, si no hay, el track number (por ejemplo
    "PSR 45"). El transponder fijo solo lleva su Modo 3/A (7777), y solo si está seleccionado.
    Vacía si las etiquetas están ocultas o si el avión no lleva etiqueta (lleva_etiqueta).
    """
    if app.casilla_etiquetas.get() == 0:
        return ""
    fila = avion["fila"]
    if filtros.es_transponder_fijo(fila):
        # Sin etiqueta, salvo si está seleccionado: está en LEBL, junto a "Radar BCN" y a los aviones que
        # despegan, y su etiqueta se montaba con las de ellos (la leyenda explica la antena)
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
    """
    Crea el marcador del avión si aún no lo tiene o lo mueve a su última posición. También su estela.
    El texto de la etiqueta solo se cambia si es distinto del que ya tenía.
    """
    fila = avion["fila"]
    latitud = valor(fila, "LAT")
    longitud = valor(fila, "LON")
    etiqueta = texto_etiqueta(app, identificador, avion)
    icono = icono_de_avion(app, identificador, avion)

    if identificador in app.marcadores:
        marcador = app.marcadores[identificador]
        if marcador.icon is not icono:
            marcador.change_icon(icono)       # solo cuando cambia el giro o el resaltado
        if marcador.text != etiqueta:
            marcador.text = etiqueta          # se dibuja con el set_position de la línea siguiente
        marcador.set_position(latitud, longitud)
    else:
        marcador = app.mapa.set_marker(latitud, longitud, text=etiqueta, icon=icono,
                                       font=FUENTE_ETIQUETA, text_color=color_etiquetas(app),
                                       command=app.al_pulsar_avion, data=identificador)
        app.marcadores[identificador] = marcador

    dibujar_estela(app, identificador, avion)


def dibujar_estela(app, identificador, avion):
    """Línea con las últimas posiciones del avión. Hacen falta al menos 2 posiciones."""
    if app.casilla_estelas.get() == 0 or len(avion["estela"]) < 2:
        return
    posiciones = list(avion["estela"])        # copia: la lista del avión sigue cambiando
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
    Quita un marcador del mapa. Es lo mismo que marcador.delete() de tkintermapview, pero sin su
    canvas.update(), que redibuja toda la ventana y atiende clics pendientes en mitad de un salto.
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
    """Quita del mapa el marcador y la estela de un avión."""
    if identificador in app.marcadores:
        quitar_marcador(app, app.marcadores[identificador])
        del app.marcadores[identificador]
    borrar_estela(app, identificador)


def borrar_todos(app):
    """Quita del mapa todos los aviones y sus estelas."""
    identificadores = list(app.marcadores.keys()) + list(app.estelas.keys())
    for identificador in identificadores:
        borrar_avion(app, identificador)


def redibujar_todos(app, aviones):
    """
    Quita todos los aviones y vuelve a dibujar los que están a la vista y son de un sistema visible.
    Al final se repasan las etiquetas: al dibujar una silueta ADS-B aún no se sabe si después
    se dibujará la de radar del mismo avión.
    """
    borrar_todos(app)
    for identificador in aviones:
        if sistema_visible(app, identificador[0]):
            dibujar_avion(app, identificador, aviones[identificador])
    actualizar_etiquetas(app, aviones)


def poner_etiqueta(app, identificador, aviones):
    """Vuelve a calcular la etiqueta de un marcador y solo la cambia si es distinta."""
    marcador = app.marcadores[identificador]
    texto = texto_etiqueta(app, identificador, aviones[identificador])
    if marcador.text != texto:
        # Para ocultarla se pone texto vacío: con None, tkintermapview no la vuelve a mostrar
        marcador.set_text(texto)


def actualizar_etiquetas(app, aviones):
    """Repasa la etiqueta de todos los marcadores (casilla Etiquetas o después de redibujar)."""
    for identificador in app.marcadores:
        if identificador in aviones:
            poner_etiqueta(app, identificador, aviones)


def actualizar_etiquetas_de(app, aviones, direcciones):
    """
    Repasa la etiqueta de las dos siluetas (radar y ADS-B) de los aviones con esas TA. Se usa en
    cada salto con los aviones que han cambiado o desaparecido: si una silueta de radar aparece o
    desaparece, la etiqueta pasa de una silueta a la otra; si el avión aterriza o despega, se quita
    o se pone. Así solo se tocan las etiquetas de esos aviones, y solo si cambia su texto.
    """
    for direccion_modo_s in direcciones:
        for categoria in (CATEGORIA_048, CATEGORIA_021):
            identificador = (categoria, direccion_modo_s)
            if identificador in app.marcadores and identificador in aviones:
                poner_etiqueta(app, identificador, aviones)


def actualizar_resaltado(app, aviones):
    """
    Resalta el avión seleccionado y, si está en el mapa, el mismo avión visto por el otro
    sistema (misma TA). Solo cambia el icono de los marcadores que lo necesitan.
    """
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
    """Categorías que deja ver el selector Sistema: (48, 21), (48,) o (21,)."""
    visibles = []
    for categoria in (CATEGORIA_048, CATEGORIA_021):
        if sistema_visible(app, categoria):
            visibles.append(categoria)
    return tuple(visibles)


def contar_en_mapa(app, aviones):
    """
    Devuelve (radar, ADS-B, blancos puros) dibujados en el mapa. Los blancos puros no se
    cuentan como radar y el transponder fijo no se cuenta.
    """
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
    """Número con punto decimal (la interfaz va en inglés) y su unidad, o "-" si no hay dato."""
    if numero is None:
        return "-"
    texto = format(numero, "." + str(decimales) + "f")
    if unidad == UNIDAD_GRADOS:
        texto = texto + unidad
    elif unidad != "":
        texto = texto + " " + unidad
    return texto


def texto_o_guion(texto):
    """El texto tal cual, o "-" si no hay dato."""
    if texto is None or texto == "":
        return "-"
    return texto


def texto_informacion(avion, identificador, texto_estado):
    """
    Texto del panel con los datos del último mensaje del avión seleccionado. Si el avión también
    está en el mapa por el otro sistema lo indica el selector Radar / ADS-B del panel, no este texto.
    texto_estado es el de simulacion.texto_estado_avion ("airborne", "on ground"...).
    La hora del mensaje se guarda con coma decimal (la del CSV); aquí se escribe con punto.
    """
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
