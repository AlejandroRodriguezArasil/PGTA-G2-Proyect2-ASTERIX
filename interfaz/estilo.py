"""
Colores, fuentes y tamaños de la aplicación (tema oscuro). ventana.py y mapa.py los cogen de aquí.
Los textos tienen un contraste de al menos 4,5:1 con su fondo.
"""

import customtkinter as ctk

# --- Colores generales ---
FONDO = "#0E1621"
TARJETA = "#162130"
BORDE = "#25344A"
CONTROL_BORDE = "#3A4C64"               # botones secundarios y selectores
CAMPO_FONDO = "#101A26"                 # campos de texto
TEXTO = "#E2E9F2"
TEXTO_SECUNDARIO = "#A3B0C2"
TEXTO_SUAVE = "#8593A6"

# --- Cabecera ---
CABECERA = "#0A111A"
CABECERA_TEXTO = "#E2E9F2"
CABECERA_TEXTO_SUAVE = "#8E9DB2"
CABECERA_PESTANA = "#16212F"              # pestaña no elegida
CABECERA_PESTANA_HOVER = "#1F2D40"
CABECERA_PESTANA_TEXTO = "#B7C4D5"

# --- Acento y botones ---
# Sobre el cian el texto va oscuro, en blanco casi no se lee
PRINCIPAL = "#33B8CC"
PRINCIPAL_HOVER = "#5FCCDC"
TEXTO_SOBRE_PRINCIPAL = "#04161C"
SECUNDARIO_HOVER = "#1F2E42"
DESACTIVADO_FONDO = "#1E2A3A"
DESACTIVADO_TEXTO = "#8896A9"

# --- Selectores (Selector en ventana.py) ---
# La opción elegida va en PRINCIPAL, las demás con borde para que se note que se pueden pulsar
SELECTOR_TEXTO_ELEGIDO = TEXTO_SOBRE_PRINCIPAL
SELECTOR_NO_ELEGIDO = "#16212F"
SELECTOR_BORDE = CONTROL_BORDE
SELECTOR_HOVER = "#21344A"

# --- Casillas y barras de desplazamiento ---
CASILLA_MARCA = TEXTO_SOBRE_PRINCIPAL
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

# --- Mapa ---
RADAR = "#4D9CFF"
ADSB = "#FFA23A"
RESALTADO = "#FF5A5A"
ESTELA_RADAR = "#3F78C9"                  # más apagadas que las siluetas
ESTELA_ADSB = "#B97B32"
TRANSPONDER_FIJO = "#B3BECC"
BLANCO_PURO = "#8A97A9"
ESTACION_RADAR = "#E2E9F2"
ZONA_FILTRO = "#E03131"                   # límite del filtro geográfico
BORDE_ICONO = "#09101A"
FONDO_ATRIBUCION = TARJETA
# Etiquetas: claras en el mapa oscuro y oscuras en el claro
ETIQUETA_MAPA_OSCURO = TEXTO
ETIQUETA_MAPA_CLARO = "#1B2430"

# --- Mapa oscuro (mapa.oscurecer_tesela) ---
# Negro = suelo y calles, medio = mar y carreteras grandes, blanco = nombres
MAPA_OSCURO_NEGRO = "#0A111B"
MAPA_OSCURO_MEDIO = "#2E4560"
MAPA_OSCURO_BLANCO = "#B8C7D9"
# Teselas que aún no han llegado. Las del claro son las mismas que trae tkintermapview
TESELA_VACIA_OSCURO = "#111B27"
TESELA_VACIA_CLARO = "#BEBEBE"
TESELA_NO_ENCONTRADA_CLARO = "#FAFAFA"

# --- Panel de tráfico de la simulación ---
TRAFICO_EN_VUELO = "#7CB7FF"
TRAFICO_EN_TIERRA = "#A3B0C2"
ICONO_EN_VUELO = "✈"
ICONO_EN_TIERRA = "▣"

# --- Eventos de la simulación ---
# Símbolos de texto normales, los emojis no salen igual en todos los Windows
EVENTO_CONTACTO_ICONO = "+"
EVENTO_CONTACTO_COLOR = "#74B4FF"
EVENTO_DESPEGA_ICONO = "↗"
EVENTO_DESPEGA_COLOR = "#52C98E"
EVENTO_ATERRIZA_ICONO = "↘"
EVENTO_ATERRIZA_COLOR = "#E8AD5C"
EVENTO_PERDIDA_ICONO = "×"
EVENTO_PERDIDA_COLOR = "#8E9BAD"        # gris y no rojo, el rojo ya es el resaltado

# --- Tipografía (Consolas es de ancho fijo, para las cifras) ---
FAMILIA = "Segoe UI"
FAMILIA_NUMEROS = "Consolas"
TAMANO_TITULO = 20
TAMANO_SECCION = 14
TAMANO_TEXTO = 13
TAMANO_AYUDA = 11
TAMANO_CIFRA = 26
TAMANO_RELOJ = 28
TAMANO_TABLA = 10           # en puntos (tkinter normal)
TAMANO_ETIQUETA_MAPA = 9
TAMANO_CONTADOR = 15

# --- Tamaños ---
RADIO_TARJETA = 10
MARGEN = 12
ANCHO_PANEL_LATERAL = 320
# Más ancho para que quepan las dos listas (En vuelo y En tierra) una al lado de otra
ANCHO_PANEL_SIMULACION = 400
ALTO_BOTON = 32


def fuente(tamano, negrita=False):
    """Fuente normal de la aplicación."""
    if negrita:
        return ctk.CTkFont(family=FAMILIA, size=tamano, weight="bold")
    return ctk.CTkFont(family=FAMILIA, size=tamano)


def fuente_numeros(tamano, negrita=False):
    """Fuente de ancho fijo, así los números del reloj no bailan."""
    if negrita:
        return ctk.CTkFont(family=FAMILIA_NUMEROS, size=tamano, weight="bold")
    return ctk.CTkFont(family=FAMILIA_NUMEROS, size=tamano)
