"""
Crea y coloca los elementos de la ventana (lo que hacen los botones está en main.py y los
colores en estilo.py). Cada función guarda en app lo que main.py necesita después.
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
# Mínimo para que quepa en un portátil 1920x1080 al 150 % (quedan unos 1280x690)
ANCHO_MINIMO = 1100
ALTO_MINIMO = 600
# Se abre maximizada; al pulsar Restaurar ocupa esta fracción de la pantalla, centrada
FRACCION_VENTANA_RESTAURADA = 0.85
# Con customtkinter, maximizar nada más crear la ventana a veces no hace nada
ESPERA_MAXIMIZAR_MS = 100

# Columnas de la tabla (px): el ancho del texto más largo, con un tope
MARGEN_COLUMNA = 24
ANCHO_MAXIMO_COLUMNA = 220

# Anchos fijos (px) de cosas que cambian de texto, para que no muevan lo de al lado
ANCHO_BARRA_PROGRESO_TABLA = 560
ANCHO_RELOJ = 170

# Botones de los selectores, en píxeles
ALTO_SELECTOR = 28
ANCHO_MINIMO_OPCION = 44
RADIO_OPCION = 6
SEPARACION_OPCIONES = 4

# Pestañas de la cabecera (en forma de cápsula), en píxeles
ANCHO_PESTANA = 150
ALTO_PESTANA = 36
RADIO_PESTANA = 18              # mitad del alto, así los extremos salen redondos
MARGEN_PESTANAS = 4             # borde de la cápsula de fondo
TAMANO_ICONO_PESTANA = 18

# Cuadro "Selected aircraft": líneas del caso más largo (un avión de radar que es el 7777)
# y margen interior en px
LINEAS_INFO_AVION = 28
MARGEN_CUADRO_INFO = 20
TEXTO_SIN_AVION = "Click an aircraft on the map or in the traffic lists to see its details."

# Listas de tráfico: filas visibles sin desplazar y ancho de las columnas (px)
FILAS_LISTA_TRAFICO = 8
ANCHO_COLUMNA_CALLSIGN = 86
ANCHO_COLUMNA_NIVEL = 68
ANCHO_COLUMNA_VISTO_POR = 80
ANCHO_BARRA_LISTA = 12
# CTkScrollbar pide 200 px de alto si no se le da otro. Con uno pequeño se estira hasta el alto
# de la lista en vez de agrandar la tarjeta
ALTO_MINIMO_BARRA_LISTA = 40

# Recuadros encima del mapa (leyenda y eventos): margen con el borde y alto del título (px)
MARGEN_VENTANA_MAPA = 10
ALTO_TITULO_PLEGABLE = 24
ALTO_FILA_LEYENDA = 20
FLECHA_DESPLEGADA = "▾"
FLECHA_RECOGIDA = "▸"

# Ventana de eventos: filas visibles y ancho de las columnas (px)
FILAS_VENTANA_EVENTOS = 4
ANCHO_EVENTO_HORA = 66
ANCHO_EVENTO_ICONO = 20
ANCHO_EVENTO_TIPO = 146
ANCHO_EVENTO_CALLSIGN = 70          # justo para 8 caracteres de ancho fijo
ANCHO_EVENTO_SISTEMA = 50

# Tag de ttk, icono y color de cada tipo de evento
ESTILO_EVENTO = {
    simulacion.NUEVO_CONTACTO: ("contacto", estilo.EVENTO_CONTACTO_ICONO, estilo.EVENTO_CONTACTO_COLOR),
    simulacion.DESPEGA: ("despega", estilo.EVENTO_DESPEGA_ICONO, estilo.EVENTO_DESPEGA_COLOR),
    simulacion.ATERRIZA: ("aterriza", estilo.EVENTO_ATERRIZA_ICONO, estilo.EVENTO_ATERRIZA_COLOR),
    simulacion.PERDIDA_CONTACTO: ("perdida", estilo.EVENTO_PERDIDA_ICONO, estilo.EVENTO_PERDIDA_COLOR),
}

# Ancho del campo de "Go to time" (px)
ANCHO_ENTRADA_HORA = 70

# Barra de controles de la simulación: margen interior y separación entre grupos (px)
MARGEN_CONTROLES = 16
SEPARACION_GRUPOS_CONTROLES = 24

# Delta de la rueda que vale una unidad. Tabla: 120, un clic baja una fila (como Tk).
# Paneles: 6 por píxel, igual que customtkinter (20 px por clic).
PASO_DESPLAZAMIENTO_TABLA = 120
PASO_DESPLAZAMIENTO_PANEL = 6
# En horizontal la unidad es un píxel y con 120 un clic movía 1 px; con 3 se mueve 40
PASO_DESPLAZAMIENTO_TABLA_HORIZONTAL = 3

# Atributo de Windows para la barra de título oscura (el 19 es el de Windows 10 antiguos)
DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_USE_IMMERSIVE_DARK_MODE_ANTIGUO = 19

# Color original de cada botón, para devolvérselo al reactivarlo
COLOR_ORIGINAL_BOTONES = {}

# Último estado puesto a cada control (True = activo)
ESTADO_CONTROLES = {}


# =============================================================================
# Ventana principal
# =============================================================================

def crear_ventana_principal():
    """Crea la ventana principal en modo oscuro. Empieza escondida y se enseña ya maximizada."""
    ctk.set_appearance_mode("dark")
    raiz = ctk.CTk(fg_color=estilo.FONDO)
    raiz.title(TITULO)
    raiz.minsize(ANCHO_MINIMO, ALTO_MINIMO)
    poner_tamano_restaurado(raiz)
    raiz.withdraw()
    # after() no corre hasta que arranca mainloop(), o sea, con todo ya construido
    raiz.after(ESPERA_MAXIMIZAR_MS, mostrar_maximizada, raiz)
    return raiz


def poner_tamano_restaurado(raiz):
    """
    Tamaño y posición que toma la ventana al pulsar Restaurar (centrada).
    geometry() de customtkinter multiplica ancho y alto por la escala de Windows, pero no x e y:
    por eso el tamaño se divide por la escala y la posición va en píxeles reales.
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
    """Enseña la ventana maximizada ("zoomed", no pantalla completa: la barra de título se queda)."""
    raiz.state("zoomed")
    poner_barra_titulo_oscura(raiz)


