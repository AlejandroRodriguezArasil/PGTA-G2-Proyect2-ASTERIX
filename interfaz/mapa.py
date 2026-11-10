"""
mapa.py

Lo que se dibuja en el mapa de la pestaña Simulación (tkintermapview, teselas de OpenStreetMap):
    - el propio mapa (MapaOSM), que pide las teselas con nuestro User-Agent
    - los iconos: siluetas de avión giradas según su rumbo, blancos puros, transponder fijo y
      radar de BCN; también los de las pestañas Datos y Simulación de la cabecera
    - la zona del filtro geográfico y el radar de Barcelona
    - el marcador de cada avión, su etiqueta y su estela
    - el texto del panel con la información del avión seleccionado

La lógica de la simulación (qué aviones hay y dónde) está en simulacion.py.
Cada avión tiene un solo marcador, que se crea cuando aparece, se mueve en cada
salto y se quita cuando caduca.
"""

import math

import PIL
import requests
import tkintermapview
from PIL import Image, ImageDraw, ImageTk

from funciones import filtros
from funciones import geo
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
USER_AGENT = "DecodificadorASTERIX-PGTA-G2/1.0 (proyecto universitario UPC)"
ATRIBUCION_MAPA = "© OpenStreetMap contributors"
TIEMPO_MAXIMO_TESELA_S = 10     # si el servidor no responde en este tiempo, se deja de esperar esa tesela

# Tamaño de los iconos en píxeles
TAMANO_SILUETA = 22
TAMANO_SILUETA_RESALTADA = 30
TAMANO_ANTENA = 26
TAMANO_ESTACION = 18
TAMANO_BLANCO_PURO = 10
TAMANO_BLANCO_PURO_RESALTADO = 14
TAMANO_LEYENDA = 20
ANCHO_ESTELA = 2
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
TIPO_BLANCO_PURO_ETIQUETA = {0: "Sin det.", 1: "PSR", 2: "SSR", 3: "PSR+SSR"}

# Esquinas de la zona del filtro geográfico
ESQUINA_NOROESTE = (geo.LATITUD_MAXIMA_DEG, geo.LONGITUD_MINIMA_DEG)
ESQUINA_SURESTE = (geo.LATITUD_MINIMA_DEG, geo.LONGITUD_MAXIMA_DEG)


# =============================================================================
# Mapa que se identifica con nuestro User-Agent
# =============================================================================

