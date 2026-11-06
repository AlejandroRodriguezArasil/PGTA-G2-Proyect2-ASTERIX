"""
estilo.py

Colores, tipografías y tamaños de toda la aplicación (R17). Es el único fichero
con colores: ventana.py y mapa.py los toman de aquí.

Estilo sobrio, de herramienta de control: fondo gris muy claro, tarjetas blancas,
cabecera azul marino y un solo azul para las acciones principales. Siempre en modo
claro, porque la tabla de tkinter (ttk.Treeview) no sigue el modo oscuro.
"""

import customtkinter as ctk

# --- Colores generales ---
FONDO = "#F2F4F7"
TARJETA = "#FFFFFF"
BORDE = "#DCE1E8"
TEXTO = "#1B2430"
TEXTO_SECUNDARIO = "#5F6B7A"
TEXTO_SUAVE = "#8A939F"

# --- Cabecera ---
CABECERA = "#14243A"
CABECERA_TEXTO = "#FFFFFF"
CABECERA_TEXTO_SUAVE = "#A9B6C8"
CABECERA_PESTANA = "#22364F"
CABECERA_PESTANA_HOVER = "#2C4566"

# --- Botones ---
PRINCIPAL = "#1F5FAD"
PRINCIPAL_HOVER = "#174C8C"
SECUNDARIO_HOVER = "#E9EEF5"
DESACTIVADO_FONDO = "#D9DDE3"
DESACTIVADO_TEXTO = "#8A939F"

# --- Selectores de varias opciones (Selector en ventana.py) ---
# La opción elegida va en PRINCIPAL; las demás, en blanco con borde para que se vea que se pueden pulsar.
# Desactivado usa DESACTIVADO_FONDO y DESACTIVADO_TEXTO, como los botones.
SELECTOR_TEXTO_ELEGIDO = "#FFFFFF"
SELECTOR_NO_ELEGIDO = "#FFFFFF"
SELECTOR_BORDE = "#8A939F"
SELECTOR_HOVER = "#DCE9F9"

# --- Avisos, estado y ayudas ---
AVISO_FONDO = "#E8F1FC"
AVISO_TEXTO = "#1F4E8C"
ESTADO_LISTO = "#2E8540"
ESTADO_TRABAJANDO = "#B7791F"
TOOLTIP_FONDO = "#1B2430"
TOOLTIP_TEXTO = "#FFFFFF"

# --- Tabla de datos ---
TABLA_CABECERA = "#E7ECF2"
TABLA_FILA_ALTERNA = "#F7F9FB"
TABLA_SELECCION = "#CFE0F7"

# --- Mapa (R43: radar y ADS-B se distinguen por el color) ---
RADAR = "#1F6FEB"
ADSB = "#E8890C"
RESALTADO = "#D62828"
ESTELA_RADAR = "#8FB4F2"
ESTELA_ADSB = "#F5C37A"
TRANSPONDER_FIJO = "#4A5563"
BLANCO_PURO = "#6B7685"
ESTACION_RADAR = "#1B2430"
ZONA_FILTRO = "#5F6B7A"
BORDE_ICONO = "#FFFFFF"
FONDO_ATRIBUCION = "#FFFFFF"

# --- Tipografía (Segoe UI viene con Windows; Consolas, de ancho fijo, para cifras) ---
FAMILIA = "Segoe UI"
FAMILIA_NUMEROS = "Consolas"
TAMANO_TITULO = 20
TAMANO_SECCION = 14
TAMANO_TEXTO = 13
TAMANO_AYUDA = 11
TAMANO_CIFRA = 26
TAMANO_RELOJ = 34
TAMANO_TABLA = 10           # tkinter normal, en puntos
TAMANO_ETIQUETA_MAPA = 9

# --- Tamaños ---
RADIO_TARJETA = 10
MARGEN = 12
ANCHO_PANEL_LATERAL = 320
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