def poner_barra_titulo_oscura(raiz):
    """
    Barra de título oscura con DwmSetWindowAttribute (dwmapi.dll, llamada con ctypes).
    Si falla, por ejemplo en un Windows viejo, la barra se queda como estaba.
    """
    try:
        ventana_windows = int(raiz.wm_frame(), 16)      # handle de la ventana
        valor = ctypes.c_int(1)                          # 1 = barra oscura
        for atributo in (DWMWA_USE_IMMERSIVE_DARK_MODE, DWMWA_USE_IMMERSIVE_DARK_MODE_ANTIGUO):
            resultado = ctypes.windll.dwmapi.DwmSetWindowAttribute(ventana_windows, atributo,
                                                                  ctypes.byref(valor), ctypes.sizeof(valor))
            if resultado == 0:                           # S_OK
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
    """Botón principal, relleno con el color de acento."""
    return ctk.CTkButton(padre, text=texto, command=comando, width=ancho, height=estilo.ALTO_BOTON,
                         font=estilo.fuente(estilo.TAMANO_TEXTO, True), fg_color=estilo.PRINCIPAL,
                         hover_color=estilo.PRINCIPAL_HOVER, text_color=estilo.TEXTO_SOBRE_PRINCIPAL,
                         text_color_disabled=estilo.DESACTIVADO_TEXTO)


def crear_boton_secundario(padre, texto, comando, ancho):
    """Botón secundario, solo con borde."""
    return ctk.CTkButton(padre, text=texto, command=comando, width=ancho, height=estilo.ALTO_BOTON,
                         font=estilo.fuente(estilo.TAMANO_TEXTO), fg_color="transparent",
                         hover_color=estilo.SECUNDARIO_HOVER, border_width=1,
                         border_color=estilo.CONTROL_BORDE, text_color=estilo.PRINCIPAL,
                         text_color_disabled=estilo.DESACTIVADO_TEXTO)


class Selector(ctk.CTkFrame):
    """
    Fila de botones con siempre una opción elegida. Se usa como CTkSegmentedButton (get, set y
    comando), pero está hecho a mano porque ese pone el mismo color de texto a todas las opciones.
    """

    def __init__(self, padre, valores, comando):
        super().__init__(padre, fg_color="transparent")
        self.comando = comando
        self.elegido = valores[0]
        self.activo = True
        self.botones = {}
        self.ayudas = {}                    # solo tienen texto las opciones desactivadas
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
        """Devuelve la función para el command del botón de 'valor'."""
        def al_pulsar():
            self.pulsar(valor)
        return al_pulsar

    def pulsar(self, valor):
        """Elige la opción pulsada y avisa a main.py, si no estaba ya elegida."""
        if valor == self.elegido:
            return
        self.set(valor)
        if self.comando is not None:
            self.comando(valor)

    def get(self):
        return self.elegido

    def set(self, valor):
        """Como CTkSegmentedButton.set: elige sin llamar al comando."""
        if valor == self.elegido:
            return
        self.elegido = valor
        self.pintar()

    def cambiar_estado(self, activo):
        self.activo = activo
        self.pintar()

    def cambiar_estado_opcion(self, valor, activa, ayuda):
        """
        Activa o desactiva una sola opción; desactivada, enseña 'ayuda' al pasar el ratón.
        Si no cambia nada no se redibuja, porque se llama en cada salto de la simulación.
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
        """Colores de cada opción según esté desactivada, elegida o no."""
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
    Pestañas de la cabecera: un Selector en forma de cápsula, con icono en cada pestaña.
    iconos: pestaña -> (icono si está elegida, icono si no).
    """

    def __init__(self, padre, valores, iconos, comando):
        self.iconos = iconos            # antes del super(): el Selector ya llama a pintar() al crearse
        super().__init__(padre, valores, comando)
        self.configure(fg_color=estilo.CABECERA_PESTANA, corner_radius=RADIO_PESTANA + MARGEN_PESTANAS)
        for valor in self.botones:
            # bg_color para que las esquinas de fuera sean del color de la cápsula y no de la cabecera
            self.botones[valor].configure(width=ANCHO_PESTANA, height=ALTO_PESTANA, corner_radius=RADIO_PESTANA,
                                          border_width=0, bg_color=estilo.CABECERA_PESTANA, compound="left",
                                          font=estilo.fuente(estilo.TAMANO_SECCION, True))
            self.botones[valor].pack_configure(pady=MARGEN_PESTANAS)
        # Margen también en los dos extremos
        self.botones[valores[0]].pack_configure(padx=(MARGEN_PESTANAS, 0))
        self.botones[valores[-1]].pack_configure(padx=(SEPARACION_OPCIONES, MARGEN_PESTANAS))

    def pintar(self):
        """La elegida va en el color de acento y la otra, del color de la cápsula."""
        for valor in self.botones:
            boton = self.botones[valor]
            if valor == self.elegido:
                boton.configure(fg_color=estilo.PRINCIPAL, hover_color=estilo.PRINCIPAL_HOVER,
                                text_color=estilo.TEXTO_SOBRE_PRINCIPAL, image=self.iconos[valor][0])
            else:
                boton.configure(fg_color=estilo.CABECERA_PESTANA, hover_color=estilo.CABECERA_PESTANA_HOVER,
                                text_color=estilo.CABECERA_PESTANA_TEXTO, image=self.iconos[valor][1])