class MapaOSM(tkintermapview.TkinterMapView):
    """
    El mapa de tkintermapview, pero pidiendo las teselas con nuestro User-Agent.
    tkintermapview 1.29 escribe el User-Agent "TkinterMapView" dentro de request_image y no
    permite cambiarlo, así que esta clase hija sobrescribe ese método.
    """

    def request_image(self, zoom, x, y, db_cursor=None):
        """
        Copia de TkinterMapView.request_image (tkintermapview 1.29, map_widget.py) con estos cambios:
          - la petición lleva USER_AGENT en lugar de "TkinterMapView";
          - la petición espera como mucho TIEMPO_MAXIMO_TESELA_S (el original no tenía límite);
          - se quita la lectura de teselas de una base de datos (es para usar el mapa sin conexión,
            que la política de OpenStreetMap no permite) y la capa superpuesta, que no se usa.
        Las variables tienen los nombres del original para poder compararlo.
        """
        try:
            url = self.tile_server.replace("{x}", str(x)).replace("{y}", str(y)).replace("{z}", str(zoom))
            # El original ponía headers={"User-Agent": "TkinterMapView"} y no tenía timeout
            respuesta = requests.get(url, stream=True, headers={"User-Agent": USER_AGENT},
                                     timeout=TIEMPO_MAXIMO_TESELA_S)
            image = Image.open(respuesta.raw)

            # Si la ventana se ha cerrado mientras tanto, no se usa la imagen
            if self.running:
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
    """Icono del transponder fijo: una torre con dos ondas a cada lado."""
    grande = tamano * ESCALA_DIBUJO
    imagen = Image.new("RGBA", (grande, grande), (0, 0, 0, 0))
    dibujo = ImageDraw.Draw(imagen)
    grosor = 2 * ESCALA_DIBUJO
    centro_x = grande / 2
    punta_y = grande * 0.32
    # Torre: mástil y patas
    dibujo.line([(centro_x, punta_y), (centro_x, grande * 0.95)], fill=color, width=grosor)
    dibujo.line([(centro_x, grande * 0.55), (grande * 0.30, grande * 0.95)], fill=color, width=grosor)
    dibujo.line([(centro_x, grande * 0.55), (grande * 0.70, grande * 0.95)], fill=color, width=grosor)
    radio_punta = grande * 0.07
    dibujo.ellipse((centro_x - radio_punta, punta_y - radio_punta, centro_x + radio_punta, punta_y + radio_punta),
                   fill=color)
    # Ondas: arcos a la derecha (de -45° a 45°) y a la izquierda (de 135° a 225°)
    for radio in (grande * 0.18, grande * 0.32):
        caja = (centro_x - radio, punta_y - radio, centro_x + radio, punta_y + radio)
        dibujo.arc(caja, start=-45, end=45, fill=color, width=grosor)
        dibujo.arc(caja, start=135, end=225, fill=color, width=grosor)
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
    app.mapa.set_polygon(esquinas, outline_color=estilo.ZONA_FILTRO, fill_color=None, border_width=2)

    latitud_radar = geo.RADAR_BCN.Lat * geo.GeoUtils.RADS2DEGS
    longitud_radar = geo.RADAR_BCN.Lon * geo.GeoUtils.RADS2DEGS
    app.mapa.set_marker(latitud_radar, longitud_radar, text="Radar BCN", icon=app.iconos["estacion"],
                        font=FUENTE_ETIQUETA, text_color=estilo.ESTACION_RADAR)


def encuadrar_zona(app):
    """Centra el mapa en la zona del filtro geográfico."""
    app.mapa.fit_bounding_box(ESQUINA_NOROESTE, ESQUINA_SURESTE)


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


def texto_etiqueta(app, fila):
    """
    Etiqueta del marcador: el callsign o, si no hay, la TA. Los blancos puros llevan su tipo y
    el Modo 3/A o, si no hay, el track number (por ejemplo "PSR 45"). Vacía si las etiquetas están ocultas.
    """
    if app.casilla_etiquetas.get() == 0:
        return ""
    if filtros.es_transponder_fijo(fila):
        return "Transponder fijo (7777)"
    if filtros.es_blanco_puro(fila):
        tipo = TIPO_BLANCO_PURO_ETIQUETA[valor(fila, "I048_020_TYP")]
        if valor(fila, "MODE3A") is not None:
            return tipo + " " + valor(fila, "MODE3A")
        return tipo + " " + str(valor(fila, "I048_161_TRACK_NUMBER"))
    if valor(fila, "TI") is not None and valor(fila, "TI") != "":
        return valor(fila, "TI")
    if valor(fila, "TA") is not None:
        return valor(fila, "TA")
    return "TN " + str(valor(fila, "I048_161_TRACK_NUMBER"))


def dibujar_avion(app, identificador, avion):
    """Crea el marcador del avión si aún no lo tiene o lo mueve a su última posición. También su estela."""
    fila = avion["fila"]
    latitud = valor(fila, "LAT")
    longitud = valor(fila, "LON")
    etiqueta = texto_etiqueta(app, fila)
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
                                       font=FUENTE_ETIQUETA, text_color=estilo.TEXTO,
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
    """Quita todos los aviones y vuelve a dibujar los que están a la vista y son de un sistema visible."""
    borrar_todos(app)
    for identificador in aviones:
        if sistema_visible(app, identificador[0]):
            dibujar_avion(app, identificador, aviones[identificador])


