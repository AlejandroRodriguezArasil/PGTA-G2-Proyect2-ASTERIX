"""
estilo.py

Colores, tipografías y tamaños de toda la aplicación. Es el único fichero
con colores: ventana.py y mapa.py los toman de aquí.

Tema oscuro de sala de control: fondo azul noche casi negro, tarjetas algo más claras,
bordes sutiles, texto claro (no blanco puro) y un solo color de acento, un cian luminoso,
para las acciones principales (botones principales, opción elegida y pestaña activa).
Radar en azul y ADS-B en naranja, como siempre, pero más luminosos para que destaquen
sobre oscuro. customtkinter va en modo oscuro; las tablas (ttk.Treeview) no siguen ese
modo, así que ventana.py les pone estos colores a mano.

Todos los textos cumplen el contraste mínimo de WCAG para texto normal (4,5:1) sobre el
fondo en el que van: el texto principal sobre las tarjetas da 13,3:1; el secundario, 7,4:1;
el suave, 5,2:1; y el texto oscuro sobre el acento, 7,8:1.
"""

import customtkinter as ctk

# --- Colores generales ---
FONDO = "#0E1621"
TARJETA = "#162130"
BORDE = "#25344A"                       # bordes de las tarjetas, sutiles
CONTROL_BORDE = "#3A4C64"               # bordes de botones secundarios y selectores, algo más visibles
CAMPO_FONDO = "#101A26"                 # campos de texto, un poco más hundidos que la tarjeta
TEXTO = "#E2E9F2"
TEXTO_SECUNDARIO = "#A3B0C2"
TEXTO_SUAVE = "#8593A6"

# --- Cabecera ---
CABECERA = "#0A111A"
CABECERA_TEXTO = "#E2E9F2"
CABECERA_TEXTO_SUAVE = "#8E9DB2"
CABECERA_PESTANA = "#16212F"              # cápsula de las pestañas y pestaña no elegida
CABECERA_PESTANA_HOVER = "#1F2D40"
CABECERA_PESTANA_TEXTO = "#B7C4D5"        # texto e icono de la pestaña no elegida

# --- Acento y botones ---
# El acento es el único color de las acciones principales. Encima va texto oscuro: un texto
# blanco sobre un cian luminoso apenas se leería.
PRINCIPAL = "#33B8CC"
PRINCIPAL_HOVER = "#5FCCDC"               # en tema oscuro, al pasar el ratón se aclara
TEXTO_SOBRE_PRINCIPAL = "#04161C"
SECUNDARIO_HOVER = "#1F2E42"
DESACTIVADO_FONDO = "#1E2A3A"
DESACTIVADO_TEXTO = "#8896A9"

# --- Selectores de varias opciones (Selector en ventana.py) ---
# La opción elegida va en PRINCIPAL; las demás, del color de la tarjeta con borde para que se vea que se
# pueden pulsar. Desactivado usa DESACTIVADO_FONDO y DESACTIVADO_TEXTO, como los botones.
SELECTOR_TEXTO_ELEGIDO = TEXTO_SOBRE_PRINCIPAL
SELECTOR_NO_ELEGIDO = "#16212F"
SELECTOR_BORDE = CONTROL_BORDE
SELECTOR_HOVER = "#21344A"

# --- Casillas y barras de desplazamiento ---
CASILLA_MARCA = TEXTO_SOBRE_PRINCIPAL     # la marca dentro de la casilla, sobre el acento
BARRA_DESPLAZAMIENTO = "#2E3E54"
BARRA_DESPLAZAMIENTO_HOVER = "#41557A"

# --- Avisos, estado y ayudas ---
AVISO_FONDO = "#12293A"
AVISO_TEXTO = "#8FD0E4"
ESTADO_LISTO = "#4CC98A"
ESTADO_TRABAJANDO = "#E6A94A"
TOOLTIP_FONDO = "#24344A"
TOOLTIP_TEXTO = TEXTO

# --- Tablas (ttk.Treeview) ---
TABLA_CABECERA = "#1C2A3B"
TABLA_FILA_ALTERNA = "#1A2636"
TABLA_SELECCION = "#1D4656"