def crear_iconos_pestanas():
    """Iconos de las pestañas, en dos colores (elegida y no elegida)."""
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
    """Devuelve un Selector con esas opciones."""
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
    """Barra de desplazamiento con los colores de la aplicación."""
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
        """Abre una ventanita sin bordes debajo del control (si hay texto)."""
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
    Va sumando los deltas de la rueda o del panel táctil y mueve una unidad cada 'paso'.
    El panel táctil manda deltas pequeños (10, 20...) que Tk y customtkinter pierden al dividirlos.
    """

    def __init__(self, paso):
        self.paso = paso
        self.acumulado = 0

    def unidades(self, delta):
        """Suma el delta y devuelve las unidades a mover (positivo: abajo o a la derecha)."""
        self.acumulado = self.acumulado - delta     # en Windows, delta negativo es bajar
        unidades = int(self.acumulado / self.paso)
        self.acumulado = self.acumulado - unidades * self.paso
        return unidades


def activar_desplazamiento_tabla(tabla):
    """Rueda y panel táctil en la tabla (en Windows el lateral llega como <Shift-MouseWheel>)."""
    vertical = Desplazador(PASO_DESPLAZAMIENTO_TABLA)
    horizontal = Desplazador(PASO_DESPLAZAMIENTO_TABLA_HORIZONTAL)

    def al_mover_vertical(evento):
        unidades = vertical.unidades(evento.delta)
        if unidades != 0:
            tabla.yview_scroll(unidades, "units")
        return "break"          # si no, Tk vuelve a desplazar por su cuenta

    def al_mover_horizontal(evento):
        unidades = horizontal.unidades(evento.delta)
        if unidades != 0:
            tabla.xview_scroll(unidades, "units")
        return "break"

    tabla.bind("<MouseWheel>", al_mover_vertical)
    tabla.bind("<Shift-MouseWheel>", al_mover_horizontal)


class PanelDesplazable(ctk.CTkScrollableFrame):
    """
    CTkScrollableFrame que también va con el panel táctil: se cambia su _mouse_wheel_all, que
    divide cada delta entre 6 y pierde los pequeños, por uno con Desplazador.
    """

    def __init__(self, padre, **opciones):
        super().__init__(padre, **opciones)
        self.configure(scrollbar_button_color=estilo.BARRA_DESPLAZAMIENTO,
                       scrollbar_button_hover_color=estilo.BARRA_DESPLAZAMIENTO_HOVER)
        self.desplazador = Desplazador(PASO_DESPLAZAMIENTO_PANEL)

    def _mouse_wheel_all(self, evento):
        """Llega con la rueda en cualquier sitio; solo desplaza si el ratón está sobre este panel."""
        if not self.check_if_master_is_canvas(evento.widget):
            return
        unidades = self.desplazador.unidades(evento.delta)
        if unidades != 0 and self._parent_canvas.yview() != (0.0, 1.0):
            self._parent_canvas.yview_scroll(unidades, "units")


def activar_desplazamiento_lista(lista):
    """Rueda en una lista de tráfico o eventos. Si le caben todas las filas, el evento pasa al panel."""
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
    Treeview de las listas de tráfico que solo toca las filas que cambian: rehacerlas enteras en
    cada salto (60 por segundo a x60) iba a tirones. La clave de cada fila es la TA del avión.
    """

    def __init__(self, tabla):
        self.tabla = tabla
        self.filas = {}             # clave -> (texto de orden, valores)

    def actualizar(self, filas_nuevas):
        """Deja en la lista justo filas_nuevas: borra, añade, cambia valores y reordena si hace falta."""
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
        """Callsign y, si hay empate, la clave."""
        return (self.filas[clave][0], clave)

    def ordenar(self):
        """Ordena por callsign moviendo las filas, sin borrarlas."""
        claves = sorted(self.filas.keys(), key=self.clave_de_orden)
        for posicion in range(len(claves)):
            self.tabla.move(claves[posicion], "", posicion)

    def seleccionar(self, clave):
        """Marca la fila de esa clave (con None, ninguna)."""
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
    Lista de eventos con el más nuevo arriba. Solo se añaden los nuevos y, pasados
    simulacion.EVENTOS_GUARDADOS, se van quitando los de abajo.
    """

    def __init__(self, tabla):
        self.tabla = tabla
        self.ta_por_fila = {}       # fila -> TA del avión, para seleccionarlo al pulsar

    def anadir(self, eventos):
        """Mete arriba los eventos nuevos y quita los que sobran por abajo."""
        for evento in eventos:
            etiqueta = ESTILO_EVENTO[evento["tipo"]][0]       # el color va en el tag
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
        """TA del avión de esa fila, o None."""
        return self.ta_por_fila.get(fila)

    def vaciar(self):
        """Quita todos los eventos."""
        filas = self.tabla.get_children()
        if len(filas) > 0:
            self.tabla.delete(*filas)
        self.ta_por_fila = {}


def cambiar_estado(elemento, activo):
    """
    Activa o desactiva un control (los botones desactivados se ven en gris).
    Si ya estaba así no se toca, porque customtkinter lo redibuja y parpadea.
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
    """True si el control está activo (al crearse lo están todos)."""
    return ESTADO_CONTROLES.get(elemento, True)