def actualizar_etiquetas(app, aviones):
    """Muestra u oculta la etiqueta de todos los marcadores, según la casilla Etiquetas."""
    for identificador in app.marcadores:
        if identificador in aviones:
            # Para ocultarla se pone texto vacío: con None, tkintermapview no la vuelve a mostrar
            app.marcadores[identificador].set_text(texto_etiqueta(app, aviones[identificador]["fila"]))


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
    """Número con coma decimal y su unidad, o "-" si no hay dato."""
    if numero is None:
        return "-"
    texto = format(numero, "." + str(decimales) + "f").replace(".", ",")
    if unidad != "":
        texto = texto + " " + unidad
    return texto


def texto_o_guion(texto):
    """El texto tal cual, o "-" si no hay dato."""
    if texto is None or texto == "":
        return "-"
    return texto


def texto_informacion(avion, identificador):
    """
    Texto del panel con los datos del último mensaje del avión seleccionado. Si el avión también
    está en el mapa por el otro sistema lo indica el selector Radar / ADS-B del panel, no este texto.
    """
    fila = avion["fila"]
    lineas = []
    if filtros.es_transponder_fijo(fila):
        lineas.append("Transponder fijo (7777): referencia")
        lineas.append("en tierra, siempre quieto.")
        lineas.append("")
    if identificador[0] == CATEGORIA_048:
        lineas.append("Sistema     Radar (CAT048)")
    else:
        lineas.append("Sistema     ADS-B (CAT021)")
    lineas.append("Callsign    " + texto_o_guion(valor(fila, "TI")))
    lineas.append("TA          " + texto_o_guion(valor(fila, "TA")))
    lineas.append("Modo 3/A    " + texto_o_guion(valor(fila, "MODE3A")))
    lineas.append("FL          " + texto_numero(valor(fila, "FL"), 2, ""))
    lineas.append("Alt. corr.  " + texto_numero(valor(fila, "ALT_CORREGIDA_FT"), 0, "ft"))
    lineas.append("Latitud     " + texto_numero(valor(fila, "LAT"), 5, "°"))
    lineas.append("Longitud    " + texto_numero(valor(fila, "LON"), 5, "°"))
    lineas.append("Último msg  " + str(valor(fila, "TIME")))
    lineas.append("")
    if identificador[0] == CATEGORIA_048:
        lineas.append("Velocidades")
        lineas.append("  GS (BDS 5.0)    " + texto_numero(valor(fila, "BDS50_GS"), 0, "kt"))
        lineas.append("  GS (I048/200)   " + texto_numero(valor(fila, "I048_200_GS_KT"), 0, "kt"))
        lineas.append("  TAS             " + texto_numero(valor(fila, "BDS50_TAS"), 0, "kt"))
        lineas.append("  IAS             " + texto_numero(valor(fila, "BDS60_IAS"), 0, "kt"))
        lineas.append("  Mach            " + texto_numero(valor(fila, "BDS60_MACH"), 3, ""))
        lineas.append("Rumbo")
        lineas.append("  HDG (BDS 6.0)   " + texto_numero(valor(fila, "BDS60_HDG"), 1, "°"))
        lineas.append("  TTA (BDS 5.0)   " + texto_numero(valor(fila, "BDS50_TTA"), 1, "°"))
        lineas.append("  Rumbo I048/200  " + texto_numero(valor(fila, "I048_200_HDG_DEG"), 1, "°"))
        lineas.append("Vertical")
        lineas.append("  BAR             " + texto_numero(valor(fila, "BDS60_BAR"), 0, "ft/min"))
        lineas.append("  IVV             " + texto_numero(valor(fila, "BDS60_IVV"), 0, "ft/min"))
    else:
        lineas.append("Velocidad y rumbo: no se decodifican en CAT021.")
    return "\n".join(lineas)