# --- Mapa (radar y ADS-B se distinguen por el color) ---
RADAR = "#4D9CFF"
ADSB = "#FFA23A"
RESALTADO = "#FF5A5A"
ESTELA_RADAR = "#3F78C9"                  # las estelas, más apagadas que las siluetas
ESTELA_ADSB = "#B97B32"
TRANSPONDER_FIJO = "#B3BECC"
BLANCO_PURO = "#8A97A9"
ESTACION_RADAR = "#E2E9F2"
ZONA_FILTRO = "#7C8BA1"
BORDE_ICONO = "#09101A"                   # borde oscuro: las siluetas luminosas resaltan sobre el mapa
FONDO_ATRIBUCION = TARJETA
# Etiquetas de los aviones: claras sobre el mapa oscuro y oscuras sobre el claro
ETIQUETA_MAPA_OSCURO = TEXTO
ETIQUETA_MAPA_CLARO = "#1B2430"

# --- Mapa oscuro (mapa.oscurecer_tesela) ---
# Cada tesela, ya en gris e invertida, se colorea de MAPA_OSCURO_NEGRO (lo más oscuro: el suelo y
# las calles) a MAPA_OSCURO_BLANCO (lo más claro: los nombres), pasando por MAPA_OSCURO_MEDIO (el mar
# y las carreteras principales). Así queda en tonos azul noche, como el resto de la aplicación.
MAPA_OSCURO_NEGRO = "#0A111B"
MAPA_OSCURO_MEDIO = "#2E4560"
MAPA_OSCURO_BLANCO = "#B8C7D9"
# Teselas que aún no han llegado (o que no existen), del color de cada mapa para que no se vean
# cuadros blancos o grises. Las del mapa claro son las de tkintermapview.
TESELA_VACIA_OSCURO = "#111B27"
TESELA_VACIA_CLARO = "#BEBEBE"
TESELA_NO_ENCONTRADA_CLARO = "#FAFAFA"

# --- Panel de tráfico de la simulación ---
TRAFICO_EN_VUELO = "#7CB7FF"
TRAFICO_EN_TIERRA = "#A3B0C2"
ICONO_EN_VUELO = "✈"
ICONO_EN_TIERRA = "▣"

# --- Registro de eventos de la simulación: un icono de texto y un color sobrio por tipo ---
# (símbolos de texto normales; los emojis no se ven igual en todos los Windows)
EVENTO_CONTACTO_ICONO = "+"
EVENTO_CONTACTO_COLOR = "#74B4FF"
EVENTO_DESPEGA_ICONO = "↗"
EVENTO_DESPEGA_COLOR = "#52C98E"
EVENTO_ATERRIZA_ICONO = "↘"
EVENTO_ATERRIZA_COLOR = "#E8AD5C"
EVENTO_PERDIDA_ICONO = "×"
EVENTO_PERDIDA_COLOR = "#8E9BAD"        # gris neutro: es lo normal al salir de cobertura (el rojo es el resaltado)

# --- Tipografía (Segoe UI viene con Windows; Consolas, de ancho fijo, para cifras) ---
FAMILIA = "Segoe UI"
FAMILIA_NUMEROS = "Consolas"
TAMANO_TITULO = 20
TAMANO_SECCION = 14
TAMANO_TEXTO = 13
TAMANO_AYUDA = 11
TAMANO_CIFRA = 26
TAMANO_RELOJ = 28
TAMANO_TABLA = 10           # tkinter normal, en puntos
TAMANO_ETIQUETA_MAPA = 9
TAMANO_CONTADOR = 15

# --- Tamaños ---
RADIO_TARJETA = 10
MARGEN = 12
ANCHO_PANEL_LATERAL = 320
# El panel de la simulación es más ancho para que las listas En vuelo y En tierra quepan una al
# lado de la otra. A 1280 píxeles de ancho el mapa sigue teniendo más del doble.
ANCHO_PANEL_SIMULACION = 400
ALTO_BOTON = 32


def fuente(tamano, negrita=False):
    """Fuente de customtkinter con la familia de la aplicación."""
    if negrita:
        return ctk.CTkFont(family=FAMILIA, size=tamano, weight="bold")
    return ctk.CTkFont(family=FAMILIA, size=tamano)


def fuente_numeros(tamano, negrita=False):
    """Fuente de ancho fijo para cifras y para el reloj, para que los números no bailen."""
    if negrita:
        return ctk.CTkFont(family=FAMILIA_NUMEROS, size=tamano, weight="bold")
    return ctk.CTkFont(family=FAMILIA_NUMEROS, size=tamano)
