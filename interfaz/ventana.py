"""
ventana.py

Construcción de la ventana. Aquí solo se crean y se colocan los elementos;
lo que hace cada botón está en main.py y los colores y tipografías, en estilo.py.

Cada función recibe la aplicación (app) y guarda en ella los elementos que main.py
usa después, por ejemplo app.boton_abrir o app.tabla.

    cabecera:         título, grupo, selector de pestaña, fichero cargado y "Abrir fichero"
    pestaña Datos:    resumen, filtros y exportar a la izquierda; tabla por páginas a la derecha
    pestaña Simulación: controles y hora (con la barra de tiempo) arriba; aviso de qué se simula
                      y mapa, con la leyenda y los eventos dentro; tráfico y avión seleccionado
                      en el panel derecho
    barra de estado:  qué está pasando y barra de progreso
"""

import ctypes
import tkinter
import tkinter.font
from tkinter import ttk

import customtkinter as ctk

from funciones import lector
from funciones import simulacion
from funciones.exportar_csv import COLUMNAS
from interfaz import estilo
from interfaz import mapa

TITULO = "ASTERIX Decoder"
# Tamaño mínimo de la ventana: cabe en un portátil de 1920x1080 al 150 % (unos 1280 x 690 útiles)
ANCHO_MINIMO = 1100
ALTO_MINIMO = 600
# La ventana se abre maximizada. Al pulsar Restaurar ocupa esta parte de la pantalla, centrada
FRACCION_VENTANA_RESTAURADA = 0.85
# Espera antes de maximizar: con customtkinter, maximizar justo al crear la ventana a veces no hace efecto
ESPERA_MAXIMIZAR_MS = 100

# Ancho de las columnas de la tabla (píxeles): el del texto más largo, con un máximo
MARGEN_COLUMNA = 24
ANCHO_MAXIMO_COLUMNA = 220

# Anchos fijos (píxeles) de lo que cambia mientras se trabaja, para que no empuje a nada
ANCHO_BARRA_PROGRESO_TABLA = 560
ANCHO_RELOJ = 170

# Opciones de los selectores (píxeles)
ALTO_SELECTOR = 28
ANCHO_MINIMO_OPCION = 44
RADIO_OPCION = 6
SEPARACION_OPCIONES = 4

# Pestañas Datos / Simulación de la cabecera, en forma de cápsula (píxeles)
ANCHO_PESTANA = 150
ALTO_PESTANA = 36
RADIO_PESTANA = 18              # la mitad del alto: los extremos quedan redondos
MARGEN_PESTANAS = 4             # cápsula de fondo que se ve alrededor de las pestañas
TAMANO_ICONO_PESTANA = 18

# Cuadro "Selected aircraft": líneas de su versión más larga (mapa.texto_informacion de un avión
# de radar que además es el transponder fijo) y margen interior en píxeles
LINEAS_INFO_AVION = 28
MARGEN_CUADRO_INFO = 20
TEXTO_SIN_AVION = "Click an aircraft on the map or in the traffic lists to see its details."

# Listas En vuelo / En tierra del panel de tráfico: filas que se ven sin desplazar y ancho de
# cada columna (píxeles). En vuelo: callsign, nivel y "Seen by"; en tierra: callsign.
FILAS_LISTA_TRAFICO = 8
ANCHO_COLUMNA_CALLSIGN = 86
ANCHO_COLUMNA_NIVEL = 68
ANCHO_COLUMNA_VISTO_POR = 80
ANCHO_BARRA_LISTA = 12
# CTkScrollbar pide 200 píxeles de alto si no se le da otro: con uno pequeño, la barra se estira
# hasta el alto de su lista en lugar de hacer más alta la tarjeta (sobre todo la de eventos)
ALTO_MINIMO_BARRA_LISTA = 40

# Recuadros dentro del mapa (leyenda y eventos): separación con el borde del mapa y alto de su
# título, que se pulsa para recogerlos o mostrarlos (ver Plegable), en píxeles
MARGEN_VENTANA_MAPA = 10
ALTO_TITULO_PLEGABLE = 24
ALTO_FILA_LEYENDA = 20
FLECHA_DESPLEGADA = "▾"
FLECHA_RECOGIDA = "▸"

# Ventana de eventos dentro del mapa: filas que se ven sin desplazar y ancho de sus columnas (píxeles)
FILAS_VENTANA_EVENTOS = 4
ANCHO_EVENTO_HORA = 66
ANCHO_EVENTO_ICONO = 20
ANCHO_EVENTO_TIPO = 146
ANCHO_EVENTO_CALLSIGN = 70          # 8 caracteres de ancho fijo; el sistema va justo detrás
ANCHO_EVENTO_SISTEMA = 50

# Etiqueta (tag de ttk), icono y color de cada tipo de evento en el registro
ESTILO_EVENTO = {
    simulacion.NUEVO_CONTACTO: ("contacto", estilo.EVENTO_CONTACTO_ICONO, estilo.EVENTO_CONTACTO_COLOR),
    simulacion.DESPEGA: ("despega", estilo.EVENTO_DESPEGA_ICONO, estilo.EVENTO_DESPEGA_COLOR),
    simulacion.ATERRIZA: ("aterriza", estilo.EVENTO_ATERRIZA_ICONO, estilo.EVENTO_ATERRIZA_COLOR),
    simulacion.PERDIDA_CONTACTO: ("perdida", estilo.EVENTO_PERDIDA_ICONO, estilo.EVENTO_PERDIDA_COLOR),
}

# Campo de la hora de "Go to time" (píxeles)
ANCHO_ENTRADA_HORA = 70

# Desplazamiento (ver Desplazador): delta que equivale a una unidad. En la tabla, un clic de la
# rueda (120) baja una fila, como hace Tk; en los paneles, cada 6 de delta es un píxel, como hace
# customtkinter (20 píxeles por clic).
PASO_DESPLAZAMIENTO_TABLA = 120
PASO_DESPLAZAMIENTO_PANEL = 6
# En horizontal la unidad de la tabla es un píxel: con 120 por unidad (lo que hace Tk) un clic solo
# movía 1 píxel. Con 3 por píxel, un clic mueve 40 píxeles y el panel táctil se nota.
PASO_DESPLAZAMIENTO_TABLA_HORIZONTAL = 3

# Barra de título oscura de Windows (ver poner_barra_titulo_oscura)
DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_USE_IMMERSIVE_DARK_MODE_ANTIGUO = 19

# Color de fondo original de cada botón, para devolvérselo al activarlo (ver cambiar_estado)
COLOR_ORIGINAL_BOTONES = {}

# Último estado (True activo, False desactivado) aplicado a cada control (ver cambiar_estado)
ESTADO_CONTROLES = {}


# =============================================================================
# Ventana principal
# =============================================================================

def crear_ventana_principal():
    """
    Crea la ventana principal en modo oscuro. Se queda escondida mientras main.py la construye y se
    enseña ya maximizada (mostrar_maximizada), para que no se vea antes una ventana pequeña.
    """
    ctk.set_appearance_mode("dark")
    raiz = ctk.CTk(fg_color=estilo.FONDO)
    raiz.title(TITULO)
    raiz.minsize(ANCHO_MINIMO, ALTO_MINIMO)
    poner_tamano_restaurado(raiz)
    raiz.withdraw()
    # after() solo se ejecuta cuando arranca mainloop(), es decir, con la ventana ya construida
    raiz.after(ESPERA_MAXIMIZAR_MS, mostrar_maximizada, raiz)
    return raiz


