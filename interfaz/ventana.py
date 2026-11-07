"""
ventana.py

Construcción de la ventana (R15-R17). Aquí solo se crean y se colocan los elementos;
lo que hace cada botón está en main.py y los colores y tipografías, en estilo.py.

Cada función recibe la aplicación (app) y guarda en ella los elementos que main.py
usa después, por ejemplo app.boton_abrir o app.tabla.

    cabecera:         título, grupo, selector de pestaña, fichero cargado y "Abrir fichero"
    pestaña Datos:    resumen, filtros y exportar a la izquierda; tabla por páginas a la derecha
    pestaña Simulación: controles y reloj arriba, aviso de qué se simula, mapa y panel lateral
    barra de estado:  qué está pasando y barra de progreso
"""

import tkinter
import tkinter.font
from tkinter import ttk

import customtkinter as ctk

from funciones.exportar_csv import COLUMNAS
from interfaz import estilo
from interfaz import mapa

TITULO = "Decodificador ASTERIX CAT048 / CAT021 - PGTA Proyecto 2"
ANCHO_MINIMO = 1200
ALTO_MINIMO = 720

# Ancho de las columnas de la tabla (píxeles): el del texto más largo, con un máximo
MARGEN_COLUMNA = 24
ANCHO_MAXIMO_COLUMNA = 220

# Anchos fijos (píxeles) de lo que cambia mientras se trabaja, para que no empuje a nada
ANCHO_BARRA_PROGRESO_TABLA = 560
ANCHO_RELOJ = 230

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

# Color de fondo original de cada botón, para devolvérselo al activarlo (ver cambiar_estado)
COLOR_ORIGINAL_BOTONES = {}

# Último estado (True activo, False desactivado) aplicado a cada control (ver cambiar_estado)
ESTADO_CONTROLES = {}


# =============================================================================
# Ventana principal
# =============================================================================

def crear_ventana_principal():
    """Crea la ventana principal en modo claro, maximizada (R16)."""
    ctk.set_appearance_mode("light")
    raiz = ctk.CTk(fg_color=estilo.FONDO)
    raiz.title(TITULO)
    raiz.minsize(ANCHO_MINIMO, ALTO_MINIMO)
    # "zoomed" maximiza la ventana en Windows; con after() se aplica cuando ya existe
    raiz.after(0, raiz.state, "zoomed")
    return raiz


# =============================================================================
# Piezas que se repiten
# =============================================================================

def crear_tarjeta(padre, titulo):
    """Tarjeta blanca con borde suave y, si se da, un título de sección."""
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
    """Botón de la acción principal de cada zona: relleno azul."""
    return ctk.CTkButton(padre, text=texto, command=comando, width=ancho, height=estilo.ALTO_BOTON,
                         font=estilo.fuente(estilo.TAMANO_TEXTO, True), fg_color=estilo.PRINCIPAL,
                         hover_color=estilo.PRINCIPAL_HOVER, text_color="white",
                         text_color_disabled=estilo.DESACTIVADO_TEXTO)