def cambiar_texto(etiqueta, texto):
    """Cambia el texto de la etiqueta solo si es otro, para no redibujarla porque sí."""
    if etiqueta.cget("text") != texto:
        etiqueta.configure(text=texto)


def escribir_texto(cuadro, texto):
    """Lo mismo para un cuadro de texto de solo lectura."""
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
    Cabecera con el título, las pestañas, el fichero cargado y el botón para abrir otro.
    Guarda app.selector_pestana, app.etiqueta_fichero y app.boton_abrir.
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
    """Barra de estado de abajo, con un punto de color, el mensaje y la barra de progreso."""
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
    """Zona central con las dos pestañas (app.pestana_datos y app.pestana_simulacion)."""
    contenido = ctk.CTkFrame(app.raiz, fg_color="transparent")
    contenido.pack(side="top", fill="both", expand=True, padx=estilo.MARGEN, pady=estilo.MARGEN)
    app.pestana_datos = ctk.CTkFrame(contenido, fg_color="transparent")
    app.pestana_simulacion = ctk.CTkFrame(contenido, fg_color="transparent")
    app.pestana_datos.pack(fill="both", expand=True)


# =============================================================================
# Pestaña Datos
# =============================================================================

def crear_cifra(padre, fila, columna, texto_pie):
    """Cifra grande con su texto debajo; devuelve la etiqueta de la cifra."""
    celda = ctk.CTkFrame(padre, fg_color="transparent")
    celda.grid(row=fila, column=columna, sticky="w", padx=(16, 8), pady=4)
    cifra = ctk.CTkLabel(celda, text="—", font=estilo.fuente_numeros(estilo.TAMANO_CIFRA, True),
                         text_color=estilo.TEXTO, anchor="w")
    cifra.pack(anchor="w")
    crear_etiqueta(celda, texto_pie, estilo.TAMANO_AYUDA, estilo.TEXTO_SECUNDARIO).pack(anchor="w")
    return cifra