def poner_tamano_restaurado(raiz):
    """
    Tamaño y posición de la ventana cuando se pulsa Restaurar: FRACCION_VENTANA_RESTAURADA de la
    pantalla, centrada. Sale del tamaño de la pantalla del ordenador en el que se abre, así que vale
    para cualquier resolución, y nunca es menor que el tamaño mínimo.
    winfo_screenwidth() y winfo_screenheight() dan píxeles reales de la pantalla. geometry() de
    customtkinter multiplica el ancho y el alto por la escala de Windows (125 %, 150 %...), así que
    antes se dividen por esa escala; la posición (x, y) no la multiplica, así que va en píxeles reales.
    """
    escala = ctk.ScalingTracker.get_window_scaling(raiz)
    ancho_pantalla = raiz.winfo_screenwidth()
    alto_pantalla = raiz.winfo_screenheight()
    ancho = max(ANCHO_MINIMO, int(ancho_pantalla * FRACCION_VENTANA_RESTAURADA / escala))
    alto = max(ALTO_MINIMO, int(alto_pantalla * FRACCION_VENTANA_RESTAURADA / escala))
    x = max(0, (ancho_pantalla - int(ancho * escala)) // 2)
    y = max(0, (alto_pantalla - int(alto * escala)) // 2)
    raiz.geometry(str(ancho) + "x" + str(alto) + "+" + str(x) + "+" + str(y))


def mostrar_maximizada(raiz):
    """
    Enseña la ventana maximizada: el estado "zoomed" de Windows, que ocupa la pantalla y deja la barra
    de título con los botones de minimizar, restaurar y cerrar (no es pantalla completa sin bordes).
    """
    raiz.state("zoomed")
    poner_barra_titulo_oscura(raiz)


def poner_barra_titulo_oscura(raiz):
    """
    Pide a Windows la barra de título oscura, para que no quede una franja blanca encima del tema
    oscuro. Se hace con la función DwmSetWindowAttribute de Windows (dwmapi.dll), llamada con ctypes,
    con el atributo DWMWA_USE_IMMERSIVE_DARK_MODE = 20 (en Windows 10 anteriores a la versión 20H1
    el mismo atributo era el 19). Si no funciona (otro sistema o un Windows antiguo), la barra se
    queda como esté: no es un error.
    """
    try:
        ventana_windows = int(raiz.wm_frame(), 16)      # identificador de la ventana para Windows
        valor = ctypes.c_int(1)                          # 1 = barra oscura
        for atributo in (DWMWA_USE_IMMERSIVE_DARK_MODE, DWMWA_USE_IMMERSIVE_DARK_MODE_ANTIGUO):
            resultado = ctypes.windll.dwmapi.DwmSetWindowAttribute(ventana_windows, atributo,
                                                                  ctypes.byref(valor), ctypes.sizeof(valor))
            if resultado == 0:                           # 0 = S_OK: Windows lo ha aceptado
                break
    except Exception:
        pass


# =============================================================================
# Piezas que se repiten
# =============================================================================

def crear_tarjeta(padre, titulo):
    """Tarjeta con borde suave y, si se da, un título de sección."""
    tarjeta = ctk.CTkFrame(padre, fg_color=estilo.TARJETA, corner_radius=estilo.RADIO_TARJETA,
                           border_width=1, border_color=estilo.BORDE)
    if titulo != "":
        ctk.CTkLabel(tarjeta, text=titulo, font=estilo.fuente(estilo.TAMANO_SECCION, True),
                     text_color=estilo.TEXTO, anchor="w").pack(fill="x", padx=16, pady=(12, 6))
    return tarjeta


def crear_etiqueta(padre, texto, tamano, color):
    """Etiqueta de texto alineada a la izquierda."""
    return ctk.CTkLabel(padre, text=texto, font=estilo.fuente(tamano), text_color=color,
                        anchor="w", justify="left")


def crear_boton_principal(padre, texto, comando, ancho):
    """Botón de la acción principal de cada zona: relleno del color de acento."""
    return ctk.CTkButton(padre, text=texto, command=comando, width=ancho, height=estilo.ALTO_BOTON,
                         font=estilo.fuente(estilo.TAMANO_TEXTO, True), fg_color=estilo.PRINCIPAL,
                         hover_color=estilo.PRINCIPAL_HOVER, text_color=estilo.TEXTO_SOBRE_PRINCIPAL,
                         text_color_disabled=estilo.DESACTIVADO_TEXTO)


def crear_boton_secundario(padre, texto, comando, ancho):
    """Botón de una acción secundaria: solo el borde, más discreto."""
    return ctk.CTkButton(padre, text=texto, command=comando, width=ancho, height=estilo.ALTO_BOTON,
                         font=estilo.fuente(estilo.TAMANO_TEXTO), fg_color="transparent",
                         hover_color=estilo.SECUNDARIO_HOVER, border_width=1,
                         border_color=estilo.CONTROL_BORDE, text_color=estilo.PRINCIPAL,
                         text_color_disabled=estilo.DESACTIVADO_TEXTO)


class Selector(ctk.CTkFrame):
    """
    Selector de varias opciones: una fila de botones en la que siempre hay uno elegido.
    Se usa igual que el CTkSegmentedButton de customtkinter: get(), set(valor) y, al pulsar
    una opción, comando(valor).

    Se hace con botones normales porque CTkSegmentedButton pone el mismo color de texto a todas
    las opciones, y aquí la elegida va en blanco sobre azul y las demás en oscuro sobre blanco,
    para que se vea que se pueden pulsar. Desactivado, todo va en el gris de los botones.
    También se puede desactivar una sola opción (cambiar_estado_opcion).
    """

    def __init__(self, padre, valores, comando):
        super().__init__(padre, fg_color="transparent")
        self.comando = comando
        self.elegido = valores[0]
        self.activo = True
        self.botones = {}
        self.ayudas = {}                    # ayuda de cada opción; solo tiene texto si está desactivada
        self.opciones_desactivadas = []
        for valor in valores:
            boton = ctk.CTkButton(self, text=valor, width=ANCHO_MINIMO_OPCION, height=ALTO_SELECTOR,
                                  corner_radius=RADIO_OPCION, border_width=1,
                                  font=estilo.fuente(estilo.TAMANO_TEXTO),
                                  text_color_disabled=estilo.DESACTIVADO_TEXTO,
                                  command=self.funcion_al_pulsar(valor))
            if len(self.botones) == 0:
                boton.pack(side="left", fill="x", expand=True)
            else:
                boton.pack(side="left", fill="x", expand=True, padx=(SEPARACION_OPCIONES, 0))
            self.botones[valor] = boton
            self.ayudas[valor] = Tooltip(boton, "")
        self.pintar()

    def funcion_al_pulsar(self, valor):
        """Devuelve la función que ejecuta el botón de la opción 'valor' al pulsarlo."""
        def al_pulsar():
            self.pulsar(valor)
        return al_pulsar

    def pulsar(self, valor):
        """Clic en una opción: se elige y se avisa a main.py (si ya estaba elegida, no hace nada)."""
        if valor == self.elegido:
            return
        self.set(valor)
        if self.comando is not None:
            self.comando(valor)

    def get(self):
        return self.elegido

    def set(self, valor):
        """Elige una opción sin llamar al comando (como CTkSegmentedButton.set)."""
        if valor == self.elegido:
            return
        self.elegido = valor
        self.pintar()

    def cambiar_estado(self, activo):
        self.activo = activo
        self.pintar()

    def cambiar_estado_opcion(self, valor, activa, ayuda):
        """
        Activa o desactiva una sola opción. Desactivada se ve en gris, no se puede pulsar y, con el
        ratón encima, muestra 'ayuda' (por qué no se puede). Si ya estaba así no se toca nada,
        para no redibujar el selector en cada salto de la simulación.
        """
        if activa and valor not in self.opciones_desactivadas:
            return
        if not activa and valor in self.opciones_desactivadas:
            return
        if activa:
            self.opciones_desactivadas.remove(valor)
            self.ayudas[valor].texto = ""
        else:
            self.opciones_desactivadas.append(valor)
            self.ayudas[valor].texto = ayuda
        self.pintar()

    def pintar(self):
        """Pone a cada opción sus colores: desactivada, elegida o no elegida."""
        for valor in self.botones:
            boton = self.botones[valor]
            if not self.activo or valor in self.opciones_desactivadas:
                boton.configure(state="disabled", fg_color=estilo.DESACTIVADO_FONDO,
                                border_color=estilo.DESACTIVADO_FONDO)
            elif valor == self.elegido:
                boton.configure(state="normal", fg_color=estilo.PRINCIPAL, hover_color=estilo.PRINCIPAL_HOVER,
                                border_color=estilo.PRINCIPAL, text_color=estilo.SELECTOR_TEXTO_ELEGIDO)
            else:
                boton.configure(state="normal", fg_color=estilo.SELECTOR_NO_ELEGIDO,
                                hover_color=estilo.SELECTOR_HOVER, border_color=estilo.SELECTOR_BORDE,
                                text_color=estilo.TEXTO)


class Pestanas(Selector):
    """
    Pestañas Datos / Simulación de la cabecera: un Selector en forma de cápsula sobre la franja
    oscura, con un icono en cada pestaña. Funciona igual que Selector (get, set y comando al
    pulsar); solo cambian el tamaño y los colores (pintar).
    iconos: pestaña -> (icono cuando está elegida, icono cuando no lo está).
    """

    def __init__(self, padre, valores, iconos, comando):
        self.iconos = iconos            # antes de crear el Selector, porque al crearse ya llama a pintar()
        super().__init__(padre, valores, comando)
        self.configure(fg_color=estilo.CABECERA_PESTANA, corner_radius=RADIO_PESTANA + MARGEN_PESTANAS)
        for valor in self.botones:
            # bg_color: las esquinas de fuera de cada pestaña son del color de la cápsula, no de la cabecera
            self.botones[valor].configure(width=ANCHO_PESTANA, height=ALTO_PESTANA, corner_radius=RADIO_PESTANA,
                                          border_width=0, bg_color=estilo.CABECERA_PESTANA, compound="left",
                                          font=estilo.fuente(estilo.TAMANO_SECCION, True))
            self.botones[valor].pack_configure(pady=MARGEN_PESTANAS)
        # Margen también a la izquierda de la primera y a la derecha de la última
        self.botones[valores[0]].pack_configure(padx=(MARGEN_PESTANAS, 0))
        self.botones[valores[-1]].pack_configure(padx=(SEPARACION_OPCIONES, MARGEN_PESTANAS))

    def pintar(self):
        """La pestaña elegida, en el color de acento con texto oscuro; la otra, del color de la cápsula."""
        for valor in self.botones:
            boton = self.botones[valor]
            if valor == self.elegido:
                boton.configure(fg_color=estilo.PRINCIPAL, hover_color=estilo.PRINCIPAL_HOVER,
                                text_color=estilo.TEXTO_SOBRE_PRINCIPAL, image=self.iconos[valor][0])
            else:
                boton.configure(fg_color=estilo.CABECERA_PESTANA, hover_color=estilo.CABECERA_PESTANA_HOVER,
                                text_color=estilo.CABECERA_PESTANA_TEXTO, image=self.iconos[valor][1])


def crear_iconos_pestanas():
    """
    Iconos de las pestañas: del color del texto sobre el acento para la elegida y del color suave
    para la otra (dibujados en mapa.py).
    """
    tamano = TAMANO_ICONO_PESTANA
    tabla = mapa.dibujar_icono_tabla(estilo.TEXTO_SOBRE_PRINCIPAL, tamano)
    tabla_suave = mapa.dibujar_icono_tabla(estilo.CABECERA_PESTANA_TEXTO, tamano)
    avion = mapa.dibujar_icono_avion(estilo.TEXTO_SOBRE_PRINCIPAL, tamano)
    avion_suave = mapa.dibujar_icono_avion(estilo.CABECERA_PESTANA_TEXTO, tamano)
    return {
        "Data": (ctk.CTkImage(light_image=tabla, size=(tamano, tamano)),
                  ctk.CTkImage(light_image=tabla_suave, size=(tamano, tamano))),
        "Simulation": (ctk.CTkImage(light_image=avion, size=(tamano, tamano)),
                       ctk.CTkImage(light_image=avion_suave, size=(tamano, tamano))),
    }


def crear_selector(padre, valores, comando):
    """Selector de varias opciones con los colores de la aplicación (ver la clase Selector)."""
    return Selector(padre, valores, comando)


def crear_casilla(padre, texto, comando):
    """Casilla de verificación con los colores de la aplicación."""
    return ctk.CTkCheckBox(padre, text=texto, command=comando, font=estilo.fuente(estilo.TAMANO_TEXTO),
                           text_color=estilo.TEXTO, fg_color=estilo.PRINCIPAL,
                           hover_color=estilo.PRINCIPAL_HOVER, border_color=estilo.TEXTO_SUAVE,
                           checkmark_color=estilo.CASILLA_MARCA, text_color_disabled=estilo.DESACTIVADO_TEXTO,
                           checkbox_width=20, checkbox_height=20)


def crear_entrada(padre, ancho, ejemplo):
    """Campo de texto con un ejemplo en gris mientras está vacío."""
    return ctk.CTkEntry(padre, width=ancho, placeholder_text=ejemplo, font=estilo.fuente(estilo.TAMANO_TEXTO),
                        fg_color=estilo.CAMPO_FONDO, border_color=estilo.CONTROL_BORDE, text_color=estilo.TEXTO,
                        placeholder_text_color=estilo.TEXTO_SUAVE)


def crear_barra_desplazamiento(padre, orientacion, comando):
    """Barra de desplazamiento con los colores de la aplicación (el tamaño, el de customtkinter)."""
    return ctk.CTkScrollbar(padre, orientation=orientacion, command=comando, fg_color="transparent",
                            button_color=estilo.BARRA_DESPLAZAMIENTO,
                            button_hover_color=estilo.BARRA_DESPLAZAMIENTO_HOVER)


class Tooltip:
    """Texto de ayuda que aparece al dejar el ratón sobre un control."""

    def __init__(self, elemento, texto):
        self.elemento = elemento
        self.texto = texto
        self.ventana_ayuda = None
        elemento.bind("<Enter>", self.mostrar, add="+")
        elemento.bind("<Leave>", self.ocultar, add="+")

    def mostrar(self, evento):
        """Crea una ventanita sin bordes justo debajo del control. Sin texto, no sale nada."""
        if self.ventana_ayuda is not None or self.texto == "":
            return
        x = self.elemento.winfo_rootx() + 8
        y = self.elemento.winfo_rooty() + self.elemento.winfo_height() + 6
        self.ventana_ayuda = tkinter.Toplevel(self.elemento)
        self.ventana_ayuda.wm_overrideredirect(True)
        self.ventana_ayuda.wm_geometry("+" + str(x) + "+" + str(y))
        tkinter.Label(self.ventana_ayuda, text=self.texto, justify="left", wraplength=320,
                      bg=estilo.TOOLTIP_FONDO, fg=estilo.TOOLTIP_TEXTO,
                      font=(estilo.FAMILIA, estilo.TAMANO_AYUDA - 2), padx=8, pady=5).pack()

    def ocultar(self, evento):
        """Cierra la ventanita de ayuda."""
        if self.ventana_ayuda is not None:
            self.ventana_ayuda.destroy()
            self.ventana_ayuda = None


# =============================================================================
# Desplazamiento con la rueda del ratón y con el panel táctil
# =============================================================================

class Desplazador:
    """
    Cuenta cuánto hay que desplazar con la rueda del ratón o con el panel táctil (Windows).
    Cada clic de la rueda llega con delta = 120, pero el panel táctil manda muchos eventos con
    deltas pequeños (10, 20...). Si cada delta se divide por separado, como hacen Tk y
    customtkinter, los pequeños se pierden y el panel táctil no mueve nada. Aquí se van sumando
    y se desplaza una unidad cada vez que la suma llega a 'paso': con la rueda el resultado es el
    mismo de siempre y con el panel táctil el movimiento es suave.
    """

    def __init__(self, paso):
        self.paso = paso
        self.acumulado = 0

    def unidades(self, delta):
        """Suma el delta y devuelve cuántas unidades hay que desplazar (positivo: hacia abajo o a la derecha)."""
        self.acumulado = self.acumulado - delta     # delta negativo = rueda hacia uno mismo = bajar
        unidades = int(self.acumulado / self.paso)
        self.acumulado = self.acumulado - unidades * self.paso
        return unidades


def activar_desplazamiento_tabla(tabla):
    """
    Rueda y panel táctil en la tabla: <MouseWheel> en vertical y <Shift-MouseWheel> en horizontal
    (así llega en Windows el desplazamiento lateral del panel táctil).
    """
    vertical = Desplazador(PASO_DESPLAZAMIENTO_TABLA)
    horizontal = Desplazador(PASO_DESPLAZAMIENTO_TABLA_HORIZONTAL)

    def al_mover_vertical(evento):
        unidades = vertical.unidades(evento.delta)
        if unidades != 0:
            tabla.yview_scroll(unidades, "units")
        return "break"          # "break": que no actúe además el desplazamiento propio de Tk

    def al_mover_horizontal(evento):
        unidades = horizontal.unidades(evento.delta)
        if unidades != 0:
            tabla.xview_scroll(unidades, "units")
        return "break"

    tabla.bind("<MouseWheel>", al_mover_vertical)
    tabla.bind("<Shift-MouseWheel>", al_mover_horizontal)


class PanelDesplazable(ctk.CTkScrollableFrame):
    """
    CTkScrollableFrame que también se desplaza con el panel táctil. customtkinter recibe la rueda
    en toda la ventana y, si el ratón está encima del panel (o de algo de dentro, como el texto
    del avión), lo desplaza con el delta dividido entre 6 y sin decimales. Aquí se sustituye ese
    método por uno que acumula el delta con un Desplazador.
    """

    def __init__(self, padre, **opciones):
        super().__init__(padre, **opciones)
        self.configure(scrollbar_button_color=estilo.BARRA_DESPLAZAMIENTO,
                       scrollbar_button_hover_color=estilo.BARRA_DESPLAZAMIENTO_HOVER)
        self.desplazador = Desplazador(PASO_DESPLAZAMIENTO_PANEL)

    def _mouse_wheel_all(self, evento):
        """Rueda o panel táctil en cualquier parte de la ventana: solo se mueve si es encima de este panel."""
        if not self.check_if_master_is_canvas(evento.widget):
            return
        unidades = self.desplazador.unidades(evento.delta)
        if unidades != 0 and self._parent_canvas.yview() != (0.0, 1.0):
            self._parent_canvas.yview_scroll(unidades, "units")


def activar_desplazamiento_lista(lista):
    """
    Rueda y panel táctil en una lista de dentro de un panel desplazable (tráfico y eventos).
    Si la lista tiene filas ocultas, se desplaza la lista; si caben todas, no se hace nada aquí y
    el evento sigue hasta el panel, que se desplaza como si el ratón no estuviera encima de la lista.
    """
    desplazador = Desplazador(PASO_DESPLAZAMIENTO_TABLA)

    def al_mover(evento):
        if lista.yview() == (0.0, 1.0):
            return None
        unidades = desplazador.unidades(evento.delta)
        if unidades != 0:
            lista.yview_scroll(unidades, "units")
        return "break"

    lista.bind("<MouseWheel>", al_mover)


class ListaIncremental:
    """
    Lista (ttk.Treeview) que se pone al día solo en lo que cambia. La usan las listas En vuelo y
    En tierra del panel de tráfico, que se ponen al día en cada salto de la simulación (60 por
    segundo a x60): rehacerlas enteras cada vez haría que la ventana fuera a tirones.

    Cada fila tiene una clave (la TA del avión, que también es el identificador de la fila en el
    Treeview), un texto por el que se ordena (el callsign) y sus valores. actualizar() recibe todas
    las filas que tiene que haber y las compara con las que hay:
        - borra las que ya no están y añade las nuevas;
        - cambia los valores solo de las filas que han cambiado (por ejemplo, el nivel);
        - si ha entrado o salido alguna fila, o ha cambiado algún callsign, vuelve a ordenar,
          moviendo las filas a su sitio sin borrarlas.
    """

    def __init__(self, tabla):
        self.tabla = tabla
        self.filas = {}             # clave -> (texto de orden, valores) de las filas que se ven

    def actualizar(self, filas_nuevas):
        """Deja en la lista exactamente filas_nuevas (clave -> (texto de orden, valores))."""
        reordenar = False
        for clave in list(self.filas.keys()):
            if clave not in filas_nuevas:
                self.tabla.delete(clave)
                del self.filas[clave]
                reordenar = True

        for clave in filas_nuevas:
            orden, valores = filas_nuevas[clave]
            if clave not in self.filas:
                self.tabla.insert("", "end", iid=clave, values=valores)
                reordenar = True
            else:
                orden_anterior, valores_anteriores = self.filas[clave]
                if valores != valores_anteriores:
                    self.tabla.item(clave, values=valores)
                if orden != orden_anterior:
                    reordenar = True
            self.filas[clave] = (orden, valores)

        if reordenar:
            self.ordenar()

    def clave_de_orden(self, clave):
        """Por qué se ordena: el callsign y, si dos coinciden, la clave."""
        return (self.filas[clave][0], clave)

    def ordenar(self):
        """Pone las filas por orden alfabético de callsign, moviéndolas sin borrarlas."""
        claves = sorted(self.filas.keys(), key=self.clave_de_orden)
        for posicion in range(len(claves)):
            self.tabla.move(claves[posicion], "", posicion)

    def seleccionar(self, clave):
        """Marca la fila de esa clave (o ninguna, con None) si no lo estaba ya."""
        if clave is not None and clave in self.filas:
            if self.tabla.selection() != (clave,):
                self.tabla.selection_set(clave)
                self.tabla.see(clave)
        elif len(self.tabla.selection()) > 0:
            self.tabla.selection_remove(self.tabla.selection())

    def vaciar(self):
        """Quita todas las filas."""
        for clave in self.filas:
            self.tabla.delete(clave)
        self.filas = {}


class RegistroEventos:
    """
    Lista de eventos de la simulación (ttk.Treeview), con el más reciente arriba. Igual que en
    ListaIncremental, en cada salto solo se añaden los eventos nuevos; cuando hay más de
    simulacion.EVENTOS_GUARDADOS se quitan los más antiguos, que están abajo.
    Cada fila guarda la TA del avión, para seleccionarlo al pulsar el evento (ta_de_fila).
    """

    def __init__(self, tabla):
        self.tabla = tabla
        self.ta_por_fila = {}       # identificador de la fila -> TA del avión del evento

    def anadir(self, eventos):
        """Pone arriba los eventos de la lista, del más antiguo al más nuevo (el último queda el primero)."""
        for evento in eventos:
            etiqueta = ESTILO_EVENTO[evento["tipo"]][0]       # el color va en la etiqueta (crear_ventana_eventos)
            icono = ESTILO_EVENTO[evento["tipo"]][1]
            fila = str(evento["numero"])
            hora = lector.formatear_hora(evento["segundo"])[:8]
            self.tabla.insert("", 0, iid=fila, tags=(etiqueta,),
                              values=(hora, icono, evento["tipo"], evento["nombre"], evento["sistema"]))
            self.ta_por_fila[fila] = evento["ta"]
        filas = self.tabla.get_children()
        for posicion in range(simulacion.EVENTOS_GUARDADOS, len(filas)):
            self.tabla.delete(filas[posicion])
            del self.ta_por_fila[filas[posicion]]

    def ta_de_fila(self, fila):
        """TA del avión del evento de esa fila (None si la fila no existe)."""
        return self.ta_por_fila.get(fila)

    def vaciar(self):
        """Quita todos los eventos."""
        filas = self.tabla.get_children()
        if len(filas) > 0:
            self.tabla.delete(*filas)
        self.ta_por_fila = {}


def cambiar_estado(elemento, activo):
    """
    Activa o desactiva un control. Los botones desactivados se ponen en gris para que se vea
    que no se pueden pulsar; al activarlos recuperan su color original.
    Si el control ya está en ese estado no se toca: volver a configurarlo hace que customtkinter
    lo redibuje (en los selectores, varias veces seguidas) y se ve un parpadeo.
    """
    if elemento in ESTADO_CONTROLES and ESTADO_CONTROLES[elemento] == activo:
        return
    ESTADO_CONTROLES[elemento] = activo

    if isinstance(elemento, Selector):
        elemento.cambiar_estado(activo)
        return

    es_boton = isinstance(elemento, ctk.CTkButton)
    if es_boton and elemento not in COLOR_ORIGINAL_BOTONES:
        COLOR_ORIGINAL_BOTONES[elemento] = elemento.cget("fg_color")

    if activo:
        elemento.configure(state="normal")
        if es_boton:
            elemento.configure(fg_color=COLOR_ORIGINAL_BOTONES[elemento])
    else:
        elemento.configure(state="disabled")
        if es_boton:
            elemento.configure(fg_color=estilo.DESACTIVADO_FONDO)


def esta_activo(elemento):
    """True si el control está activo (el último cambiar_estado; al crearse, todos lo están)."""
    return ESTADO_CONTROLES.get(elemento, True)


def cambiar_texto(etiqueta, texto):
    """Cambia el texto de una etiqueta solo si es distinto, para no redibujarla sin necesidad."""
    if etiqueta.cget("text") != texto:
        etiqueta.configure(text=texto)


def escribir_texto(cuadro, texto):
    """Cambia el texto de un cuadro de texto de solo lectura (solo si es distinto)."""
    if cuadro.get("1.0", "end-1c") == texto:
        return
    cuadro.configure(state="normal")
    cuadro.delete("1.0", "end")
    cuadro.insert("1.0", texto)
    cuadro.configure(state="disabled")


# =============================================================================
# Cabecera, pestañas y barra de estado
# =============================================================================

def crear_cabecera(app):
    """
    Cabecera azul marino: título, grupo, selector de pestaña, fichero cargado y botón para abrirlo.
    Guarda: app.selector_pestana, app.etiqueta_fichero, app.boton_abrir.
    """
    cabecera = ctk.CTkFrame(app.raiz, fg_color=estilo.CABECERA, corner_radius=0, height=68)
    cabecera.pack(side="top", fill="x")
    cabecera.grid_columnconfigure(1, weight=1)

    titulos = ctk.CTkFrame(cabecera, fg_color="transparent")
    titulos.grid(row=0, column=0, sticky="w", padx=20, pady=10)
    ctk.CTkLabel(titulos, text="ASTERIX Decoder", font=estilo.fuente(estilo.TAMANO_TITULO, True),
                 text_color=estilo.CABECERA_TEXTO, anchor="w").pack(anchor="w")
    ctk.CTkLabel(titulos, text="CAT048 · CAT021     PGTA · Group 02", font=estilo.fuente(estilo.TAMANO_AYUDA),
                 text_color=estilo.CABECERA_TEXTO_SUAVE, anchor="w").pack(anchor="w")

    app.selector_pestana = Pestanas(cabecera, ["Data", "Simulation"], crear_iconos_pestanas(), app.cambiar_pestana)
    app.selector_pestana.grid(row=0, column=1)

    derecha = ctk.CTkFrame(cabecera, fg_color="transparent")
    derecha.grid(row=0, column=2, sticky="e", padx=20)
    app.etiqueta_fichero = ctk.CTkLabel(derecha, text="No file loaded",
                                        font=estilo.fuente(estilo.TAMANO_TEXTO),
                                        text_color=estilo.CABECERA_TEXTO_SUAVE)
    app.etiqueta_fichero.pack(side="left", padx=(0, 14))
    app.boton_abrir = crear_boton_principal(derecha, "Open .ast file", app.elegir_fichero, 160)
    app.boton_abrir.pack(side="left")
    Tooltip(app.boton_abrir, "Choose an ASTERIX file (.ast) with CAT048 and/or CAT021 messages.")


def crear_barra_estado(app):
    """
    Barra de abajo: un punto de color, lo que está pasando y la barra de progreso.
    Guarda: app.punto_estado, app.etiqueta_estado, app.etiqueta_porcentaje, app.barra_progreso.
    """
    barra = ctk.CTkFrame(app.raiz, fg_color=estilo.TARJETA, corner_radius=0, height=34,
                         border_width=1, border_color=estilo.BORDE)
    barra.pack(side="bottom", fill="x")

    app.punto_estado = ctk.CTkLabel(barra, text="●", font=estilo.fuente(estilo.TAMANO_TEXTO),
                                    text_color=estilo.TEXTO_SUAVE)
    app.punto_estado.pack(side="left", padx=(16, 6))
    app.etiqueta_estado = crear_etiqueta(barra, "Open an .ast file to start",
                                         estilo.TAMANO_AYUDA + 1, estilo.TEXTO_SECUNDARIO)
    app.etiqueta_estado.pack(side="left")

    app.etiqueta_porcentaje = ctk.CTkLabel(barra, text="", width=50, font=estilo.fuente_numeros(estilo.TAMANO_AYUDA),
                                           text_color=estilo.TEXTO_SECUNDARIO)
    app.etiqueta_porcentaje.pack(side="right", padx=(6, 16))
    app.barra_progreso = ctk.CTkProgressBar(barra, width=260, height=8, fg_color=estilo.BORDE,
                                            progress_color=estilo.PRINCIPAL)
    app.barra_progreso.set(0)
    app.barra_progreso.pack(side="right")


def crear_pestanas(app):
    """
    Zona central con las dos pestañas; el selector de la cabecera muestra una u otra.
    Guarda: app.pestana_datos y app.pestana_simulacion.
    """
    contenido = ctk.CTkFrame(app.raiz, fg_color="transparent")
    contenido.pack(side="top", fill="both", expand=True, padx=estilo.MARGEN, pady=estilo.MARGEN)
    app.pestana_datos = ctk.CTkFrame(contenido, fg_color="transparent")
    app.pestana_simulacion = ctk.CTkFrame(contenido, fg_color="transparent")
    app.pestana_datos.pack(fill="both", expand=True)


# =============================================================================
# Pestaña Datos
# =============================================================================

def crear_cifra(padre, fila, columna, texto_pie):
    """Una cifra grande con su explicación debajo (tarjeta de resumen). Devuelve la etiqueta de la cifra."""
    celda = ctk.CTkFrame(padre, fg_color="transparent")
    celda.grid(row=fila, column=columna, sticky="w", padx=(16, 8), pady=4)
    cifra = ctk.CTkLabel(celda, text="—", font=estilo.fuente_numeros(estilo.TAMANO_CIFRA, True),
                         text_color=estilo.TEXTO, anchor="w")
    cifra.pack(anchor="w")
    crear_etiqueta(celda, texto_pie, estilo.TAMANO_AYUDA, estilo.TEXTO_SECUNDARIO).pack(anchor="w")
    return cifra


def crear_tarjeta_resumen(app, padre):
    """
    Resumen de la decodificación en cifras grandes y el detalle de los descartes.
    Guarda: app.cifra_leidos, app.cifra_filas, app.cifra_descartados, app.cifra_tiempo,
            app.etiqueta_detalle_resumen.
    """
    tarjeta = crear_tarjeta(padre, "File summary")
    tarjeta.pack(fill="x", pady=(0, estilo.MARGEN))

    cifras = ctk.CTkFrame(tarjeta, fg_color="transparent")
    cifras.pack(fill="x")
    app.cifra_leidos = crear_cifra(cifras, 0, 0, "records read")
    app.cifra_filas = crear_cifra(cifras, 0, 1, "messages in the table")
    app.cifra_descartados = crear_cifra(cifras, 1, 0, "discarded")
    app.cifra_tiempo = crear_cifra(cifras, 1, 1, "seconds")

    app.etiqueta_detalle_resumen = crear_etiqueta(tarjeta, "Open an .ast file to see its summary.",
                                                  estilo.TAMANO_AYUDA, estilo.TEXTO_SECUNDARIO)
    app.etiqueta_detalle_resumen.configure(wraplength=estilo.ANCHO_PANEL_LATERAL - 40)
    app.etiqueta_detalle_resumen.pack(fill="x", padx=16, pady=(6, 14))


def crear_tarjeta_filtros(app, padre):
    """
    Filtros combinables.
    Guarda: app.selector_categoria, las casillas, app.entrada_altitud, app.entrada_aeronave,
            app.boton_aplicar y app.boton_quitar.
    """
    tarjeta = crear_tarjeta(padre, "Filters")
    tarjeta.pack(fill="x", pady=(0, estilo.MARGEN))

    crear_etiqueta(tarjeta, "ASTERIX category", estilo.TAMANO_TEXTO, estilo.TEXTO).pack(fill="x", padx=16)
    app.selector_categoria = crear_selector(tarjeta, ["Both", "CAT048", "CAT021"], None)
    app.selector_categoria.pack(fill="x", padx=16, pady=(4, 10))

    app.casilla_blancos_puros = crear_casilla(tarjeta, "Remove pure targets (CAT048)", None)
    app.casilla_blancos_puros.pack(fill="x", padx=16, pady=4)
    Tooltip(app.casilla_blancos_puros, "Removes the CAT048 messages that do not come from a Mode S interrogation: "
                                       "I048/020 TYP = 0, 1, 2 or 3 (no detection, PSR, SSR or PSR+SSR).")
    app.casilla_transponder_fijo = crear_casilla(tarjeta, "Remove fixed transponder (7777)", None)
    app.casilla_transponder_fijo.pack(fill="x", padx=16, pady=4)
    Tooltip(app.casilla_transponder_fijo, "Removes the messages with Mode 3/A 7777: "
                                          "a fixed reference transponder on the ground.")
    app.casilla_en_tierra = crear_casilla(tarjeta, "Remove aircraft on ground (CAT048)", None)
    app.casilla_en_tierra.pack(fill="x", padx=16, pady=4)
    Tooltip(app.casilla_en_tierra, "Removes the CAT048 messages with I048/230 STAT = 1 or 3 (on ground).")
    app.casilla_solo_fl = crear_casilla(tarjeta, "Only messages with FL", None)
    app.casilla_solo_fl.pack(fill="x", padx=16, pady=4)

    crear_etiqueta(tarjeta, "Maximum altitude (ft)", estilo.TAMANO_TEXTO, estilo.TEXTO).pack(
        fill="x", padx=16, pady=(10, 0))
    app.entrada_altitud = crear_entrada(tarjeta, 200, "For example: 6000")
    app.entrada_altitud.pack(fill="x", padx=16, pady=(4, 0))
    Tooltip(app.entrada_altitud, "Uses the QNH-corrected altitude or, if there is none, FL x 100. "
                                 "Messages with neither are removed.")

    crear_etiqueta(tarjeta, "Aircraft", estilo.TAMANO_TEXTO, estilo.TEXTO).pack(fill="x", padx=16, pady=(10, 0))
    app.entrada_aeronave = crear_entrada(tarjeta, 200, "Callsign, address or Mode 3/A")
    app.entrada_aeronave.pack(fill="x", padx=16, pady=(4, 0))
    Tooltip(app.entrada_aeronave, "Searches the text in the callsign (TI), the Mode S address (TA) "
                                  "or the Mode 3/A. For example, RYR finds every Ryanair flight.")

    app.entrada_altitud.bind("<Return>", app.aplicar_filtros_con_intro)
    app.entrada_aeronave.bind("<Return>", app.aplicar_filtros_con_intro)

    botones = ctk.CTkFrame(tarjeta, fg_color="transparent")
    botones.pack(fill="x", padx=16, pady=(14, 16))
    app.boton_aplicar = crear_boton_principal(botones, "Apply filters", app.aplicar_filtros, 130)
    app.boton_aplicar.pack(side="left")
    app.boton_quitar = crear_boton_secundario(botones, "Clear filters", app.quitar_filtros, 120)
    app.boton_quitar.pack(side="right")


def crear_tarjeta_exportar(app, padre):
    """
    Exportar a CSV.
    Guarda: app.boton_exportar_todo y app.boton_exportar_filtrado.
    """
    tarjeta = crear_tarjeta(padre, "Export to CSV")
    tarjeta.pack(fill="x")

    app.boton_exportar_todo = crear_boton_principal(tarjeta, "Export all", app.exportar_todo, 200)
    app.boton_exportar_todo.pack(fill="x", padx=16, pady=4)
    app.boton_exportar_filtrado = crear_boton_secundario(tarjeta, "Export filtered",
                                                         app.exportar_filtrado, 200)
    app.boton_exportar_filtrado.pack(fill="x", padx=16, pady=4)
    Tooltip(app.boton_exportar_filtrado, "Exports only the messages left after the filters. "
                                         "Enabled once a filter is applied.")
    crear_etiqueta(tarjeta, "';' separator and decimal comma", estilo.TAMANO_AYUDA, estilo.TEXTO_SUAVE).pack(
        fill="x", padx=16, pady=(2, 14))


def configurar_estilo_tabla(app):
    """
    Fuente, alto de fila y colores de las tablas (ttk.Treeview) de Datos y del panel de tráfico:
    cabecera un poco más clara que la tarjeta, filas alternas y selección en azul petróleo.
    El tema "clam" de ttk dibuja los bordes con tres colores (bordercolor, lightcolor y darkcolor)
    que por defecto son claros: se les ponen los de la paleta para que no quede ninguna línea blanca.
    Guarda: app.fuente_tabla y app.fuente_cabecera, que se usan para calcular los anchos.
    """
    app.fuente_tabla = tkinter.font.Font(family=estilo.FAMILIA, size=estilo.TAMANO_TABLA)
    app.fuente_cabecera = tkinter.font.Font(family=estilo.FAMILIA, size=estilo.TAMANO_TABLA, weight="bold")
    # El alto de fila sale de la fuente, para que se vea bien con cualquier escala de pantalla
    alto_fila = app.fuente_tabla.metrics("linespace") + 10

    tabla = ttk.Style(app.raiz)
    tabla.theme_use("clam")
    tabla.configure("Asterix.Treeview", font=app.fuente_tabla, rowheight=alto_fila,
                    background=estilo.TARJETA, fieldbackground=estilo.TARJETA,
                    foreground=estilo.TEXTO, borderwidth=0, bordercolor=estilo.BORDE,
                    lightcolor=estilo.TARJETA, darkcolor=estilo.TARJETA)
    tabla.map("Asterix.Treeview", background=[("selected", estilo.TABLA_SELECCION)],
              foreground=[("selected", estilo.TEXTO)])
    tabla.configure("Asterix.Treeview.Heading", font=app.fuente_cabecera, background=estilo.TABLA_CABECERA,
                    foreground=estilo.TEXTO, relief="flat", padding=(6, 8), bordercolor=estilo.BORDE,
                    lightcolor=estilo.TABLA_CABECERA, darkcolor=estilo.TABLA_CABECERA)
    tabla.map("Asterix.Treeview.Heading", background=[("active", estilo.TABLA_CABECERA)])


def crear_tarjeta_tabla(app, padre):
    """
    Tarjeta con la tabla de mensajes (todas las columnas del CSV), su paginación y lo que se
    pone en su sitio cuando está vacía o mientras se decodifica.
    Guarda: app.etiqueta_total y lo que guarda cada función de las que llama.
    """
    tarjeta = crear_tarjeta(padre, "")
    tarjeta.grid(row=0, column=1, sticky="nsew")

    encabezado = ctk.CTkFrame(tarjeta, fg_color="transparent")
    encabezado.pack(fill="x", padx=16, pady=(12, 8))
    ctk.CTkLabel(encabezado, text="Decoded messages", font=estilo.fuente(estilo.TAMANO_SECCION, True),
                 text_color=estilo.TEXTO).pack(side="left")
    app.etiqueta_total = crear_etiqueta(encabezado, "", estilo.TAMANO_TEXTO, estilo.TEXTO_SECUNDARIO)
    app.etiqueta_total.pack(side="right")

    marco = ctk.CTkFrame(tarjeta, fg_color="transparent")
    marco.pack(fill="both", expand=True, padx=(16, 10))
    marco.grid_rowconfigure(0, weight=1)
    marco.grid_columnconfigure(0, weight=1)

    # La tabla se crea antes que los dos avisos para que estos queden por encima al mostrarlos
    crear_tabla(app, marco)
    crear_estado_vacio_tabla(app, marco)
    crear_progreso_tabla(app, marco)
    crear_paginacion(app, tarjeta)


def crear_tabla(app, marco):
    """La tabla (ttk.Treeview) con una columna por columna del CSV y sus dos barras. Guarda: app.tabla."""
    configurar_estilo_tabla(app)
    app.tabla = ttk.Treeview(marco, columns=COLUMNAS, show="headings", style="Asterix.Treeview",
                             selectmode="browse")
    for columna in COLUMNAS:
        app.tabla.heading(columna, text=columna)
        app.tabla.column(columna, minwidth=40, stretch=False, anchor="center")
    ajustar_anchos_columnas(app, [])
    app.tabla.tag_configure("alterna", background=estilo.TABLA_FILA_ALTERNA)
    activar_desplazamiento_tabla(app.tabla)

    barra_vertical = crear_barra_desplazamiento(marco, "vertical", app.tabla.yview)
    barra_horizontal = crear_barra_desplazamiento(marco, "horizontal", app.tabla.xview)
    app.tabla.configure(yscrollcommand=barra_vertical.set, xscrollcommand=barra_horizontal.set)
    app.tabla.grid(row=0, column=0, sticky="nsew")
    barra_vertical.grid(row=0, column=1, sticky="ns")
    barra_horizontal.grid(row=1, column=0, sticky="ew")


def crear_estado_vacio_tabla(app, marco):
    """
    Mensaje que se pone encima de la tabla cuando no hay nada que mostrar (main.py dice cuál).
    Guarda: app.estado_vacio_tabla, app.etiqueta_vacio_tabla, app.boton_vacio_tabla.
    """
    app.estado_vacio_tabla = ctk.CTkFrame(marco, fg_color=estilo.TARJETA)
    app.etiqueta_vacio_tabla = ctk.CTkLabel(app.estado_vacio_tabla, text="",
                                            font=estilo.fuente(estilo.TAMANO_SECCION),
                                            text_color=estilo.TEXTO_SECUNDARIO, justify="center")
    app.etiqueta_vacio_tabla.pack(padx=30, pady=(24, 12))
    app.boton_vacio_tabla = crear_boton_principal(app.estado_vacio_tabla, "Open .ast file",
                                                  app.elegir_fichero, 180)
    app.boton_vacio_tabla.pack(pady=(0, 24))


def crear_progreso_tabla(app, marco):
    """
    Progreso grande de la decodificación, en el sitio de la tabla (main.py lo muestra y lo quita).
    Guarda: app.progreso_tabla, app.barra_progreso_tabla, app.etiqueta_progreso_tabla.
    """
    app.progreso_tabla = ctk.CTkFrame(marco, fg_color=estilo.TARJETA)
    app.barra_progreso_tabla = ctk.CTkProgressBar(app.progreso_tabla, width=ANCHO_BARRA_PROGRESO_TABLA, height=14,
                                                  fg_color=estilo.BORDE, progress_color=estilo.PRINCIPAL)
    app.barra_progreso_tabla.set(0)
    app.barra_progreso_tabla.pack(padx=30, pady=(28, 12))
    app.etiqueta_progreso_tabla = ctk.CTkLabel(app.progreso_tabla, text="", font=estilo.fuente(estilo.TAMANO_SECCION),
                                               text_color=estilo.TEXTO)
    app.etiqueta_progreso_tabla.pack(padx=30, pady=(0, 28))


def crear_paginacion(app, tarjeta):
    """
    Botones Anterior y Siguiente y la página actual.
    Guarda: app.boton_anterior, app.etiqueta_pagina, app.boton_siguiente.
    """
    paginacion = ctk.CTkFrame(tarjeta, fg_color="transparent")
    paginacion.pack(fill="x", padx=16, pady=(8, 12))
    app.boton_anterior = crear_boton_secundario(paginacion, "◀  Previous", app.pagina_anterior, 110)
    app.boton_anterior.pack(side="left")
    app.etiqueta_pagina = ctk.CTkLabel(paginacion, text="", width=150, font=estilo.fuente(estilo.TAMANO_TEXTO),
                                       text_color=estilo.TEXTO)
    app.etiqueta_pagina.pack(side="left", padx=8)
    app.boton_siguiente = crear_boton_secundario(paginacion, "Next  ▶", app.pagina_siguiente, 110)
    app.boton_siguiente.pack(side="left")


def ajustar_anchos_columnas(app, filas_formateadas):
    """
    Pone a cada columna el ancho de su texto más largo: la cabecera o alguno de los valores de
    filas_formateadas (listas de textos de celdas). Primero se busca el texto más largo por número
    de letras y solo se mide ese, para no hacer miles de medidas.
    """
    for posicion in range(len(COLUMNAS)):
        texto_mas_largo = ""
        for celdas in filas_formateadas:
            if len(celdas[posicion]) > len(texto_mas_largo):
                texto_mas_largo = celdas[posicion]
        ancho = app.fuente_cabecera.measure(COLUMNAS[posicion]) + MARGEN_COLUMNA
        ancho_valor = app.fuente_tabla.measure(texto_mas_largo) + MARGEN_COLUMNA
        if ancho_valor > ancho:
            ancho = ancho_valor
        if ancho > ANCHO_MAXIMO_COLUMNA:
            ancho = ANCHO_MAXIMO_COLUMNA
        app.tabla.column(COLUMNAS[posicion], width=ancho)


def crear_pestana_datos(app):
    """Pestaña Datos: panel izquierdo (resumen, filtros, exportar) y la tabla a la derecha."""
    pestana = app.pestana_datos
    pestana.grid_rowconfigure(0, weight=1)
    pestana.grid_columnconfigure(1, weight=1)

    panel = PanelDesplazable(pestana, width=estilo.ANCHO_PANEL_LATERAL, fg_color="transparent")
    panel.grid(row=0, column=0, sticky="ns", padx=(0, estilo.MARGEN))
    crear_tarjeta_resumen(app, panel)
    crear_tarjeta_filtros(app, panel)
    crear_tarjeta_exportar(app, panel)

    crear_tarjeta_tabla(app, pestana)


# =============================================================================
# Pestaña Simulación
# =============================================================================

def crear_controles_simulacion(app, padre):
    """
    Controles de la simulación en dos filas: arriba los botones y la velocidad; abajo las
    casillas y el sistema. Repartidos así caben en un portátil de 1280 píxeles de ancho.
    La hora, "Go to time" y la barra de tiempo van en su propia tarjeta (crear_tarjeta_tiempo).
    Lo que guarda cada parte está en su función.
    """
    tarjeta = crear_tarjeta(padre, "")
    tarjeta.grid(row=0, column=0, sticky="nsew", padx=(0, estilo.MARGEN), pady=(0, estilo.MARGEN))

    fila_1 = ctk.CTkFrame(tarjeta, fg_color="transparent")
    fila_1.pack(fill="x", padx=16, pady=(12, 5))
    crear_botones_reproduccion(app, fila_1)
    crear_selector_velocidad(app, fila_1)

    fila_2 = ctk.CTkFrame(tarjeta, fg_color="transparent")
    fila_2.pack(fill="x", padx=16, pady=(5, 12))
    crear_casillas_simulacion(app, fila_2)
    crear_selector_sistema(app, fila_2)
    crear_selector_mapa(app, fila_2)


def crear_botones_reproduccion(app, fila_1):
    """
    Reproducir, Pausa, +1 s y Reset.
    Guarda: app.boton_play, app.boton_pausa, app.boton_paso, app.boton_reset.
    """
    app.boton_play = crear_boton_principal(fila_1, "▶  Play", app.play, 120)
    app.boton_play.pack(side="left")
    Tooltip(app.boton_play, "Runs the simulation in steps of 1 s of time of day.")
    # Símbolos de texto normales: los de pausa y avance (⏸, ⏭) salen como emojis en Windows
    app.boton_pausa = crear_boton_secundario(fila_1, "❚❚  Pause", app.pausa, 92)
    app.boton_pausa.pack(side="left", padx=(8, 0))
    app.boton_paso = crear_boton_secundario(fila_1, "▶❚  +1 s", app.avanzar_un_segundo, 82)
    app.boton_paso.pack(side="left", padx=(8, 0))
    Tooltip(app.boton_paso, "Advances a single 1 s step.")
    app.boton_reset = crear_boton_secundario(fila_1, "⟲  Reset", app.reset_simulacion, 86)
    app.boton_reset.pack(side="left", padx=(8, 0))
    Tooltip(app.boton_reset, "Stops the simulation and goes back to the first time in the data.")


def crear_selector_velocidad(app, fila_1):
    """Selector de velocidad. Guarda: app.selector_velocidad."""
    # La ayuda de los selectores va en su etiqueta
    etiqueta_velocidad = crear_etiqueta(fila_1, "Speed", estilo.TAMANO_TEXTO, estilo.TEXTO)
    etiqueta_velocidad.pack(side="left", padx=(18, 6))
    Tooltip(etiqueta_velocidad, "Each step is always 1 s; the speed changes how often a step is drawn.")
    app.selector_velocidad = crear_selector(fila_1, ["x1", "x2", "x5", "x10", "x30", "x60"], app.cambiar_velocidad)
    app.selector_velocidad.pack(side="left")


def crear_selector_sistema(app, fila_2):
    """Selector Radar / ADS-B / Ambos. Guarda: app.selector_sistema."""
    etiqueta_sistema = crear_etiqueta(fila_2, "System", estilo.TAMANO_TEXTO, estilo.TEXTO)
    etiqueta_sistema.pack(side="left", padx=(24, 6))
    Tooltip(etiqueta_sistema, "Aircraft seen by the radar (CAT048), by ADS-B (CAT021) or by both. "
                              "It also filters the traffic lists.")
    app.selector_sistema = crear_selector(fila_2, ["Both", "Radar", "ADS-B"], app.cambiar_sistema)
    app.selector_sistema.pack(side="left")


def crear_selector_mapa(app, fila_2):
    """Selector del aspecto del mapa: Oscuro (el de la aplicación) o Claro (el original). Guarda: app.selector_mapa."""
    etiqueta_mapa = crear_etiqueta(fila_2, "Map", estilo.TAMANO_TEXTO, estilo.TEXTO)
    etiqueta_mapa.pack(side="left", padx=(20, 6))
    Tooltip(etiqueta_mapa, "Dark: the OpenStreetMap map darkened, so that the aircraft stand out. "
                           "Light: the original map.")
    app.selector_mapa = crear_selector(fila_2, ["Dark", "Light"], app.cambiar_mapa)
    app.selector_mapa.set("Light")              # al empezar, el mapa claro (MapaOSM empieza así)
    app.selector_mapa.pack(side="left")


def crear_casillas_simulacion(app, fila_2):
    """
    Casillas Etiquetas y Estelas (marcadas al empezar) y Seguir (sin marcar).
    Guarda: app.casilla_etiquetas, app.casilla_estelas, app.casilla_seguir.
    """
    app.casilla_etiquetas = crear_casilla(fila_2, "Labels", app.cambiar_etiquetas)
    app.casilla_etiquetas.select()
    app.casilla_etiquetas.pack(side="left")
    Tooltip(app.casilla_etiquetas, "Data block of each aircraft, as on a radar display: the callsign "
                                   "(or the Mode S address) and, below, the level in hundreds of feet with its "
                                   "trend and the ground speed (GS) in knots (no speed in ADS-B). If both "
                                   "systems see it, the label goes on the radar symbol. Aircraft on the "
                                   "ground and the fixed transponder have no label, unless selected. "
                                   "Pure targets show "
                                   "their type and number, for example PSR 45.")
    app.casilla_estelas = crear_casilla(fila_2, "Trails", app.cambiar_estelas)
    app.casilla_estelas.select()
    app.casilla_estelas.pack(side="left", padx=(16, 0))
    Tooltip(app.casilla_estelas, "Line with the last positions of each aircraft.")
    app.casilla_seguir = crear_casilla(fila_2, "Follow", app.cambiar_seguir)
    app.casilla_seguir.pack(side="left", padx=(16, 0))
    Tooltip(app.casilla_seguir, "Keeps the selected aircraft in the centre of the map, without changing the zoom. "
                                "If the aircraft disappears, following stops.")


def crear_tarjeta_tiempo(app, padre):
    """
    Hora del día de la simulación, grande y legible, con "Go to time" a su derecha y, debajo,
    la barra de tiempo, que va de la primera a la última hora de los datos.
    Guarda: app.etiqueta_reloj, app.entrada_hora, app.boton_ir, app.barra_tiempo,
            app.etiqueta_hora_inicio, app.etiqueta_hora_fin.
    """
    tarjeta = crear_tarjeta(padre, "")
    tarjeta.grid(row=0, column=1, sticky="nsew", pady=(0, estilo.MARGEN))

    fila_hora = ctk.CTkFrame(tarjeta, fg_color="transparent")
    fila_hora.pack(fill="x", padx=16, pady=(10, 0))
    reloj = ctk.CTkFrame(fila_hora, fg_color="transparent")
    reloj.pack(side="left")
    crear_etiqueta(reloj, "Simulation time (UTC)", estilo.TAMANO_AYUDA, estilo.TEXTO_SECUNDARIO).pack(anchor="w")
    app.etiqueta_reloj = ctk.CTkLabel(reloj, text="--:--:--",
                                      font=estilo.fuente_numeros(estilo.TAMANO_RELOJ, True),
                                      text_color=estilo.TEXTO, anchor="w", width=ANCHO_RELOJ)
    app.etiqueta_reloj.pack(anchor="w")

    ir_a_hora = ctk.CTkFrame(fila_hora, fg_color="transparent")
    ir_a_hora.pack(side="right", anchor="s", pady=(0, 4))
    crear_etiqueta(ir_a_hora, "Go to time", estilo.TAMANO_AYUDA, estilo.TEXTO_SECUNDARIO).pack(anchor="w")
    campos = ctk.CTkFrame(ir_a_hora, fg_color="transparent")
    campos.pack(anchor="w")
    app.entrada_hora = crear_entrada(campos, ANCHO_ENTRADA_HORA, "hh:mm")
    app.entrada_hora.pack(side="left")
    app.entrada_hora.bind("<Return>", app.ir_a_hora_con_intro)
    Tooltip(app.entrada_hora, "Type the time (UTC) as hh:mm and press Enter. Each aircraft appears at "
                              "its last known position before that time.")
    app.boton_ir = crear_boton_secundario(campos, "Go", app.ir_a_hora, 44)
    app.boton_ir.pack(side="left", padx=(6, 0))

    fila_barra = ctk.CTkFrame(tarjeta, fg_color="transparent")
    fila_barra.pack(fill="x", padx=16, pady=(4, 12))
    app.etiqueta_hora_inicio = crear_etiqueta(fila_barra, "--:--", estilo.TAMANO_AYUDA, estilo.TEXTO_SECUNDARIO)
    app.etiqueta_hora_inicio.pack(side="left")
    app.etiqueta_hora_fin = crear_etiqueta(fila_barra, "--:--", estilo.TAMANO_AYUDA, estilo.TEXTO_SECUNDARIO)
    app.etiqueta_hora_fin.pack(side="right")
    # Al arrastrar, command avisa de cada posición (el reloj enseña esa hora); el salto se hace
    # al soltar el ratón (<ButtonRelease-1>), no en cada movimiento, para que no se trabe.
    app.barra_tiempo = ctk.CTkSlider(fila_barra, from_=0, to=1, height=16, command=app.mover_barra_tiempo,
                                     fg_color=estilo.BORDE, progress_color=estilo.PRINCIPAL,
                                     button_color=estilo.PRINCIPAL, button_hover_color=estilo.PRINCIPAL_HOVER)
    app.barra_tiempo.set(0)
    app.barra_tiempo.pack(side="left", fill="x", expand=True, padx=8)
    app.barra_tiempo.bind("<ButtonRelease-1>", app.soltar_barra_tiempo, add="+")
    Tooltip(app.barra_tiempo, "Drag to go to another time: the clock shows the time and the jump is made on release.")


def configurar_barra_tiempo(app, inicio, fin, texto_inicio, texto_fin):
    """Pone la barra de tiempo de inicio a fin (segundos desde medianoche), en pasos de 1 s, con sus horas a los lados."""
    if fin <= inicio:
        fin = inicio + 1
    app.barra_tiempo.configure(from_=inicio, to=fin, number_of_steps=fin - inicio)
    app.barra_tiempo.set(inicio)
    cambiar_texto(app.etiqueta_hora_inicio, texto_inicio)
    cambiar_texto(app.etiqueta_hora_fin, texto_fin)


def crear_zona_mapa(app, padre):
    """
    Aviso de qué se simula y el mapa, que ocupa todo el alto que queda. Dentro del mapa, en las
    esquinas: la leyenda (abajo a la izquierda), la ventana de eventos (arriba a la derecha), la
    atribución de OpenStreetMap (abajo a la derecha) y, en el centro, el mensaje que se ve cuando no
    hay nada que mostrar.
    Guarda: app.etiqueta_aviso_simulacion, app.mapa, app.mensaje_mapa, app.etiqueta_mensaje_mapa
            y lo que guardan crear_leyenda_mapa y crear_ventana_eventos.
    """
    zona = ctk.CTkFrame(padre, fg_color="transparent")
    zona.grid(row=1, column=0, sticky="nsew", padx=(0, estilo.MARGEN))

    aviso = ctk.CTkFrame(zona, fg_color=estilo.AVISO_FONDO, corner_radius=estilo.RADIO_TARJETA)
    aviso.pack(fill="x", pady=(0, 8))
    app.etiqueta_aviso_simulacion = ctk.CTkLabel(aviso, text="", font=estilo.fuente(estilo.TAMANO_TEXTO),
                                                 text_color=estilo.AVISO_TEXTO, anchor="w", justify="left")
    app.etiqueta_aviso_simulacion.pack(fill="x", padx=16, pady=5)

    marco_mapa = ctk.CTkFrame(zona, fg_color=estilo.TARJETA, corner_radius=0, border_width=1,
                              border_color=estilo.BORDE)
    marco_mapa.pack(fill="both", expand=True)
    app.mapa = mapa.MapaOSM(marco_mapa, corner_radius=0)
    app.mapa.pack(fill="both", expand=True, padx=1, pady=1)

    # Lo que va encima del mapa se crea después del mapa, para que quede por encima
    crear_leyenda_mapa(app, marco_mapa)
    crear_ventana_eventos(app, marco_mapa)

    # Mensaje en el centro del mapa cuando no hay nada que ver (main.py dice cuál)
    app.mensaje_mapa = crear_tarjeta(marco_mapa, "")
    app.etiqueta_mensaje_mapa = ctk.CTkLabel(app.mensaje_mapa, text="", font=estilo.fuente(estilo.TAMANO_SECCION),
                                             text_color=estilo.TEXTO, justify="center")
    app.etiqueta_mensaje_mapa.pack(padx=28, pady=18)

    # Atribución que pide OpenStreetMap, en la esquina inferior derecha del mapa
    atribucion = tkinter.Label(marco_mapa, text=mapa.ATRIBUCION_MAPA, font=(estilo.FAMILIA, 8),
                               bg=estilo.FONDO_ATRIBUCION, fg=estilo.TEXTO_SECUNDARIO, padx=4)
    atribucion.place(relx=1.0, rely=1.0, x=-2, y=-2, anchor="se")


def crear_ventana_mapa(marco_mapa):
    """
    Recuadro que va encima del mapa (la leyenda y la ventana de eventos): del color de las tarjetas,
    con borde y sin esquinas redondeadas, porque sus esquinas no pueden ser transparentes sobre el mapa.
    """
    return ctk.CTkFrame(marco_mapa, fg_color=estilo.TARJETA, corner_radius=0, border_width=1,
                        border_color=estilo.CONTROL_BORDE)


class Plegable:
    """
    Título de un recuadro del mapa (leyenda o eventos) que, al pulsarlo, recoge o vuelve a mostrar
    su contenido. Empieza desplegado, para que se vea nada más abrir la pestaña; recogerlo sirve
    para ver más mapa en una pantalla pequeña. El contenido son los elementos colocados con grid():
    grid_remove() los quita y grid() los vuelve a poner donde estaban.
    """

    def __init__(self, padre, texto):
        self.texto = texto
        self.partes = []
        self.desplegado = True
        self.boton = ctk.CTkButton(padre, text="", command=self.cambiar, anchor="w", width=0,
                                   height=ALTO_TITULO_PLEGABLE, fg_color="transparent",
                                   hover_color=estilo.SECUNDARIO_HOVER, text_color=estilo.TEXTO,
                                   font=estilo.fuente(estilo.TAMANO_TEXTO, True))
        self.pintar()

    def anadir(self, parte):
        """Añade un elemento al contenido que se recoge."""
        self.partes.append(parte)

    def cambiar(self):
        """Clic en el título: recoge el contenido si se ve y al revés."""
        self.desplegado = not self.desplegado
        for parte in self.partes:
            if self.desplegado:
                parte.grid()
            else:
                parte.grid_remove()
        self.pintar()

    def pintar(self):
        """Flecha delante del título: ▾ desplegado, ▸ recogido."""
        if self.desplegado:
            self.boton.configure(text=FLECHA_DESPLEGADA + "  " + self.texto)
        else:
            self.boton.configure(text=FLECHA_RECOGIDA + "  " + self.texto)


def crear_fila_leyenda(padre, fila, columna, imagen, texto, ayuda):
    """
    Un elemento de la leyenda, en su fila y columna: la misma imagen que se dibuja en el mapa y lo que
    significa. Si se da 'ayuda', sale al dejar el ratón encima. Devuelve el elemento.
    """
    icono = ctk.CTkImage(light_image=imagen, size=(imagen.width, imagen.height))
    # height: CTkLabel mide 28 píxeles de alto si no se le dice otra cosa; con 20 la leyenda tapa menos mapa
    elemento = ctk.CTkLabel(padre, text="  " + texto, image=icono, compound="left", anchor="w", height=ALTO_FILA_LEYENDA,
                            font=estilo.fuente(estilo.TAMANO_AYUDA), text_color=estilo.TEXTO)
    elemento.grid(row=fila, column=columna, sticky="w", padx=(10, 6), pady=1)
    if ayuda != "":
        Tooltip(elemento, ayuda)
    return elemento


def crear_leyenda_mapa(app, marco_mapa):
    """
    Leyenda dentro del mapa, abajo a la izquierda, a la vista nada más abrir la pestaña. Usa las
    mismas imágenes que se dibujan en el mapa, en dos columnas para que ocupe poco, y debajo explica
    las etiquetas. Pulsando su título se recoge (Plegable), por si en un portátil tapa algo.
    """
    leyenda = crear_ventana_mapa(marco_mapa)
    leyenda.place(relx=0.0, rely=1.0, x=MARGEN_VENTANA_MAPA, y=-MARGEN_VENTANA_MAPA, anchor="sw")
    plegable = Plegable(leyenda, "Legend")
    plegable.boton.grid(row=0, column=0, columnspan=2, sticky="w", padx=4, pady=(4, 0))
    imagenes = app.imagenes_leyenda
    elementos = [
        (1, 0, imagenes["radar"], "Radar (CAT048)", ""),
        (1, 1, imagenes["adsb"], "ADS-B (CAT021)", ""),
        (2, 0, imagenes["resaltado"], "Selected and its pair",
         "The clicked aircraft and, if the other system also sees it, its symbol in that system."),
        (2, 1, imagenes["blanco_puro"], "Pure target (no Mode S)",
         "Primary or secondary radar echo, without Mode S. They are removed with “Remove pure targets” "
         "in the Data tab."),
        (3, 0, imagenes["transponder_fijo"], "Fixed transponder (7777)",
         "Reference transponder on the ground, always stationary."),
        (3, 1, imagenes["estacion"], "Barcelona radar", ""),
        (4, 0, imagenes["zona"], "Geographic filter limit",
         "Messages outside this rectangle are discarded when decoding."),
        (4, 1, imagenes["estela"], "Trail: last positions", ""),
    ]
    for fila, columna, imagen, texto, ayuda in elementos:
        plegable.anadir(crear_fila_leyenda(leyenda, fila, columna, imagen, texto, ayuda))
    # Tres líneas cortas escritas a mano, para que ninguna se parta a mitad de una idea
    explicacion = crear_etiqueta(leyenda,
                                 "Label: callsign and, below, level in hundreds of ft\n"
                                 "with its trend (" + simulacion.SUBE + " climbing, " + simulacion.BAJA + " descending, "
                                 + simulacion.NIVELADO + " level) and speed in kt.\n"
                                 "Aircraft on ground and 7777: no label, unless selected.",
                                 estilo.TAMANO_AYUDA, estilo.TEXTO_SECUNDARIO)
    explicacion.grid(row=5, column=0, columnspan=2, sticky="w", padx=10, pady=(2, 6))
    plegable.anadir(explicacion)


def configurar_estilo_eventos(app):
    """
    Estilo de la lista de eventos: letra de ancho fijo (como en una pantalla de control, para que
    las columnas queden alineadas) y filas más bajas que las de la tabla de Datos. Cada tipo de
    evento tiene su color (las etiquetas se configuran en crear_ventana_eventos).
    """
    app.fuente_eventos = tkinter.font.Font(family=estilo.FAMILIA_NUMEROS, size=estilo.TAMANO_TABLA)
    alto_fila = app.fuente_eventos.metrics("linespace") + 4
    eventos = ttk.Style(app.raiz)
    eventos.configure("Eventos.Treeview", font=app.fuente_eventos, rowheight=alto_fila,
                      background=estilo.TARJETA, fieldbackground=estilo.TARJETA,
                      foreground=estilo.TEXTO, borderwidth=0, bordercolor=estilo.BORDE,
                      lightcolor=estilo.TARJETA, darkcolor=estilo.TARJETA)
    eventos.map("Eventos.Treeview", background=[("selected", estilo.TABLA_SELECCION)])


def crear_ventana_eventos(app, marco_mapa):
    """
    Ventana de eventos dentro del mapa, arriba a la derecha, como la de mensajes de una pantalla radar:
    arriba, el título y los totales de despegues y aterrizajes; debajo, los eventos más recientes
    (hora, icono, tipo, callsign y sistema), con su barra de desplazamiento.
    Guarda: app.registro_eventos (RegistroEventos), app.etiqueta_totales_eventos.
    """
    configurar_estilo_eventos(app)
    ventana_eventos = crear_ventana_mapa(marco_mapa)
    ventana_eventos.place(relx=1.0, rely=0.0, x=-MARGEN_VENTANA_MAPA, y=MARGEN_VENTANA_MAPA, anchor="ne")
    ventana_eventos.grid_columnconfigure(0, weight=1)

    cabecera = ctk.CTkFrame(ventana_eventos, fg_color="transparent")
    cabecera.grid(row=0, column=0, columnspan=2, sticky="ew", padx=(4, 10), pady=(4, 0))
    plegable = Plegable(cabecera, "Events")
    plegable.boton.pack(side="left")
    Tooltip(plegable.boton, "New contact, takeoff, landing and contact lost, the most recent "
                            "on top. They appear when playing or stepping 1 s; when going to another time (Go to time, "
                            "the time bar or Reset) the list is cleared. Click an event: selects the "
                            "aircraft. Click the title: hides or shows the list.")
    app.etiqueta_totales_eventos = crear_etiqueta(cabecera, "Takeoffs: 0 · Landings: 0",
                                                  estilo.TAMANO_AYUDA, estilo.TEXTO_SECUNDARIO)
    app.etiqueta_totales_eventos.pack(side="right")
    Tooltip(app.etiqueta_totales_eventos, "Since playback started or since the last time jump. "
                                          "A takeoff or a landing is a status change confirmed by "
                                          + str(simulacion.MENSAJES_PARA_CAMBIAR_ESTADO) + " consecutive messages.")

    columnas = ("hora", "icono", "tipo", "callsign", "sistema")
    anchos = (ANCHO_EVENTO_HORA, ANCHO_EVENTO_ICONO, ANCHO_EVENTO_TIPO, ANCHO_EVENTO_CALLSIGN, ANCHO_EVENTO_SISTEMA)
    # show="": sin cabecera, para que quepan más eventos en poco alto
    tabla = ttk.Treeview(ventana_eventos, columns=columnas, show="", style="Eventos.Treeview", selectmode="browse",
                         height=FILAS_VENTANA_EVENTOS)
    for posicion in range(len(columnas)):
        tabla.column(columnas[posicion], width=anchos[posicion], minwidth=anchos[posicion], stretch=False,
                     anchor="w")
    tabla.column("icono", anchor="center")
    for tipo in ESTILO_EVENTO:
        etiqueta = ESTILO_EVENTO[tipo][0]
        color = ESTILO_EVENTO[tipo][2]
        tabla.tag_configure(etiqueta, foreground=color)
    tabla.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=(0, 8))
    barra = crear_barra_desplazamiento(ventana_eventos, "vertical", tabla.yview)
    barra.configure(width=ANCHO_BARRA_LISTA, height=ALTO_MINIMO_BARRA_LISTA)
    tabla.configure(yscrollcommand=barra.set)
    barra.grid(row=1, column=1, sticky="ns", padx=(0, 6), pady=(0, 8))
    plegable.anadir(tabla)
    plegable.anadir(barra)
    activar_desplazamiento_lista(tabla)
    tabla.bind("<ButtonRelease-1>", app.al_pulsar_evento)
    app.registro_eventos = RegistroEventos(tabla)


def crear_panel_simulacion(app, padre):
    """
    Panel derecho de la simulación, de arriba abajo: tráfico (lo que más se consulta) e información
    del avión seleccionado. La leyenda y los eventos van dentro del mapa. En pantallas bajas
    (portátiles) el panel se desplaza con la rueda del ratón o el panel táctil, como el de la
    pestaña Datos.
    """
    panel = PanelDesplazable(padre, width=estilo.ANCHO_PANEL_SIMULACION, fg_color="transparent")
    panel.grid(row=1, column=1, sticky="nsew")
    crear_tarjeta_trafico(app, panel)
    crear_tarjeta_avion(app, panel)


def crear_lista_trafico(app, padre, columna, columnas, titulos, anchos):
    """
    Una lista del panel de tráfico (ttk.Treeview con el estilo de la tabla de Datos) con su barra
    de desplazamiento, en la columna indicada de 'padre'. Al pulsar una fila se selecciona su avión.
    Devuelve la ListaIncremental que la pone al día.
    """
    marco = ctk.CTkFrame(padre, fg_color="transparent")
    marco.grid(row=1, column=columna, sticky="nsew")
    if columna == 0:
        marco.grid_configure(padx=(0, 8))           # separación entre las dos listas
    tabla = ttk.Treeview(marco, columns=columnas, show="headings", style="Asterix.Treeview",
                         selectmode="browse", height=FILAS_LISTA_TRAFICO)
    for posicion in range(len(columnas)):
        tabla.heading(columnas[posicion], text=titulos[posicion])
        tabla.column(columnas[posicion], width=anchos[posicion], minwidth=anchos[posicion], stretch=False,
                     anchor="center")
    tabla.column("callsign", anchor="w", stretch=True)
    tabla.heading("callsign", anchor="w")
    barra = crear_barra_desplazamiento(marco, "vertical", tabla.yview)
    barra.configure(width=ANCHO_BARRA_LISTA, height=ALTO_MINIMO_BARRA_LISTA)
    tabla.configure(yscrollcommand=barra.set)
    tabla.pack(side="left", fill="both", expand=True)
    barra.pack(side="left", fill="y")
    activar_desplazamiento_lista(tabla)
    tabla.bind("<ButtonRelease-1>", app.al_pulsar_fila_trafico)
    return ListaIncremental(tabla)


def crear_cifra_pequena(padre, color, texto_pie):
    """Una cifra del contador "En el mapa" (el número en color y lo que cuenta). Devuelve la etiqueta de la cifra."""
    cifra = ctk.CTkLabel(padre, text="0", font=estilo.fuente(estilo.TAMANO_TEXTO, True), text_color=color)
    cifra.pack(side="left", padx=(8, 3))
    crear_etiqueta(padre, texto_pie, estilo.TAMANO_AYUDA, estilo.TEXTO_SECUNDARIO).pack(side="left")
    return cifra


def crear_tarjeta_trafico(app, panel):
    """
    Panel de tráfico: dos contadores (en vuelo y en tierra), cada uno encima de su lista, y debajo
    las cifras de lo que hay dibujado en el mapa (radar, ADS-B y blancos puros).
    La lista En vuelo dice por qué sistema se ve cada avión ("Seen by": Radar, ADS-B o Ambos). La
    lista En tierra no lo necesita: en tierra solo lo ve el radar (el ADS-B en tierra se descarta).
    Guarda: app.contador_en_vuelo, app.contador_en_tierra, app.lista_en_vuelo, app.lista_en_tierra
            (ListaIncremental), app.cifra_radar, app.cifra_adsb, app.cifra_blancos_puros.
    """
    tarjeta = crear_tarjeta(panel, "Traffic")
    tarjeta.pack(fill="x", pady=(0, estilo.MARGEN))
    cuerpo = ctk.CTkFrame(tarjeta, fg_color="transparent")
    cuerpo.pack(fill="x", padx=12, pady=(0, 4))
    cuerpo.grid_columnconfigure(0, weight=1)

    app.contador_en_vuelo = ctk.CTkLabel(cuerpo, text="", font=estilo.fuente(estilo.TAMANO_CONTADOR, True),
                                         text_color=estilo.TRAFICO_EN_VUELO, anchor="w")
    app.contador_en_vuelo.grid(row=0, column=0, sticky="w", pady=(0, 4))
    app.contador_en_tierra = ctk.CTkLabel(cuerpo, text="", font=estilo.fuente(estilo.TAMANO_CONTADOR, True),
                                          text_color=estilo.TRAFICO_EN_TIERRA, anchor="w")
    app.contador_en_tierra.grid(row=0, column=1, sticky="w", pady=(0, 4))
    escribir_contadores_trafico(app, 0, 0)
    Tooltip(app.contador_en_vuelo, "Radar: by the STAT of I048/230 (0 and 2: airborne). Everything received "
                                   "by ADS-B is airborne. If both systems see it, the radar decides.")
    Tooltip(app.contador_en_tierra, "By the radar STAT of I048/230 (1 and 3: on ground). ADS-B aircraft on "
                                    "the ground (GBS = 1) do not appear: they are discarded when decoding.")

    app.lista_en_vuelo = crear_lista_trafico(app, cuerpo, 0, ("callsign", "nivel", "visto_por"),
                                             ("Callsign", "Level", "Seen by"),
                                             (ANCHO_COLUMNA_CALLSIGN, ANCHO_COLUMNA_NIVEL, ANCHO_COLUMNA_VISTO_POR))
    app.lista_en_tierra = crear_lista_trafico(app, cuerpo, 1, ("callsign",), ("Callsign",),
                                              (ANCHO_COLUMNA_CALLSIGN,))

    nota = crear_etiqueta(tarjeta, "Level, in hundreds of feet: A = QNH-corrected altitude, FL = flight "
                                   "level.", estilo.TAMANO_AYUDA, estilo.TEXTO_SUAVE)
    nota.configure(wraplength=estilo.ANCHO_PANEL_SIMULACION - 40)
    nota.pack(fill="x", padx=16, pady=(4, 0))

    en_el_mapa = ctk.CTkFrame(tarjeta, fg_color="transparent")
    en_el_mapa.pack(fill="x", padx=16, pady=(4, 12))
    etiqueta_mapa = crear_etiqueta(en_el_mapa, "On the map:", estilo.TAMANO_AYUDA, estilo.TEXTO_SECUNDARIO)
    etiqueta_mapa.pack(side="left")
    Tooltip(etiqueta_mapa, "Symbols drawn on the map with the chosen system. Pure targets do not "
                           "count as radar and the fixed transponder is not counted.")
    app.cifra_radar = crear_cifra_pequena(en_el_mapa, estilo.RADAR, "radar")
    app.cifra_adsb = crear_cifra_pequena(en_el_mapa, estilo.ADSB, "ADS-B")
    app.cifra_blancos_puros = crear_cifra_pequena(en_el_mapa, estilo.BLANCO_PURO, "pure targets")


def escribir_contadores_trafico(app, en_vuelo, en_tierra):
    """Textos de los contadores del panel de tráfico, por ejemplo "✈ 12 airborne" y "▣ 3 on ground"."""
    cambiar_texto(app.contador_en_vuelo, estilo.ICONO_EN_VUELO + "  " + str(en_vuelo) + " airborne")
    cambiar_texto(app.contador_en_tierra, estilo.ICONO_EN_TIERRA + "  " + str(en_tierra) + " on ground")


def crear_tarjeta_avion(app, panel):
    """
    Información del avión pulsado, con el selector Radar / ADS-B encima.
    El cuadro de texto tiene la altura justa para su versión más larga y no tiene barra propia:
    si no cabe en la pantalla, se ve desplazando el panel.
    Guarda: app.selector_sistema_avion, app.cuadro_info.
    """
    informacion = crear_tarjeta(panel, "Selected aircraft")
    informacion.pack(fill="x", pady=(0, estilo.MARGEN))
    # Radar / ADS-B: pasa a los datos del mismo avión visto por el otro sistema (main.py lo pone al día)
    app.selector_sistema_avion = crear_selector(informacion, ["Radar", "ADS-B"], app.cambiar_sistema_avion)
    app.selector_sistema_avion.pack(fill="x", padx=16, pady=(0, 8))
    cambiar_estado(app.selector_sistema_avion, False)      # al empezar no hay avión seleccionado

    fuente = estilo.fuente_numeros(estilo.TAMANO_AYUDA + 1)
    alto = LINEAS_INFO_AVION * fuente.metrics("linespace") + MARGEN_CUADRO_INFO
    app.cuadro_info = ctk.CTkTextbox(informacion, height=alto, wrap="word", fg_color=estilo.TARJETA,
                                     text_color=estilo.TEXTO, font=fuente, activate_scrollbars=False)
    app.cuadro_info.pack(fill="x", padx=12, pady=(0, 12))
    escribir_texto(app.cuadro_info, TEXTO_SIN_AVION)


def crear_pestana_simulacion(app):
    """Pestaña Simulación: controles y hora arriba; mapa (con la leyenda y los eventos dentro) y panel debajo."""
    pestana = app.pestana_simulacion
    pestana.grid_rowconfigure(1, weight=1)
    pestana.grid_columnconfigure(0, weight=1)
    pestana.grid_columnconfigure(1, minsize=estilo.ANCHO_PANEL_SIMULACION)

    crear_controles_simulacion(app, pestana)
    crear_tarjeta_tiempo(app, pestana)
    crear_zona_mapa(app, pestana)
    crear_panel_simulacion(app, pestana)