def crear_boton_secundario(padre, texto, comando, ancho):
    """Botón de una acción secundaria: solo el borde, más discreto."""
    return ctk.CTkButton(padre, text=texto, command=comando, width=ancho, height=estilo.ALTO_BOTON,
                         font=estilo.fuente(estilo.TAMANO_TEXTO), fg_color="transparent",
                         hover_color=estilo.SECUNDARIO_HOVER, border_width=1,
                         border_color=estilo.BORDE, text_color=estilo.PRINCIPAL,
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
        """La pestaña elegida, en el azul principal con texto blanco; la otra, del color de la cápsula."""
        for valor in self.botones:
            boton = self.botones[valor]
            if valor == self.elegido:
                boton.configure(fg_color=estilo.PRINCIPAL, hover_color=estilo.PRINCIPAL_HOVER,
                                text_color=estilo.CABECERA_TEXTO, image=self.iconos[valor][0])
            else:
                boton.configure(fg_color=estilo.CABECERA_PESTANA, hover_color=estilo.CABECERA_PESTANA_HOVER,
                                text_color=estilo.CABECERA_PESTANA_TEXTO, image=self.iconos[valor][1])


def crear_iconos_pestanas():
    """Iconos de las pestañas: blancos para la elegida y del color suave para la otra (dibujados en mapa.py)."""
    tamano = TAMANO_ICONO_PESTANA
    tabla = mapa.dibujar_icono_tabla(estilo.CABECERA_TEXTO, tamano)
    tabla_suave = mapa.dibujar_icono_tabla(estilo.CABECERA_PESTANA_TEXTO, tamano)
    avion = mapa.dibujar_icono_avion(estilo.CABECERA_TEXTO, tamano)
    avion_suave = mapa.dibujar_icono_avion(estilo.CABECERA_PESTANA_TEXTO, tamano)
    return {
        "Datos": (ctk.CTkImage(light_image=tabla, size=(tamano, tamano)),
                  ctk.CTkImage(light_image=tabla_suave, size=(tamano, tamano))),
        "Simulación": (ctk.CTkImage(light_image=avion, size=(tamano, tamano)),
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
                           checkbox_width=20, checkbox_height=20)


def crear_entrada(padre, ancho, ejemplo):
    """Campo de texto con un ejemplo en gris mientras está vacío."""
    return ctk.CTkEntry(padre, width=ancho, placeholder_text=ejemplo, font=estilo.fuente(estilo.TAMANO_TEXTO),
                        fg_color=estilo.TARJETA, border_color=estilo.BORDE, text_color=estilo.TEXTO)


class Tooltip:
    """Texto de ayuda que aparece al dejar el ratón sobre un control (R15)."""

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


def cambiar_estado(elemento, activo):
    """
    Activa o desactiva un control. Los botones desactivados se ponen en gris para que se vea
    que no se pueden pulsar (R15); al activarlos recuperan su color original.
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
    ctk.CTkLabel(titulos, text="Decodificador ASTERIX", font=estilo.fuente(estilo.TAMANO_TITULO, True),
                 text_color=estilo.CABECERA_TEXTO, anchor="w").pack(anchor="w")
    ctk.CTkLabel(titulos, text="CAT048 · CAT021     PGTA · Grupo G2", font=estilo.fuente(estilo.TAMANO_AYUDA),
                 text_color=estilo.CABECERA_TEXTO_SUAVE, anchor="w").pack(anchor="w")

    app.selector_pestana = Pestanas(cabecera, ["Datos", "Simulación"], crear_iconos_pestanas(), app.cambiar_pestana)
    app.selector_pestana.grid(row=0, column=1)

    derecha = ctk.CTkFrame(cabecera, fg_color="transparent")
    derecha.grid(row=0, column=2, sticky="e", padx=20)
    app.etiqueta_fichero = ctk.CTkLabel(derecha, text="Ningún fichero cargado",
                                        font=estilo.fuente(estilo.TAMANO_TEXTO),
                                        text_color=estilo.CABECERA_TEXTO_SUAVE)
    app.etiqueta_fichero.pack(side="left", padx=(0, 14))
    app.boton_abrir = crear_boton_principal(derecha, "Abrir fichero .ast", app.elegir_fichero, 160)
    app.boton_abrir.pack(side="left")
    Tooltip(app.boton_abrir, "Elige un fichero ASTERIX (.ast) con mensajes CAT048 y/o CAT021.")


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
    app.etiqueta_estado = crear_etiqueta(barra, "Abre un fichero .ast para empezar",
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
    tarjeta = crear_tarjeta(padre, "Resumen del fichero")
    tarjeta.pack(fill="x", pady=(0, estilo.MARGEN))

    cifras = ctk.CTkFrame(tarjeta, fg_color="transparent")
    cifras.pack(fill="x")
    app.cifra_leidos = crear_cifra(cifras, 0, 0, "registros leídos")
    app.cifra_filas = crear_cifra(cifras, 0, 1, "mensajes en la tabla")
    app.cifra_descartados = crear_cifra(cifras, 1, 0, "descartados")
    app.cifra_tiempo = crear_cifra(cifras, 1, 1, "segundos")

    app.etiqueta_detalle_resumen = crear_etiqueta(tarjeta, "Abre un fichero .ast para ver el resumen.",
                                                  estilo.TAMANO_AYUDA, estilo.TEXTO_SECUNDARIO)
    app.etiqueta_detalle_resumen.configure(wraplength=estilo.ANCHO_PANEL_LATERAL - 40)
    app.etiqueta_detalle_resumen.pack(fill="x", padx=16, pady=(6, 14))


def crear_tarjeta_filtros(app, padre):
    """
    Filtros combinables (R34-R39).
    Guarda: app.selector_categoria, las casillas, app.entrada_altitud, app.entrada_aeronave,
            app.boton_aplicar y app.boton_quitar.
    """
    tarjeta = crear_tarjeta(padre, "Filtros")
    tarjeta.pack(fill="x", pady=(0, estilo.MARGEN))

    crear_etiqueta(tarjeta, "Categoría ASTERIX", estilo.TAMANO_TEXTO, estilo.TEXTO).pack(fill="x", padx=16)
    app.selector_categoria = crear_selector(tarjeta, ["Ambas", "CAT048", "CAT021"], None)
    app.selector_categoria.pack(fill="x", padx=16, pady=(4, 10))

    app.casilla_blancos_puros = crear_casilla(tarjeta, "Quitar blancos puros (CAT048)", None)
    app.casilla_blancos_puros.pack(fill="x", padx=16, pady=4)
    Tooltip(app.casilla_blancos_puros, "Quita los mensajes CAT048 que no vienen de una interrogación "
                                       "Modo S: I048/020 TYP = 0, 1, 2 o 3 (sin detección, PSR, SSR, SSR + PSR).")
    app.casilla_transponder_fijo = crear_casilla(tarjeta, "Quitar transponder fijo (7777)", None)
    app.casilla_transponder_fijo.pack(fill="x", padx=16, pady=4)
    Tooltip(app.casilla_transponder_fijo, "Quita los mensajes con Modo 3/A 7777 o con el bit RAB = 1: "
                                          "un transponder fijo de referencia en tierra.")
    app.casilla_en_tierra = crear_casilla(tarjeta, "Quitar aeronaves en tierra (CAT048)", None)
    app.casilla_en_tierra.pack(fill="x", padx=16, pady=4)
    Tooltip(app.casilla_en_tierra, "Quita los mensajes CAT048 con I048/230 STAT = 1 o 3 (en tierra).")
    app.casilla_solo_fl = crear_casilla(tarjeta, "Solo mensajes con FL", None)
    app.casilla_solo_fl.pack(fill="x", padx=16, pady=4)

    crear_etiqueta(tarjeta, "Altitud máxima (ft)", estilo.TAMANO_TEXTO, estilo.TEXTO).pack(
        fill="x", padx=16, pady=(10, 0))
    app.entrada_altitud = crear_entrada(tarjeta, 200, "Por ejemplo: 6000")
    app.entrada_altitud.pack(fill="x", padx=16, pady=(4, 0))
    Tooltip(app.entrada_altitud, "Usa la altitud corregida por QNH y, si no la hay, FL x 100. "
                                 "Los mensajes sin ninguna de las dos se quitan.")

    crear_etiqueta(tarjeta, "Aeronave", estilo.TAMANO_TEXTO, estilo.TEXTO).pack(fill="x", padx=16, pady=(10, 0))
    app.entrada_aeronave = crear_entrada(tarjeta, 200, "Callsign, dirección o Modo 3/A")
    app.entrada_aeronave.pack(fill="x", padx=16, pady=(4, 0))
    Tooltip(app.entrada_aeronave, "Busca el texto dentro del callsign (TI), la dirección Modo S (TA) "
                                  "o el Modo 3/A. Por ejemplo, RYR encuentra todos los Ryanair.")

    app.entrada_altitud.bind("<Return>", app.aplicar_filtros_con_intro)
    app.entrada_aeronave.bind("<Return>", app.aplicar_filtros_con_intro)

    botones = ctk.CTkFrame(tarjeta, fg_color="transparent")
    botones.pack(fill="x", padx=16, pady=(14, 16))
    app.boton_aplicar = crear_boton_principal(botones, "Aplicar filtros", app.aplicar_filtros, 130)
    app.boton_aplicar.pack(side="left")
    app.boton_quitar = crear_boton_secundario(botones, "Quitar filtros", app.quitar_filtros, 120)
    app.boton_quitar.pack(side="right")


def crear_tarjeta_exportar(app, padre):
    """
    Exportar a CSV (R18, R35).
    Guarda: app.boton_exportar_todo y app.boton_exportar_filtrado.
    """
    tarjeta = crear_tarjeta(padre, "Exportar a CSV")
    tarjeta.pack(fill="x")

    app.boton_exportar_todo = crear_boton_principal(tarjeta, "Exportar todo", app.exportar_todo, 200)
    app.boton_exportar_todo.pack(fill="x", padx=16, pady=4)
    app.boton_exportar_filtrado = crear_boton_secundario(tarjeta, "Exportar lo filtrado",
                                                         app.exportar_filtrado, 200)
    app.boton_exportar_filtrado.pack(fill="x", padx=16, pady=4)
    Tooltip(app.boton_exportar_filtrado, "Exporta solo los mensajes que quedan tras los filtros. "
                                         "Se activa al aplicar algún filtro.")
    crear_etiqueta(tarjeta, "Separador ';' y coma decimal", estilo.TAMANO_AYUDA, estilo.TEXTO_SUAVE).pack(
        fill="x", padx=16, pady=(2, 14))


def configurar_estilo_tabla(app):
    """
    Fuente, alto de fila y colores de la tabla (ttk.Treeview): cabecera gris azulada,
    filas alternas y selección en azul claro.
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
                    foreground=estilo.TEXTO, borderwidth=0)
    tabla.map("Asterix.Treeview", background=[("selected", estilo.TABLA_SELECCION)],
              foreground=[("selected", estilo.TEXTO)])
    tabla.configure("Asterix.Treeview.Heading", font=app.fuente_cabecera, background=estilo.TABLA_CABECERA,
                    foreground=estilo.TEXTO, relief="flat", padding=(6, 8))
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
    ctk.CTkLabel(encabezado, text="Mensajes decodificados", font=estilo.fuente(estilo.TAMANO_SECCION, True),
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

    barra_vertical = ctk.CTkScrollbar(marco, orientation="vertical", command=app.tabla.yview)
    barra_horizontal = ctk.CTkScrollbar(marco, orientation="horizontal", command=app.tabla.xview)
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
    app.boton_vacio_tabla = crear_boton_principal(app.estado_vacio_tabla, "Abrir fichero .ast",
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
    app.boton_anterior = crear_boton_secundario(paginacion, "◀  Anterior", app.pagina_anterior, 110)
    app.boton_anterior.pack(side="left")
    app.etiqueta_pagina = ctk.CTkLabel(paginacion, text="", width=150, font=estilo.fuente(estilo.TAMANO_TEXTO),
                                       text_color=estilo.TEXTO)
    app.etiqueta_pagina.pack(side="left", padx=8)
    app.boton_siguiente = crear_boton_secundario(paginacion, "Siguiente  ▶", app.pagina_siguiente, 110)
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

    panel = ctk.CTkScrollableFrame(pestana, width=estilo.ANCHO_PANEL_LATERAL, fg_color="transparent")
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
    Controles de la simulación (R40, R41, R43) en dos filas: arriba los botones y los selectores;
    abajo las casillas e "Ir a la hora". Lo que guarda cada parte está en su función.
    """
    tarjeta = crear_tarjeta(padre, "")
    tarjeta.grid(row=0, column=0, sticky="nsew", padx=(0, estilo.MARGEN), pady=(0, estilo.MARGEN))

    fila_1 = ctk.CTkFrame(tarjeta, fg_color="transparent")
    fila_1.pack(fill="x", padx=16, pady=(12, 6))
    crear_botones_reproduccion(app, fila_1)
    crear_selectores_simulacion(app, fila_1)

    fila_2 = ctk.CTkFrame(tarjeta, fg_color="transparent")
    fila_2.pack(fill="x", padx=16, pady=(6, 12))
    crear_casillas_simulacion(app, fila_2)
    crear_ir_a_hora(app, fila_2)


def crear_botones_reproduccion(app, fila_1):
    """
    Reproducir, Pausa, +1 s y Reset.
    Guarda: app.boton_play, app.boton_pausa, app.boton_paso, app.boton_reset.
    """
    app.boton_play = crear_boton_principal(fila_1, "▶  Reproducir", app.play, 130)
    app.boton_play.pack(side="left")
    Tooltip(app.boton_play, "Avanza la simulación de 1 s en 1 s de hora del día.")
    # Símbolos de texto normales: los de pausa y avance (⏸, ⏭) salen como emojis en Windows
    app.boton_pausa = crear_boton_secundario(fila_1, "❚❚  Pausa", app.pausa, 100)
    app.boton_pausa.pack(side="left", padx=(8, 0))
    app.boton_paso = crear_boton_secundario(fila_1, "▶❚  +1 s", app.avanzar_un_segundo, 90)
    app.boton_paso.pack(side="left", padx=(8, 0))
    Tooltip(app.boton_paso, "Avanza un solo salto de 1 s.")
    app.boton_reset = crear_boton_secundario(fila_1, "⟲  Reset", app.reset_simulacion, 90)
    app.boton_reset.pack(side="left", padx=(8, 0))
    Tooltip(app.boton_reset, "Para la simulación y vuelve a la primera hora de los datos.")


def crear_selectores_simulacion(app, fila_1):
    """Selectores de velocidad y de sistema. Guarda: app.selector_velocidad, app.selector_sistema."""
    # La ayuda de los selectores va en su etiqueta
    etiqueta_velocidad = crear_etiqueta(fila_1, "Velocidad", estilo.TAMANO_TEXTO, estilo.TEXTO)
    etiqueta_velocidad.pack(side="left", padx=(24, 8))
    Tooltip(etiqueta_velocidad, "Cada salto es siempre de 1 s; la velocidad cambia cada cuánto se dibuja.")
    app.selector_velocidad = crear_selector(fila_1, ["x1", "x2", "x5", "x10", "x30", "x60"], app.cambiar_velocidad)
    app.selector_velocidad.pack(side="left")

    etiqueta_sistema = crear_etiqueta(fila_1, "Sistema", estilo.TAMANO_TEXTO, estilo.TEXTO)
    etiqueta_sistema.pack(side="left", padx=(24, 8))
    Tooltip(etiqueta_sistema, "Aviones vistos por el radar (CAT048), por ADS-B (CAT021) o por los dos.")
    app.selector_sistema = crear_selector(fila_1, ["Ambos", "Radar", "ADS-B"], app.cambiar_sistema)
    app.selector_sistema.pack(side="left")


def crear_casillas_simulacion(app, fila_2):
    """Casillas Etiquetas y Estelas, marcadas al empezar. Guarda: app.casilla_etiquetas, app.casilla_estelas."""
    app.casilla_etiquetas = crear_casilla(fila_2, "Etiquetas", app.cambiar_etiquetas)
    app.casilla_etiquetas.select()
    app.casilla_etiquetas.pack(side="left")
    Tooltip(app.casilla_etiquetas, "Callsign de cada avión (o su dirección Modo S si no tiene).")
    app.casilla_estelas = crear_casilla(fila_2, "Estelas", app.cambiar_estelas)
    app.casilla_estelas.select()
    app.casilla_estelas.pack(side="left", padx=(16, 0))
    Tooltip(app.casilla_estelas, "Línea con las últimas posiciones de cada avión.")


def crear_ir_a_hora(app, fila_2):
    """Campo de la hora (hh:mm) y botón Ir (R41). Guarda: app.entrada_hora, app.boton_ir."""
    crear_etiqueta(fila_2, "Ir a la hora", estilo.TAMANO_TEXTO, estilo.TEXTO).pack(side="left", padx=(24, 8))
    app.entrada_hora = crear_entrada(fila_2, 80, "hh:mm")
    app.entrada_hora.pack(side="left")
    app.entrada_hora.bind("<Return>", app.ir_a_hora_con_intro)
    Tooltip(app.entrada_hora, "Escribe la hora (UTC) como hh:mm y pulsa Intro. Cada avión aparece en "
                              "su última posición conocida antes de esa hora.")
    app.boton_ir = crear_boton_secundario(fila_2, "Ir", app.ir_a_hora, 50)
    app.boton_ir.pack(side="left", padx=(8, 0))


def crear_tarjeta_reloj(app, padre):
    """Hora del día de la simulación, grande y legible (R44). Guarda: app.etiqueta_reloj."""
    tarjeta = crear_tarjeta(padre, "")
    tarjeta.grid(row=0, column=1, sticky="nsew", pady=(0, estilo.MARGEN))
    crear_etiqueta(tarjeta, "Hora de la simulación (UTC)", estilo.TAMANO_AYUDA, estilo.TEXTO_SECUNDARIO).pack(
        fill="x", padx=16, pady=(12, 0))
    app.etiqueta_reloj = ctk.CTkLabel(tarjeta, text="--:--:--", font=estilo.fuente_numeros(estilo.TAMANO_RELOJ, True),
                                      text_color=estilo.TEXTO, anchor="w", width=ANCHO_RELOJ)
    app.etiqueta_reloj.pack(anchor="w", padx=16, pady=(0, 10))


def crear_zona_mapa(app, padre):
    """
    Aviso de qué se simula, el mapa, el mensaje que se ve cuando no hay nada que mostrar
    y la atribución de OpenStreetMap.
    Guarda: app.etiqueta_aviso_simulacion, app.mapa, app.mensaje_mapa, app.etiqueta_mensaje_mapa.
    """
    zona = ctk.CTkFrame(padre, fg_color="transparent")
    zona.grid(row=1, column=0, sticky="nsew", padx=(0, estilo.MARGEN))

    aviso = ctk.CTkFrame(zona, fg_color=estilo.AVISO_FONDO, corner_radius=estilo.RADIO_TARJETA)
    aviso.pack(fill="x", pady=(0, 8))
    app.etiqueta_aviso_simulacion = ctk.CTkLabel(aviso, text="", font=estilo.fuente(estilo.TAMANO_TEXTO),
                                                 text_color=estilo.AVISO_TEXTO, anchor="w", justify="left")
    app.etiqueta_aviso_simulacion.pack(fill="x", padx=16, pady=8)

    marco_mapa = ctk.CTkFrame(zona, fg_color=estilo.TARJETA, corner_radius=0, border_width=1,
                              border_color=estilo.BORDE)
    marco_mapa.pack(fill="both", expand=True)
    app.mapa = mapa.MapaOSM(marco_mapa, corner_radius=0)
    app.mapa.pack(fill="both", expand=True, padx=1, pady=1)

    # Mensaje en el centro del mapa cuando no hay nada que ver (main.py dice cuál)
    app.mensaje_mapa = crear_tarjeta(marco_mapa, "")
    app.etiqueta_mensaje_mapa = ctk.CTkLabel(app.mensaje_mapa, text="", font=estilo.fuente(estilo.TAMANO_SECCION),
                                             text_color=estilo.TEXTO, justify="center")
    app.etiqueta_mensaje_mapa.pack(padx=28, pady=18)

    # Atribución que pide OpenStreetMap, en la esquina inferior derecha del mapa
    atribucion = tkinter.Label(marco_mapa, text=mapa.ATRIBUCION_MAPA, font=(estilo.FAMILIA, 8),
                               bg=estilo.FONDO_ATRIBUCION, fg=estilo.TEXTO_SECUNDARIO, padx=4)
    atribucion.place(relx=1.0, rely=1.0, x=-2, y=-2, anchor="se")


def crear_fila_leyenda(padre, imagen, texto):
    """
    Una fila de la leyenda: la misma imagen que se dibuja en el mapa y lo que significa.
    Si el texto ocupa varias líneas, cada una se separa del icono con los mismos tres espacios.
    """
    icono = ctk.CTkImage(light_image=imagen, size=(imagen.width, imagen.height))
    texto_separado = "   " + texto.replace("\n", "\n   ")
    fila = ctk.CTkLabel(padre, text=texto_separado, image=icono, compound="left", anchor="w", justify="left",
                        font=estilo.fuente(estilo.TAMANO_TEXTO), text_color=estilo.TEXTO)
    fila.pack(fill="x", padx=16, pady=2)


def crear_cifra_mapa(padre, columna, color, texto_pie):
    """Una cifra del contador "En el mapa", con lo que cuenta debajo. Devuelve la etiqueta de la cifra."""
    cifra = ctk.CTkLabel(padre, text="0", font=estilo.fuente(estilo.TAMANO_CIFRA, True), text_color=color)
    cifra.grid(row=0, column=columna)
    crear_etiqueta(padre, texto_pie, estilo.TAMANO_AYUDA, estilo.TEXTO_SECUNDARIO).grid(row=1, column=columna)
    return cifra


def crear_panel_simulacion(app, padre):
    """
    Panel derecho de la simulación: leyenda (R44), aviones en el mapa e información del
    avión pulsado (R42).
    Guarda: app.cifra_radar, app.cifra_adsb, app.cifra_blancos_puros, app.selector_sistema_avion,
            app.cuadro_info.
    """
    panel = ctk.CTkFrame(padre, fg_color="transparent", width=estilo.ANCHO_PANEL_LATERAL)
    panel.grid(row=1, column=1, sticky="nsew")

    leyenda = crear_tarjeta(panel, "Leyenda")
    leyenda.pack(fill="x", pady=(0, estilo.MARGEN))
    imagenes = app.imagenes_leyenda
    crear_fila_leyenda(leyenda, imagenes["radar"], "Radar (CAT048)")
    crear_fila_leyenda(leyenda, imagenes["adsb"], "ADS-B (CAT021)")
    crear_fila_leyenda(leyenda, imagenes["blanco_puro"], "Blanco puro (sin Modo S): eco de\n"
                                                         "radar primario o secundario. Se\n"
                                                         "quitan con «Quitar blancos puros»")
    crear_fila_leyenda(leyenda, imagenes["resaltado"], "Avión seleccionado y su pareja")
    crear_fila_leyenda(leyenda, imagenes["transponder_fijo"], "Transponder fijo (7777), siempre quieto")
    crear_fila_leyenda(leyenda, imagenes["estacion"], "Radar de Barcelona")
    crear_fila_leyenda(leyenda, imagenes["zona"], "Zona del filtro geográfico")
    crear_fila_leyenda(leyenda, imagenes["estela"], "Estela: últimas posiciones")
    crear_etiqueta(leyenda, "La silueta apunta al rumbo del avión.", estilo.TAMANO_AYUDA,
                   estilo.TEXTO_SUAVE).pack(fill="x", padx=16, pady=(4, 12))

    contador = crear_tarjeta(panel, "En el mapa")
    contador.pack(fill="x", pady=(0, estilo.MARGEN))
    cifras = ctk.CTkFrame(contador, fg_color="transparent")
    cifras.pack(fill="x", padx=16, pady=(0, 12))
    # Tres columnas del mismo ancho: al pasar de 9 a 10 aviones no se mueve nada
    cifras.grid_columnconfigure((0, 1, 2), weight=1, uniform="cifras")
    app.cifra_radar = crear_cifra_mapa(cifras, 0, estilo.RADAR, "radar")
    app.cifra_adsb = crear_cifra_mapa(cifras, 1, estilo.ADSB, "ADS-B")
    app.cifra_blancos_puros = crear_cifra_mapa(cifras, 2, estilo.BLANCO_PURO, "blancos puros")

    informacion = crear_tarjeta(panel, "Avión seleccionado")
    informacion.pack(fill="both", expand=True)
    # Radar / ADS-B: pasa a los datos del mismo avión visto por el otro sistema (main.py lo pone al día)
    app.selector_sistema_avion = crear_selector(informacion, ["Radar", "ADS-B"], app.cambiar_sistema_avion)
    app.selector_sistema_avion.pack(fill="x", padx=16, pady=(0, 8))
    cambiar_estado(app.selector_sistema_avion, False)      # al empezar no hay avión seleccionado
    app.cuadro_info = ctk.CTkTextbox(informacion, wrap="word", fg_color=estilo.TARJETA, text_color=estilo.TEXTO,
                                     font=estilo.fuente_numeros(estilo.TAMANO_AYUDA + 1),
                                     activate_scrollbars=False)
    app.cuadro_info.pack(fill="both", expand=True, padx=12, pady=(0, 12))
    escribir_texto(app.cuadro_info, "Haz clic en un avión del mapa para ver su información.")


def crear_pestana_simulacion(app):
    """Pestaña Simulación (R03, R40-R45): controles y reloj arriba; mapa y panel debajo."""
    pestana = app.pestana_simulacion
    pestana.grid_rowconfigure(1, weight=1)
    pestana.grid_columnconfigure(0, weight=1)
    pestana.grid_columnconfigure(1, minsize=estilo.ANCHO_PANEL_LATERAL)

    crear_controles_simulacion(app, pestana)
    crear_tarjeta_reloj(app, pestana)
    crear_zona_mapa(app, pestana)
    crear_panel_simulacion(app, pestana)