def crear_tarjeta_resumen(app, padre):
    """Tarjeta del resumen: cuatro cifras grandes y debajo el detalle de los descartes."""
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
    """Tarjeta de filtros: categoría, casillas, altitud máxima, aeronave y los botones."""
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
    """Los dos botones de exportar a CSV."""
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
    Estilo de las tablas ttk de Datos y de tráfico. En el tema "clam" hay que dar bordercolor,
    lightcolor y darkcolor, o salen líneas blancas. Guarda app.fuente_tabla y app.fuente_cabecera.
    """
    app.fuente_tabla = tkinter.font.Font(family=estilo.FAMILIA, size=estilo.TAMANO_TABLA)
    app.fuente_cabecera = tkinter.font.Font(family=estilo.FAMILIA, size=estilo.TAMANO_TABLA, weight="bold")
    # Alto de fila a partir de la fuente, así vale con cualquier escala de pantalla
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
    """Tarjeta de la tabla de mensajes, con la paginación y los avisos que se ponen encima."""
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

    # La tabla va antes que los avisos para que estos queden encima
    crear_tabla(app, marco)
    crear_estado_vacio_tabla(app, marco)
    crear_progreso_tabla(app, marco)
    crear_paginacion(app, tarjeta)


def crear_tabla(app, marco):
    """Crea app.tabla, con todas las columnas del CSV y sus dos barras."""
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
    """Aviso que tapa la tabla cuando no hay nada que enseñar (el texto lo pone main.py)."""
    app.estado_vacio_tabla = ctk.CTkFrame(marco, fg_color=estilo.TARJETA)
    app.etiqueta_vacio_tabla = ctk.CTkLabel(app.estado_vacio_tabla, text="",
                                            font=estilo.fuente(estilo.TAMANO_SECCION),
                                            text_color=estilo.TEXTO_SECUNDARIO, justify="center")
    app.etiqueta_vacio_tabla.pack(padx=30, pady=(24, 12))
    app.boton_vacio_tabla = crear_boton_principal(app.estado_vacio_tabla, "Open .ast file",
                                                  app.elegir_fichero, 180)
    app.boton_vacio_tabla.pack(pady=(0, 24))


def crear_progreso_tabla(app, marco):
    """Barra de progreso grande que sale en lugar de la tabla mientras se decodifica."""
    app.progreso_tabla = ctk.CTkFrame(marco, fg_color=estilo.TARJETA)
    app.barra_progreso_tabla = ctk.CTkProgressBar(app.progreso_tabla, width=ANCHO_BARRA_PROGRESO_TABLA, height=14,
                                                  fg_color=estilo.BORDE, progress_color=estilo.PRINCIPAL)
    app.barra_progreso_tabla.set(0)
    app.barra_progreso_tabla.pack(padx=30, pady=(28, 12))
    app.etiqueta_progreso_tabla = ctk.CTkLabel(app.progreso_tabla, text="", font=estilo.fuente(estilo.TAMANO_SECCION),
                                               text_color=estilo.TEXTO)
    app.etiqueta_progreso_tabla.pack(padx=30, pady=(0, 28))


def crear_paginacion(app, tarjeta):
    """Botones Previous / Next con la página en medio."""
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
    Ancho de cada columna según su texto más largo (cabecera o celdas).
    Solo se mide el que tiene más letras, para no hacer miles de medidas.
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
    """Pestaña Datos: resumen, filtros y exportar a la izquierda y la tabla al lado."""
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
    Tarjeta de controles encima del mapa. Los grupos son hijos de la tarjeta y no de una fila,
    así ColocadorControles los puede cambiar de fila con pack(in_=...).
    """
    tarjeta = crear_tarjeta(padre, "")
    tarjeta.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=(0, estilo.MARGEN))

    # Filas antes que grupos: en tkinter lo último que se crea queda encima
    fila_1 = ctk.CTkFrame(tarjeta, fg_color="transparent")
    fila_1.pack(fill="x", padx=MARGEN_CONTROLES, pady=(12, 6))
    fila_vista = ctk.CTkFrame(tarjeta, fg_color="transparent")
    fila_tiempo = ctk.CTkFrame(tarjeta, fg_color="transparent")
    fila_tiempo.pack(fill="x", padx=MARGEN_CONTROLES, pady=(6, 12))

    grupo_reproduccion = ctk.CTkFrame(tarjeta, fg_color="transparent")
    crear_botones_reproduccion(app, grupo_reproduccion)
    grupo_velocidad = ctk.CTkFrame(tarjeta, fg_color="transparent")
    crear_selector_velocidad(app, grupo_velocidad)
    grupo_casillas = ctk.CTkFrame(tarjeta, fg_color="transparent")
    crear_casillas_simulacion(app, grupo_casillas)
    grupo_sistema = ctk.CTkFrame(tarjeta, fg_color="transparent")
    crear_selector_sistema(app, grupo_sistema)
    grupo_mapa = ctk.CTkFrame(tarjeta, fg_color="transparent")
    crear_selector_mapa(app, grupo_mapa)

    crear_linea_tiempo(app, fila_tiempo)

    colocador = ColocadorControles(tarjeta, fila_1, fila_vista, fila_tiempo,
                                   [grupo_reproduccion, grupo_velocidad],
                                   [grupo_casillas, grupo_sistema, grupo_mapa])
    tarjeta.bind("<Configure>", colocador.al_cambiar_tamano, add="+")


class ColocadorControles:
    """
    Pone los controles de vista en la fila 1 si caben y, si no (portátil o ventana estrecha),
    en una fila propia debajo. Solo recoloca cuando se pasa de un caso al otro.
    """

    def __init__(self, tarjeta, fila_1, fila_vista, fila_tiempo, grupos_reproduccion, grupos_vista):
        self.tarjeta = tarjeta
        self.fila_1 = fila_1
        self.fila_vista = fila_vista
        self.fila_tiempo = fila_tiempo
        self.grupos_reproduccion = grupos_reproduccion      # [reproducción, velocidad]
        self.grupos_vista = grupos_vista                    # [casillas, System, Map]
        self.en_una_fila = None                             # None hasta la primera colocación

    def ancho_necesario(self):
        """Píxeles que hacen falta para tenerlo todo en una fila."""
        # winfo_reqwidth() ya da píxeles reales, pero los padx los escala customtkinter
        escala = ctk.ScalingTracker.get_widget_scaling(self.tarjeta)
        ancho = 0
        for grupo in self.grupos_reproduccion + self.grupos_vista:
            ancho = ancho + grupo.winfo_reqwidth()
        separaciones = len(self.grupos_reproduccion + self.grupos_vista) - 1
        return ancho + int((separaciones * SEPARACION_GRUPOS_CONTROLES + 2 * MARGEN_CONTROLES) * escala)

    def al_cambiar_tamano(self, evento):
        """<Configure> de la tarjeta: mira si todo cabe en una fila."""
        cabe = self.tarjeta.winfo_width() >= self.ancho_necesario()
        if cabe == self.en_una_fila:
            return
        self.en_una_fila = cabe
        for grupo in self.grupos_reproduccion + self.grupos_vista:
            grupo.pack_forget()
        if cabe:
            self.colocar_en_una_fila()
        else:
            self.colocar_en_dos_filas()

    def colocar_en_una_fila(self):
        """Todo en la fila 1: reproducción y velocidad a la izquierda, vista a la derecha."""
        self.fila_vista.pack_forget()
        reproduccion, velocidad = self.grupos_reproduccion
        casillas, sistema, mapa_aspecto = self.grupos_vista
        reproduccion.pack(in_=self.fila_1, side="left")
        velocidad.pack(in_=self.fila_1, side="left", padx=(SEPARACION_GRUPOS_CONTROLES, 0))
        # side="right" coloca de derecha a izquierda: Map, System y luego las casillas
        mapa_aspecto.pack(in_=self.fila_1, side="right", padx=(SEPARACION_GRUPOS_CONTROLES, 0))
        sistema.pack(in_=self.fila_1, side="right", padx=(SEPARACION_GRUPOS_CONTROLES, 0))
        casillas.pack(in_=self.fila_1, side="right", padx=(SEPARACION_GRUPOS_CONTROLES, 0))

    def colocar_en_dos_filas(self):
        """Reproducción y velocidad en la fila 1; casillas, System y Map en la fila de debajo."""
        self.fila_vista.pack(fill="x", padx=MARGEN_CONTROLES, pady=(6, 6), before=self.fila_tiempo)
        reproduccion, velocidad = self.grupos_reproduccion
        casillas, sistema, mapa_aspecto = self.grupos_vista
        reproduccion.pack(in_=self.fila_1, side="left")
        velocidad.pack(in_=self.fila_1, side="right")
        casillas.pack(in_=self.fila_vista, side="left")
        mapa_aspecto.pack(in_=self.fila_vista, side="right")
        # expand=True sin fill: el grupo queda centrado en el espacio que dejan los otros dos
        sistema.pack(in_=self.fila_vista, side="left", expand=True)


def crear_botones_reproduccion(app, grupo):
    """Botones Play, Pause, +1 s y Reset."""
    app.boton_play = crear_boton_principal(grupo, "▶  Play", app.play, 120)
    app.boton_play.pack(side="left")
    Tooltip(app.boton_play, "Runs the simulation in steps of 1 s of time of day.")
    # ⏸ y ⏭ salen como emojis en Windows, por eso se usan estos símbolos
    app.boton_pausa = crear_boton_secundario(grupo, "❚❚  Pause", app.pausa, 92)
    app.boton_pausa.pack(side="left", padx=(8, 0))
    app.boton_paso = crear_boton_secundario(grupo, "▶❚  +1 s", app.avanzar_un_segundo, 82)
    app.boton_paso.pack(side="left", padx=(8, 0))
    Tooltip(app.boton_paso, "Advances a single 1 s step.")
    app.boton_reset = crear_boton_secundario(grupo, "⟲  Reset", app.reset_simulacion, 86)
    app.boton_reset.pack(side="left", padx=(8, 0))
    Tooltip(app.boton_reset, "Stops the simulation and goes back to the first time in the data.")


def crear_selector_velocidad(app, grupo):
    """Etiqueta "Speed" y el selector de x1 a x60."""
    # La ayuda de los selectores se pone en su etiqueta
    etiqueta_velocidad = crear_etiqueta(grupo, "Speed", estilo.TAMANO_TEXTO, estilo.TEXTO)
    etiqueta_velocidad.pack(side="left", padx=(0, 6))
    Tooltip(etiqueta_velocidad, "Each step is always 1 s; the speed changes how often a step is drawn.")
    app.selector_velocidad = crear_selector(grupo, ["x1", "x2", "x5", "x10", "x30", "x60"], app.cambiar_velocidad)
    app.selector_velocidad.pack(side="left")


def crear_selector_sistema(app, grupo):
    """Selector de sistema: Both, Radar o ADS-B."""
    etiqueta_sistema = crear_etiqueta(grupo, "System", estilo.TAMANO_TEXTO, estilo.TEXTO)
    etiqueta_sistema.pack(side="left", padx=(0, 6))
    Tooltip(etiqueta_sistema, "Aircraft seen by the radar (CAT048), by ADS-B (CAT021) or by both. "
                              "It also filters the traffic lists.")
    app.selector_sistema = crear_selector(grupo, ["Both", "Radar", "ADS-B"], app.cambiar_sistema)
    app.selector_sistema.pack(side="left")


def crear_selector_mapa(app, grupo):
    """Selector del mapa oscuro o claro."""
    etiqueta_mapa = crear_etiqueta(grupo, "Map", estilo.TAMANO_TEXTO, estilo.TEXTO)
    etiqueta_mapa.pack(side="left", padx=(0, 6))
    Tooltip(etiqueta_mapa, "Dark: the OpenStreetMap map darkened, so that the aircraft stand out. "
                           "Light: the original map.")
    app.selector_mapa = crear_selector(grupo, ["Dark", "Light"], app.cambiar_mapa)
    app.selector_mapa.set("Light")              # MapaOSM también empieza en claro
    app.selector_mapa.pack(side="left")


def crear_casillas_simulacion(app, grupo):
    """Casillas Labels y Trails (marcadas al empezar) y Follow."""
    app.casilla_etiquetas = crear_casilla(grupo, "Labels", app.cambiar_etiquetas)
    app.casilla_etiquetas.select()
    app.casilla_etiquetas.pack(side="left")
    Tooltip(app.casilla_etiquetas, "Data block of each aircraft, as on a radar display: the callsign "
                                   "(or the Mode S address) and, below, the level in hundreds of feet with its "
                                   "trend and the ground speed (GS) in knots (no speed in ADS-B). If both "
                                   "systems see it, the label goes on the radar symbol. Aircraft on the "
                                   "ground and the fixed transponder have no label, unless selected. "
                                   "Pure targets show "
                                   "their type and number, for example PSR 45.")
    app.casilla_estelas = crear_casilla(grupo, "Trails", app.cambiar_estelas)
    app.casilla_estelas.select()
    app.casilla_estelas.pack(side="left", padx=(16, 0))
    Tooltip(app.casilla_estelas, "Line with the last positions of each aircraft.")
    app.casilla_seguir = crear_casilla(grupo, "Follow", app.cambiar_seguir)
    app.casilla_seguir.pack(side="left", padx=(16, 0))
    Tooltip(app.casilla_seguir, "Keeps the selected aircraft in the centre of the map, without changing the zoom. "
                                "If the aircraft disappears, following stops.")


def crear_linea_tiempo(app, fila):
    """Fila del reloj, la barra de tiempo (con la primera y la última hora) y "Go to time"."""
    reloj = ctk.CTkFrame(fila, fg_color="transparent")
    reloj.pack(side="left")
    crear_etiqueta(reloj, "Simulation time (UTC)", estilo.TAMANO_AYUDA, estilo.TEXTO_SECUNDARIO).pack(anchor="w")
    app.etiqueta_reloj = ctk.CTkLabel(reloj, text="--:--:--",
                                      font=estilo.fuente_numeros(estilo.TAMANO_RELOJ, True),
                                      text_color=estilo.TEXTO, anchor="w", width=ANCHO_RELOJ)
    app.etiqueta_reloj.pack(anchor="w")

    ir_a_hora = ctk.CTkFrame(fila, fg_color="transparent")
    ir_a_hora.pack(side="right")
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

    # La barra va la última para que expand=True le dé todo el ancho que sobra
    barra = ctk.CTkFrame(fila, fg_color="transparent")
    barra.pack(side="left", fill="x", expand=True, padx=SEPARACION_GRUPOS_CONTROLES)
    app.etiqueta_hora_inicio = crear_etiqueta(barra, "--:--", estilo.TAMANO_AYUDA, estilo.TEXTO_SECUNDARIO)
    app.etiqueta_hora_inicio.pack(side="left")
    app.etiqueta_hora_fin = crear_etiqueta(barra, "--:--", estilo.TAMANO_AYUDA, estilo.TEXTO_SECUNDARIO)
    app.etiqueta_hora_fin.pack(side="right")
    # Al arrastrar solo cambia el reloj; el salto se hace al soltar, si no se traba
    app.barra_tiempo = ctk.CTkSlider(barra, from_=0, to=1, height=16, command=app.mover_barra_tiempo,
                                     fg_color=estilo.BORDE, progress_color=estilo.PRINCIPAL,
                                     button_color=estilo.PRINCIPAL, button_hover_color=estilo.PRINCIPAL_HOVER)
    app.barra_tiempo.set(0)
    app.barra_tiempo.pack(side="left", fill="x", expand=True, padx=8)
    app.barra_tiempo.bind("<ButtonRelease-1>", app.soltar_barra_tiempo, add="+")
    Tooltip(app.barra_tiempo, "Drag to go to another time: the clock shows the time and the jump is made on release.")


def configurar_barra_tiempo(app, inicio, fin, texto_inicio, texto_fin):
    """Ajusta la barra de tiempo de inicio a fin (segundos del día), de 1 s en 1 s."""
    if fin <= inicio:
        fin = inicio + 1
    app.barra_tiempo.configure(from_=inicio, to=fin, number_of_steps=fin - inicio)
    app.barra_tiempo.set(inicio)
    cambiar_texto(app.etiqueta_hora_inicio, texto_inicio)
    cambiar_texto(app.etiqueta_hora_fin, texto_fin)


def crear_zona_mapa(app, padre):
    """
    Aviso de qué se simula y el mapa, con la leyenda, los eventos y la atribución encima.
    Guarda app.mapa, app.mensaje_mapa y app.etiqueta_aviso_simulacion, entre otros.
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

    # Después del mapa, para que quede encima
    crear_leyenda_mapa(app, marco_mapa)
    crear_ventana_eventos(app, marco_mapa)

    # Mensaje del centro cuando no hay nada que ver (el texto lo pone main.py)
    app.mensaje_mapa = crear_tarjeta(marco_mapa, "")
    app.etiqueta_mensaje_mapa = ctk.CTkLabel(app.mensaje_mapa, text="", font=estilo.fuente(estilo.TAMANO_SECCION),
                                             text_color=estilo.TEXTO, justify="center")
    app.etiqueta_mensaje_mapa.pack(padx=28, pady=18)

    # OpenStreetMap pide poner la atribución
    atribucion = tkinter.Label(marco_mapa, text=mapa.ATRIBUCION_MAPA, font=(estilo.FAMILIA, 8),
                               bg=estilo.FONDO_ATRIBUCION, fg=estilo.TEXTO_SECUNDARIO, padx=4)
    atribucion.place(relx=1.0, rely=1.0, x=-2, y=-2, anchor="se")


def crear_ventana_mapa(marco_mapa):
    """Recuadro para encima del mapa, sin esquinas redondeadas (no pueden ser transparentes ahí)."""
    return ctk.CTkFrame(marco_mapa, fg_color=estilo.TARJETA, corner_radius=0, border_width=1,
                        border_color=estilo.CONTROL_BORDE)


class Plegable:
    """
    Título de un recuadro del mapa que recoge o enseña su contenido al pulsarlo (empieza abierto).
    Las partes van con grid(), así grid_remove() y grid() las dejan en su sitio.
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
        """Añade una parte al contenido plegable."""
        self.partes.append(parte)

    def cambiar(self):
        """Recoge o despliega."""
        self.desplegado = not self.desplegado
        for parte in self.partes:
            if self.desplegado:
                parte.grid()
            else:
                parte.grid_remove()
        self.pintar()

    def pintar(self):
        """Pone la flecha (▾ o ▸) delante del título."""
        if self.desplegado:
            self.boton.configure(text=FLECHA_DESPLEGADA + "  " + self.texto)
        else:
            self.boton.configure(text=FLECHA_RECOGIDA + "  " + self.texto)


def crear_fila_leyenda(padre, fila, columna, imagen, texto, ayuda):
    """Un elemento de la leyenda (imagen y texto, con ayuda si se da). Lo devuelve."""
    icono = ctk.CTkImage(light_image=imagen, size=(imagen.width, imagen.height))
    # CTkLabel mide 28 px de alto por defecto; con 20 la leyenda tapa menos mapa
    elemento = ctk.CTkLabel(padre, text="  " + texto, image=icono, compound="left", anchor="w", height=ALTO_FILA_LEYENDA,
                            font=estilo.fuente(estilo.TAMANO_AYUDA), text_color=estilo.TEXTO)
    elemento.grid(row=fila, column=columna, sticky="w", padx=(10, 6), pady=1)
    if ayuda != "":
        Tooltip(elemento, ayuda)
    return elemento


def crear_leyenda_mapa(app, marco_mapa):
    """Leyenda abajo a la izquierda del mapa: dos columnas de símbolos y la explicación de las etiquetas."""
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
    # Saltos de línea a mano para que no se corte a mitad de frase
    explicacion = crear_etiqueta(leyenda,
                                 "Label: callsign and, below, level in hundreds of ft\n"
                                 "with its trend (" + simulacion.SUBE + " climbing, " + simulacion.BAJA + " descending, "
                                 + simulacion.NIVELADO + " level) and speed in kt.\n"
                                 "Aircraft on ground and 7777: no label, unless selected.",
                                 estilo.TAMANO_AYUDA, estilo.TEXTO_SECUNDARIO)
    explicacion.grid(row=5, column=0, columnspan=2, sticky="w", padx=10, pady=(2, 6))
    plegable.anadir(explicacion)


def configurar_estilo_eventos(app):
    """Estilo de la lista de eventos: letra de ancho fijo para que cuadren las columnas y filas más bajas."""
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
    Ventana de eventos arriba a la derecha del mapa: título, totales y la lista.
    Guarda app.registro_eventos y app.etiqueta_totales_eventos.
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
    # Sin cabecera, así caben más filas
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
    """Panel derecho con el tráfico y el avión seleccionado; se desplaza si la pantalla es baja."""
    panel = PanelDesplazable(padre, width=estilo.ANCHO_PANEL_SIMULACION, fg_color="transparent")
    panel.grid(row=1, column=1, sticky="nsew")
    crear_tarjeta_trafico(app, panel)
    crear_tarjeta_avion(app, panel)


def crear_lista_trafico(app, padre, columna, columnas, titulos, anchos):
    """Crea una lista de tráfico con su barra en esa columna y devuelve su ListaIncremental."""
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
    """Número en color con su texto, para la línea "On the map". Devuelve la etiqueta del número."""
    cifra = ctk.CTkLabel(padre, text="0", font=estilo.fuente(estilo.TAMANO_TEXTO, True), text_color=color)
    cifra.pack(side="left", padx=(8, 3))
    crear_etiqueta(padre, texto_pie, estilo.TAMANO_AYUDA, estilo.TEXTO_SECUNDARIO).pack(side="left")
    return cifra


def crear_tarjeta_trafico(app, panel):
    """
    Tarjeta Traffic: contadores y listas en vuelo / en tierra, y lo que hay dibujado en el mapa.
    La de tierra no lleva "Seen by" porque el ADS-B en tierra se descarta.
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
    """Pone los contadores, p. ej. "✈ 12 airborne" y "▣ 3 on ground"."""
    cambiar_texto(app.contador_en_vuelo, estilo.ICONO_EN_VUELO + "  " + str(en_vuelo) + " airborne")
    cambiar_texto(app.contador_en_tierra, estilo.ICONO_EN_TIERRA + "  " + str(en_tierra) + " on ground")


def crear_tarjeta_avion(app, panel):
    """
    Tarjeta del avión seleccionado, con el selector Radar / ADS-B. El cuadro tiene el alto justo
    para el caso más largo y no lleva barra: si no cabe, se desplaza el panel.
    """
    informacion = crear_tarjeta(panel, "Selected aircraft")
    informacion.pack(fill="x", pady=(0, estilo.MARGEN))
    # Para ver el mismo avión con el otro sistema
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
    """Pestaña Simulación: controles arriba y, debajo, el mapa y el panel."""
    pestana = app.pestana_simulacion
    pestana.grid_rowconfigure(1, weight=1)
    pestana.grid_columnconfigure(0, weight=1)
    pestana.grid_columnconfigure(1, minsize=estilo.ANCHO_PANEL_SIMULACION)

    crear_controles_simulacion(app, pestana)
    crear_zona_mapa(app, pestana)
    crear_panel_simulacion(app, pestana)
