"""
main.py

Punto de entrada de la aplicación: python main.py

Flujo del programa. Los métodos de la clase Aplicacion están en este mismo orden:

    1. Elegir fichero      elegir_fichero                                  (R10)
    2. Decodificar         decodificar_en_segundo_plano, revisar_decodificacion
                           (R12: en un hilo aparte, con barra de progreso)
    3. Mostrar datos       mostrar_datos, mostrar_pagina                   (tabla por páginas)
    4. Filtrar             aplicar_filtros, quitar_filtros                 (R34-R39)
    5. Exportar            exportar_todo, exportar_filtrado                (R18, R35, R38)
    6. Simular             preparar_simulacion, play, tic_reloj, dar_un_salto
                           (R03, R08, R40-R45: mapa con los mensajes filtrados en Datos)

Los datos se decodifican una sola vez y se guardan en memoria (self.filas_todas).
Filtrar, cambiar de página, exportar y simular trabajan sobre esa lista sin volver a
leer el .ast (R11).

tkinter no permite tocar la ventana desde otro hilo: el hilo solo guarda el porcentaje
y el resultado, y la ventana los consulta cada 100 ms con after(). El reloj de la
simulación también funciona con after(), sin hilos.

Cómo se ve la ventana está en interfaz/ventana.py e interfaz/estilo.py; lo que se dibuja
en el mapa, en interfaz/mapa.py; y la lógica (decodificar, filtrar, exportar y simular),
en la carpeta funciones/.
"""

import os
import sys
import threading
import time
from tkinter import filedialog, messagebox

from funciones import decodificar
from funciones import exportar_csv
from funciones import filtros
from funciones import lector
from funciones import simulacion
from interfaz import estilo
from interfaz import mapa
from interfaz import ventana

FILAS_POR_PAGINA = 500
FILAS_PARA_MEDIR_ANCHOS = 200
INTERVALO_REVISION_MS = 100          # cada cuánto mira la ventana cómo va el hilo

# Python solo deja ejecutar un hilo a la vez (el GIL) y el hilo que decodifica no para. Con el
# cambio de hilo por defecto (cada 5 ms) la ventana casi no consigue su turno y se queda congelada.
# Cambiando cada 0,5 ms la ventana responde; a cambio, decodificar tarda un 10 % más.
INTERVALO_CAMBIO_DE_HILO_S = 0.0005

# Espera entre saltos de 1 s de la simulación según la velocidad elegida (R41).
# Cada salto es siempre de 1 s; lo que cambia es cada cuánto se dibuja.
ESPERA_POR_VELOCIDAD_MS = {"x1": 1000, "x2": 500, "x5": 200, "x10": 100, "x30": 33, "x60": 17}
RETRASO_MAXIMO_S = 1.0      # retraso del reloj de la simulación que se intenta recuperar (ver tic_reloj)

# Ayuda de la opción Radar / ADS-B del panel cuando no se puede pulsar
AYUDA_SIN_PAREJA = "Este avión no está en el mapa por el otro sistema."


class Aplicacion:
    """
    La ventana y sus datos. Hace falta una clase porque los botones llaman a métodos que
    comparten los datos cargados, la página actual, los filtros y el estado de la simulación.
    """

    def __init__(self):
        # --- Datos en memoria ---
        self.filas_todas = []           # todas las filas decodificadas (tuplas)
        self.filas_visibles = []        # las que quedan tras los filtros (las mismas tuplas, sin copiar)
        self.recuentos = None           # recuentos de la decodificación
        self.nombre_fichero = ""
        self.opciones_filtros = None    # filtros aplicados; None si no hay ninguno
        self.pagina_actual = 0

        # --- Trabajo en segundo plano (decodificar o exportar) ---
        self.hilo = None
        self.porcentaje = 0             # lo escribe el hilo, lo lee la ventana
        self.registros_leidos = 0       # ídem, solo al decodificar
        self.resultado_hilo = None
        self.error_hilo = None

        # --- Simulación ---
        self.estado_simulacion = None   # el de simulacion.preparar(); None si hay que prepararla
        self.reproduciendo = False
        self.id_reloj = None            # el after() pendiente del reloj, para poder cancelarlo
        self.instante_siguiente_salto = 0.0
        self.espera_ms = ESPERA_POR_VELOCIDAD_MS["x1"]
        self.marcadores = {}            # identificador de avión -> su marcador en el mapa
        self.estelas = {}               # identificador de avión -> su estela en el mapa
        self.avion_seleccionado = None
        self.aviones_resaltados = set() # el seleccionado y su pareja del otro sistema
        self.mapa_encuadrado = False

        # --- Ventana ---
        # Las funciones de ventana.py crean los elementos y los guardan en la aplicación
        # (self.boton_abrir, self.tabla...); el docstring de cada una dice cuáles.
        self.raiz = ventana.crear_ventana_principal()
        # Un error no previsto se muestra en un diálogo y no como traza (R14)
        self.raiz.report_callback_exception = self.mostrar_error_inesperado
        mapa.crear_iconos(self)
        ventana.crear_cabecera(self)
        ventana.crear_barra_estado(self)
        ventana.crear_pestanas(self)
        ventana.crear_pestana_datos(self)
        ventana.crear_pestana_simulacion(self)
        mapa.configurar_mapa(self)
        self.mostrar_pagina()
        self.actualizar_panel_simulacion()

    # =========================================================================
    # 1. Elegir fichero (R10)
    # =========================================================================

    def elegir_fichero(self):
        """Botón "Abrir fichero .ast": diálogo para elegir el fichero y empezar a decodificarlo."""
        ruta = filedialog.askopenfilename(
            title="Elige un fichero ASTERIX",
            filetypes=[("Ficheros ASTERIX", "*.ast"), ("Todos los ficheros", "*.*")])
        if ruta == "":
            return
        self.decodificar_en_segundo_plano(ruta)

    # =========================================================================
    # 2. Decodificar en un hilo aparte (R12)
    # =========================================================================

    def decodificar_en_segundo_plano(self, ruta):
        """Suelta los datos anteriores y lanza la decodificación en otro hilo."""
        # Los datos del fichero anterior se sueltan antes de cargar el nuevo (R13)
        self.filas_todas = []
        self.filas_visibles = []
        self.recuentos = None
        self.opciones_filtros = None
        self.pagina_actual = 0

        self.nombre_fichero = os.path.basename(ruta)
        self.etiqueta_fichero.configure(text=self.nombre_fichero)
        self.mostrar_resumen(None)

        self.porcentaje = 0
        self.registros_leidos = 0
        self.barra_progreso_tabla.set(0)
        ventana.cambiar_texto(self.etiqueta_progreso_tabla, "Decodificando " + self.nombre_fichero + "...  0 %")
        self.resultado_hilo = None
        self.error_hilo = None
        self.hilo = threading.Thread(target=self.tarea_decodificar, args=(ruta,), daemon=True)
        self.hilo.start()

        self.invalidar_simulacion()
        self.mostrar_pagina()
        self.poner_estado("Decodificando " + self.nombre_fichero + "...", estilo.ESTADO_TRABAJANDO)
        self.poner_progreso(0)
        self.raiz.after(INTERVALO_REVISION_MS, self.revisar_decodificacion)

    def tarea_decodificar(self, ruta):
        """Se ejecuta en el hilo aparte. No toca la ventana: solo guarda el resultado o el error."""
        try:
            self.resultado_hilo = decodificar.decodificar_fichero(ruta, self.guardar_progreso_decodificacion)
        except ValueError as error:
            self.error_hilo = "El fichero no es ASTERIX o está dañado:\n" + str(error) + "."
        except OSError as error:
            self.error_hilo = "No se ha podido leer el fichero:\n" + str(error.strerror) + "."
        except MemoryError:
            self.error_hilo = "No hay memoria suficiente para decodificar este fichero."
        except Exception as error:
            self.error_hilo = "Error inesperado al decodificar:\n" + str(error)

    def guardar_progreso_decodificacion(self, porcentaje, registros_leidos):
        """La llama decodificar_fichero desde el hilo para informar del progreso."""
        self.porcentaje = porcentaje
        self.registros_leidos = registros_leidos

    def guardar_porcentaje(self, porcentaje):
        """La llama la exportación desde el hilo para informar del progreso."""
        self.porcentaje = porcentaje

    def revisar_decodificacion(self):
        """Se repite cada 100 ms: mueve las barras de progreso y, al acabar, muestra los datos."""
        if self.hilo.is_alive():
            self.poner_progreso(self.porcentaje)
            # Progreso grande en el sitio de la tabla
            self.barra_progreso_tabla.set(self.porcentaje / 100)
            ventana.cambiar_texto(self.etiqueta_progreso_tabla,
                                  "Decodificando " + self.nombre_fichero + "...  " + str(self.porcentaje) + " %  ·  "
                                  + con_miles(self.registros_leidos) + " registros leídos")
            self.raiz.after(INTERVALO_REVISION_MS, self.revisar_decodificacion)
            return

        self.hilo = None
        if self.error_hilo is not None:
            self.nombre_fichero = ""
            self.etiqueta_fichero.configure(text="Ningún fichero cargado")
            self.poner_progreso(0)
            self.poner_estado("No se ha podido decodificar el fichero", estilo.TEXTO_SUAVE)
            self.etiqueta_detalle_resumen.configure(text="No se ha podido decodificar el fichero.")
            self.mostrar_pagina()
            self.actualizar_panel_simulacion()
            messagebox.showerror("Error al decodificar", self.error_hilo)
            return

        filas, recuentos = self.resultado_hilo
        self.resultado_hilo = None
        self.mostrar_datos(filas, recuentos)

    # =========================================================================
    # 3. Mostrar los datos: resumen y tabla por páginas
    # =========================================================================

    def mostrar_datos(self, filas, recuentos):
        """Guarda las filas decodificadas, muestra el resumen y la primera página."""
        self.filas_todas = filas
        self.filas_visibles = filas
        self.recuentos = recuentos
        self.pagina_actual = 0
        self.mostrar_resumen(recuentos)

        # Ancho de cada columna según su cabecera y los valores de las primeras filas
        muestra = []
        for fila in filas[:FILAS_PARA_MEDIR_ANCHOS]:
            muestra.append(exportar_csv.formatear_fila(fila))
        ventana.ajustar_anchos_columnas(self, muestra)

        self.invalidar_simulacion()
        self.mostrar_pagina()
        self.poner_progreso(100)
        self.poner_estado("Decodificado en " + formatear_segundos(recuentos["segundos"]) + " · "
                          + con_miles(len(filas)) + " mensajes", estilo.ESTADO_LISTO)

    def mostrar_resumen(self, recuentos):
        """Rellena la tarjeta de resumen; con None la deja vacía (mientras se decodifica)."""
        if recuentos is None:
            for cifra in (self.cifra_leidos, self.cifra_filas, self.cifra_descartados, self.cifra_tiempo):
                cifra.configure(text="—")
            self.etiqueta_detalle_resumen.configure(text="Decodificando el fichero...")
            return

        leidos = recuentos["registros_048"] + recuentos["registros_021"]
        filas = recuentos["filas_048"] + recuentos["filas_021"]
        fuera_de_zona = recuentos["descartados_048_fuera_de_zona"] + recuentos["descartados_021_fuera_de_zona"]
        sin_posicion = recuentos["descartados_048_sin_posicion"] + recuentos["descartados_021_sin_posicion"]

        self.cifra_leidos.configure(text=con_miles(leidos))
        self.cifra_filas.configure(text=con_miles(filas))
        self.cifra_descartados.configure(text=con_miles(leidos - filas))
        self.cifra_tiempo.configure(text=format(recuentos["segundos"], ".1f").replace(".", ","))

        lineas = [
            "CAT048: " + con_miles(recuentos["registros_048"]) + " leídos, " + con_miles(recuentos["filas_048"])
            + " en la tabla (" + con_miles(recuentos["filas_048_sin_fl"]) + " sin FL)",
            "CAT021: " + con_miles(recuentos["registros_021"]) + " leídos, " + con_miles(recuentos["filas_021"])
            + " en la tabla",
            "Descartados: " + con_miles(fuera_de_zona) + " fuera de zona, "
            + con_miles(recuentos["descartados_021_en_tierra"]) + " en tierra (GBS), "
            + con_miles(sin_posicion) + " sin posición",
            "Bloques desincronizados: " + con_miles(recuentos["bloques_desincronizados"]),
        ]
        self.etiqueta_detalle_resumen.configure(text="\n".join(lineas))

    def numero_de_paginas(self):
        """Número de páginas de la tabla (al menos 1, aunque no haya filas)."""
        paginas = (len(self.filas_visibles) + FILAS_POR_PAGINA - 1) // FILAS_POR_PAGINA
        if paginas == 0:
            paginas = 1
        return paginas

    def mostrar_pagina(self):
        """Vacía la tabla y pone las filas de la página actual."""
        for elemento in self.tabla.get_children():
            self.tabla.delete(elemento)

        total = len(self.filas_visibles)
        primera = self.pagina_actual * FILAS_POR_PAGINA
        ultima = min(primera + FILAS_POR_PAGINA, total)
        for numero_fila in range(primera, ultima):
            celdas = exportar_csv.formatear_fila(self.filas_visibles[numero_fila])
            if numero_fila % 2 == 1:
                self.tabla.insert("", "end", values=celdas, tags=("alterna",))
            else:
                self.tabla.insert("", "end", values=celdas)
        self.tabla.yview_moveto(0)

        self.etiqueta_pagina.configure(text="Página " + con_miles(self.pagina_actual + 1)
                                       + " de " + con_miles(self.numero_de_paginas()))
        if total == 0:
            self.etiqueta_total.configure(text="")
        else:
            texto = ("Mostrando " + con_miles(primera + 1) + "-" + con_miles(ultima)
                     + " de " + con_miles(total) + " mensajes")
            if self.opciones_filtros is not None:
                texto = texto + " (" + con_miles(len(self.filas_todas)) + " sin filtrar)"
            self.etiqueta_total.configure(text=texto)

        self.actualizar_estado_vacio_tabla()
        self.actualizar_botones()

    def actualizar_estado_vacio_tabla(self):
        """
        Si la tabla no tiene filas, pone encima lo que corresponde: la barra de progreso grande
        mientras se decodifica, o un mensaje que explica por qué está vacía y qué hacer.
        """
        if self.recuentos is None and self.hilo is not None:
            self.estado_vacio_tabla.place_forget()
            self.progreso_tabla.place(relx=0.5, rely=0.45, anchor="center")
            return
        self.progreso_tabla.place_forget()

        boton = ""
        if self.recuentos is None:
            mensaje = "Abre un fichero .ast para empezar.\nSe decodificarán sus mensajes CAT048 y CAT021."
            boton = "abrir"
        elif len(self.filas_todas) == 0:
            mensaje = "El fichero no tiene ningún mensaje dentro de la zona del filtro geográfico."
        elif len(self.filas_visibles) == 0:
            mensaje = "Ningún mensaje cumple los filtros."
            boton = "quitar"
        else:
            self.estado_vacio_tabla.place_forget()
            return

        self.etiqueta_vacio_tabla.configure(text=mensaje)
        if boton == "abrir":
            self.boton_vacio_tabla.configure(text="Abrir fichero .ast", command=self.elegir_fichero)
            self.boton_vacio_tabla.pack(pady=(0, 24))
        elif boton == "quitar":
            self.boton_vacio_tabla.configure(text="Quitar filtros", command=self.quitar_filtros)
            self.boton_vacio_tabla.pack(pady=(0, 24))
        else:
            self.boton_vacio_tabla.pack_forget()
        self.estado_vacio_tabla.place(relx=0.5, rely=0.45, anchor="center")

    def pagina_anterior(self):
        """Botón "Anterior"."""
        if self.pagina_actual > 0:
            self.pagina_actual = self.pagina_actual - 1
            self.mostrar_pagina()

    def pagina_siguiente(self):
        """Botón "Siguiente"."""
        if self.pagina_actual < self.numero_de_paginas() - 1:
            self.pagina_actual = self.pagina_actual + 1
            self.mostrar_pagina()

    # =========================================================================
    # 4. Filtrar (R34-R39)
    # =========================================================================

    def leer_opciones_filtros(self):
        """
        Lee el panel de filtros y devuelve el diccionario de opciones de filtros.aplicar_filtros.
        Si la altitud escrita no es un número, avisa y devuelve None.
        """
        opciones = {}

        categoria = self.selector_categoria.get()
        if categoria == "CAT048":
            opciones["categoria"] = 48
        elif categoria == "CAT021":
            opciones["categoria"] = 21
        else:
            opciones["categoria"] = None

        opciones["quitar_blancos_puros"] = self.casilla_blancos_puros.get() == 1
        opciones["quitar_transponder_fijo"] = self.casilla_transponder_fijo.get() == 1
        opciones["quitar_en_tierra"] = self.casilla_en_tierra.get() == 1
        opciones["solo_con_fl"] = self.casilla_solo_fl.get() == 1

        texto_altitud = self.entrada_altitud.get().strip()
        if texto_altitud == "":
            opciones["altitud_maxima_ft"] = None
        else:
            try:
                opciones["altitud_maxima_ft"] = float(texto_altitud.replace(",", "."))
            except ValueError:
                messagebox.showwarning("Altitud no válida",
                                       "La altitud máxima tiene que ser un número en ft, por ejemplo 6000.")
                return None

        opciones["aeronave"] = self.entrada_aeronave.get().strip()
        return opciones

    def aplicar_filtros(self):
        """Botón "Aplicar filtros": aplica a la vez todos los filtros marcados (R36)."""
        opciones = self.leer_opciones_filtros()
        if opciones is None:
            return
        self.filas_visibles = filtros.aplicar_filtros(self.filas_todas, opciones)
        if filtros.hay_filtros_activos(opciones):
            self.opciones_filtros = opciones
        else:
            self.opciones_filtros = None
        self.pagina_actual = 0
        self.invalidar_simulacion()      # la simulación usa los mensajes filtrados
        self.mostrar_pagina()
        self.poner_estado("Filtrado: " + con_miles(len(self.filas_visibles)) + " de "
                          + con_miles(len(self.filas_todas)) + " mensajes", estilo.ESTADO_LISTO)

    def aplicar_filtros_con_intro(self, evento):
        """Pulsar Intro en un campo de texto del panel de filtros equivale a "Aplicar filtros"."""
        if len(self.filas_todas) > 0 and self.hilo is None:
            self.aplicar_filtros()

    def quitar_filtros(self):
        """Botón "Quitar filtros": deja el panel como al principio y vuelve a mostrar todo (R34)."""
        self.selector_categoria.set("Ambas")
        self.casilla_blancos_puros.deselect()
        self.casilla_transponder_fijo.deselect()
        self.casilla_en_tierra.deselect()
        self.casilla_solo_fl.deselect()
        self.entrada_altitud.delete(0, "end")
        self.entrada_aeronave.delete(0, "end")

        self.filas_visibles = self.filas_todas
        self.opciones_filtros = None
        self.pagina_actual = 0
        self.invalidar_simulacion()
        self.mostrar_pagina()
        self.poner_estado("Sin filtros: " + con_miles(len(self.filas_todas)) + " mensajes", estilo.ESTADO_LISTO)

    # =========================================================================
    # 5. Exportar a CSV (R18, R35, R38)
    # =========================================================================

    def exportar_todo(self):
        """Botón "Exportar todo": todas las filas decodificadas."""
        nombre_base = os.path.splitext(self.nombre_fichero)[0]
        self.exportar(self.filas_todas, nombre_base + ".csv")

    def exportar_filtrado(self):
        """Botón "Exportar lo filtrado": solo las filas que quedan tras los filtros."""
        nombre_base = os.path.splitext(self.nombre_fichero)[0]
        self.exportar(self.filas_visibles, nombre_base + "_filtrado.csv")

    def exportar(self, filas, nombre_sugerido):
        """Diálogo para elegir dónde se guarda el CSV (R18) y exportación en un hilo aparte."""
        ruta = filedialog.asksaveasfilename(
            title="Guardar CSV", initialfile=nombre_sugerido, defaultextension=".csv",
            filetypes=[("CSV separado por ';'", "*.csv")])
        if ruta == "":
            return
        self.empezar_exportacion(ruta, filas)

    def empezar_exportacion(self, ruta, filas):
        """Lanza la escritura del CSV en otro hilo para que la ventana no se congele."""
        self.porcentaje = 0
        self.resultado_hilo = None
        self.error_hilo = None
        self.hilo = threading.Thread(target=self.tarea_exportar, args=(ruta, filas), daemon=True)
        self.hilo.start()
        self.actualizar_botones()
        self.poner_estado("Exportando " + con_miles(len(filas)) + " mensajes...", estilo.ESTADO_TRABAJANDO)
        self.poner_progreso(0)
        self.raiz.after(INTERVALO_REVISION_MS, self.revisar_exportacion)

    def tarea_exportar(self, ruta, filas):
        """Se ejecuta en el hilo aparte. No toca la ventana: solo guarda el resultado o el error."""
        instante_inicio = time.time()
        try:
            exportar_csv.exportar(ruta, filas, self.guardar_porcentaje)
            self.resultado_hilo = (ruta, len(filas), time.time() - instante_inicio)
        except OSError as error:
            self.error_hilo = ("No se ha podido guardar el CSV (" + str(error.strerror) + ").\n"
                               "Si el fichero está abierto en Excel, ciérralo y vuelve a intentarlo.")
        except Exception as error:
            self.error_hilo = "Error inesperado al exportar:\n" + str(error)

    def revisar_exportacion(self):
        """Se repite cada 100 ms: mueve la barra de progreso y, al acabar, avisa."""
        if self.hilo.is_alive():
            self.poner_progreso(self.porcentaje)
            self.raiz.after(INTERVALO_REVISION_MS, self.revisar_exportacion)
            return

        self.hilo = None
        self.actualizar_botones()
        if self.error_hilo is not None:
            self.poner_progreso(0)
            self.poner_estado("No se ha podido exportar", estilo.TEXTO_SUAVE)
            messagebox.showerror("Error al exportar", self.error_hilo)
            return

        ruta, numero_filas, segundos = self.resultado_hilo
        self.poner_progreso(100)
        self.poner_estado("Exportado en " + formatear_segundos(segundos) + ": " + ruta, estilo.ESTADO_LISTO)
        messagebox.showinfo("Exportación terminada",
                            "Se han guardado " + con_miles(numero_filas) + " mensajes en:\n" + ruta)

    # =========================================================================
    # 6. Simular en el mapa (R03, R08, R40-R45)
    # =========================================================================

    def cambiar_pestana(self, pestana):
        """
        Selector de la cabecera: muestra la pestaña Datos o la pestaña Simulación.
        Al pasar a Datos, la simulación se pausa (como el botón Pausa) y al volver sigue en pausa.
        """
        if pestana == "Datos":
            self.pausa()
            self.pestana_simulacion.pack_forget()
            self.pestana_datos.pack(fill="both", expand=True)
            return

        self.pestana_datos.pack_forget()
        self.pestana_simulacion.pack(fill="both", expand=True)
        if not self.mapa_encuadrado:
            mapa.encuadrar_zona(self)
            self.mapa_encuadrado = True
        if self.estado_simulacion is None and len(self.filas_visibles) > 0 and self.hilo is None:
            self.preparar_simulacion()

    def invalidar_simulacion(self):
        """
        Los datos o los filtros han cambiado: se para la simulación y se vacía el mapa.
        Se vuelve a preparar al entrar en la pestaña Simulación o al pulsar Reproducir.
        """
        self.pausa()
        mapa.borrar_todos(self)
        self.estado_simulacion = None
        self.avion_seleccionado = None
        self.aviones_resaltados = set()
        ventana.escribir_texto(self.cuadro_info, "Haz clic en un avión del mapa para ver su información.")
        self.actualizar_panel_simulacion()

    def preparar_simulacion(self):
        """Ordena por hora los mensajes filtrados en la pestaña Datos y dibuja el primer segundo."""
        self.estado_simulacion = simulacion.preparar(self.filas_visibles)
        mapa.redibujar_todos(self, self.estado_simulacion["aviones"])
        mapa.actualizar_resaltado(self, self.estado_simulacion["aviones"])
        self.actualizar_panel_simulacion()
        self.actualizar_botones()

    def play(self):
        """Botón Reproducir: arranca el reloj de la simulación (R40)."""
        if self.estado_simulacion is None:
            self.preparar_simulacion()
        if simulacion.ha_terminado(self.estado_simulacion):
            messagebox.showinfo("Simulación", "La simulación ha llegado al final de los datos.\n"
                                              "Pulsa Reset o elige una hora para volver a empezar.")
            return
        if self.reproduciendo:
            return
        self.reproduciendo = True
        self.actualizar_botones()
        self.poner_estado("Reproduciendo a " + self.selector_velocidad.get(), estilo.ESTADO_LISTO)
        self.instante_siguiente_salto = time.perf_counter() + self.espera_ms / 1000
        self.id_reloj = self.raiz.after(self.espera_ms, self.tic_reloj)

    def pausa(self):
        """Botón Pausa: para el reloj de la simulación."""
        if self.reproduciendo:
            self.poner_estado("Simulación en pausa", estilo.TEXTO_SUAVE)
        self.reproduciendo = False
        if self.id_reloj is not None:
            self.raiz.after_cancel(self.id_reloj)
            self.id_reloj = None
        self.actualizar_botones()

    def tic_reloj(self):
        """
        Reloj de la simulación: da un salto de 1 s y programa el siguiente con after().

        En Windows, after() solo es preciso a unos 15,6 ms y a menudo espera más de lo pedido.
        Por eso se lleva la hora a la que debería tocar cada salto
        y la espera se calcula hasta esa hora: si un salto llega tarde, el siguiente espera menos.
        Si se acumula más de RETRASO_MAXIMO_S de retraso, se deja de recuperar: la simulación va
        más lenta, pero la ventana sigue respondiendo.
        """
        self.id_reloj = None
        if not self.reproduciendo:
            return
        self.dar_un_salto()
        if simulacion.ha_terminado(self.estado_simulacion):
            self.pausa()
            self.poner_estado("Fin de los datos. Pulsa Reset para volver a empezar.", estilo.TEXTO_SUAVE)
            return

        ahora = time.perf_counter()
        self.instante_siguiente_salto = self.instante_siguiente_salto + self.espera_ms / 1000
        if ahora - self.instante_siguiente_salto > RETRASO_MAXIMO_S:
            self.instante_siguiente_salto = ahora
        espera_ms = int((self.instante_siguiente_salto - ahora) * 1000)
        if espera_ms < 1:
            espera_ms = 1
        self.id_reloj = self.raiz.after(espera_ms, self.tic_reloj)

    def dar_un_salto(self):
        """Avanza la simulación 1 s: mueve los aviones con mensaje nuevo y quita los que han caducado."""
        cambiados, caducados = simulacion.avanzar_un_segundo(self.estado_simulacion)
        for identificador in caducados:
            mapa.borrar_avion(self, identificador)
        aviones = self.estado_simulacion["aviones"]
        for identificador in cambiados:
            if mapa.sistema_visible(self, identificador[0]):
                mapa.dibujar_avion(self, identificador, aviones[identificador])
        mapa.actualizar_resaltado(self, aviones)
        self.actualizar_panel_simulacion()

    def avanzar_un_segundo(self):
        """Botón +1 s: un solo salto, con la simulación en pausa o en marcha."""
        if self.estado_simulacion is None:
            self.preparar_simulacion()
        if not simulacion.ha_terminado(self.estado_simulacion):
            self.dar_un_salto()

    def reset_simulacion(self):
        """Botón Reset: para la simulación y vuelve al primer segundo de los datos."""
        self.pausa()
        if self.estado_simulacion is None:
            self.preparar_simulacion()
            return
        self.saltar_a_segundo(self.estado_simulacion["inicio"])

    def ir_a_hora(self):
        """Botón "Ir": salta a la hora escrita (hh:mm). Cada avión aparece en su última posición antes de esa hora."""
        segundo = leer_hora(self.entrada_hora.get())
        if segundo is None:
            messagebox.showwarning("Hora no válida", "Escribe la hora como hh:mm, por ejemplo 06:30.")
            return
        if self.estado_simulacion is None:
            self.preparar_simulacion()
        inicio = self.estado_simulacion["inicio"]
        fin = self.estado_simulacion["fin"]
        if segundo < inicio or segundo > fin:
            messagebox.showwarning("Hora fuera de los datos",
                                   "Los datos van de las " + hora_sin_decimales(inicio) + " a las "
                                   + hora_sin_decimales(fin) + " UTC.")
            return
        self.saltar_a_segundo(segundo)

    def ir_a_hora_con_intro(self, evento):
        """Pulsar Intro en el campo de la hora equivale al botón "Ir"."""
        if len(self.filas_todas) > 0 and self.hilo is None:
            self.ir_a_hora()

    def saltar_a_segundo(self, segundo):
        """Lleva la simulación a esa hora y redibuja el mapa. Si estaba en marcha, sigue en marcha."""
        simulacion.ir_a_segundo(self.estado_simulacion, segundo)
        mapa.redibujar_todos(self, self.estado_simulacion["aviones"])
        mapa.actualizar_resaltado(self, self.estado_simulacion["aviones"])
        self.actualizar_panel_simulacion()

    def cambiar_velocidad(self, velocidad):
        """Selector de velocidad (R41): cambia la espera entre saltos, no el tamaño del salto."""
        self.espera_ms = ESPERA_POR_VELOCIDAD_MS[velocidad]
        self.instante_siguiente_salto = time.perf_counter()
        if self.reproduciendo:
            self.poner_estado("Reproduciendo a " + velocidad, estilo.ESTADO_LISTO)

    def cambiar_sistema(self, sistema):
        """Selector Radar / ADS-B / Ambos (R43): vuelve a dibujar solo los aviones del sistema elegido."""
        if self.estado_simulacion is not None:
            mapa.redibujar_todos(self, self.estado_simulacion["aviones"])
            mapa.actualizar_resaltado(self, self.estado_simulacion["aviones"])
        self.actualizar_panel_simulacion()

    def cambiar_etiquetas(self):
        """Casilla Etiquetas: muestra u oculta el callsign junto a cada avión."""
        if self.estado_simulacion is not None:
            mapa.actualizar_etiquetas(self, self.estado_simulacion["aviones"])

    def cambiar_estelas(self):
        """Casilla Estelas: muestra u oculta la línea con las últimas posiciones de cada avión (R45)."""
        if self.estado_simulacion is not None:
            mapa.redibujar_todos(self, self.estado_simulacion["aviones"])
            mapa.actualizar_resaltado(self, self.estado_simulacion["aviones"])

    def al_pulsar_avion(self, marcador):
        """
        Clic en un avión del mapa: lo selecciona, lo resalta junto a su pareja del otro sistema (R08)
        y muestra su información en el panel (R42). El selector Radar / ADS-B del panel se pone en
        el sistema de ese avión.
        """
        self.avion_seleccionado = marcador.data
        mapa.actualizar_resaltado(self, self.estado_simulacion["aviones"])
        self.actualizar_panel_simulacion()

    def cambiar_sistema_avion(self, sistema):
        """
        Selector Radar / ADS-B del panel: el avión seleccionado pasa a ser su pareja del otro
        sistema (misma TA, R08). El resaltado no cambia: las dos siluetas ya estaban en rojo.
        'sistema' es la opción pulsada, que la pasa el Selector. No hace falta usarla: como solo
        hay dos sistemas, pulsar la otra opción siempre significa pasar a la pareja.
        """
        pareja = mapa.pareja_otro_sistema(self.avion_seleccionado)
        if pareja is None:
            return
        self.avion_seleccionado = pareja
        self.actualizar_panel_simulacion()

    def actualizar_selector_sistema_avion(self):
        """
        Selector Radar / ADS-B del panel: desactivado si no hay avión seleccionado. Si lo hay, marca
        su sistema, y la otra opción solo se puede pulsar si la pareja está en el mapa (la pareja
        puede aparecer o caducar en cualquier salto). cambiar_estado y cambiar_estado_opcion no
        tocan nada si ya estaba así, para que el selector no parpadee al reproducir.
        """
        if self.avion_seleccionado is None:
            # Se reactivan las dos opciones para que no quede la ayuda de una pareja que ya no existe
            self.selector_sistema_avion.cambiar_estado_opcion("Radar", True, "")
            self.selector_sistema_avion.cambiar_estado_opcion("ADS-B", True, "")
            ventana.cambiar_estado(self.selector_sistema_avion, False)
            return
        ventana.cambiar_estado(self.selector_sistema_avion, True)

        if self.avion_seleccionado[0] == mapa.CATEGORIA_048:
            sistema = "Radar"
            otro_sistema = "ADS-B"
        else:
            sistema = "ADS-B"
            otro_sistema = "Radar"
        pareja = mapa.pareja_otro_sistema(self.avion_seleccionado)
        pareja_en_mapa = pareja is not None and pareja in self.marcadores

        self.selector_sistema_avion.set(sistema)
        self.selector_sistema_avion.cambiar_estado_opcion(sistema, True, "")
        self.selector_sistema_avion.cambiar_estado_opcion(otro_sistema, pareja_en_mapa, AYUDA_SIN_PAREJA)

    def actualizar_panel_simulacion(self):
        """
        Pone al día el reloj (R44), el aviso de qué se simula, el contador, el panel del avión con
        su selector Radar / ADS-B y el mensaje del mapa. Se llama en cada salto: solo se cambia lo
        que es distinto.
        """
        self.actualizar_aviso_simulacion()
        self.actualizar_mensaje_mapa()
        self.actualizar_selector_sistema_avion()
        estado = self.estado_simulacion
        if estado is None:
            ventana.cambiar_texto(self.etiqueta_reloj, "--:--:--")
            ventana.cambiar_texto(self.cifra_radar, "0")
            ventana.cambiar_texto(self.cifra_adsb, "0")
            ventana.cambiar_texto(self.cifra_blancos_puros, "0")
            return

        ventana.cambiar_texto(self.etiqueta_reloj, hora_sin_decimales(estado["segundo"]))
        radar, adsb, blancos_puros = mapa.contar_en_mapa(self, estado["aviones"])
        ventana.cambiar_texto(self.cifra_radar, str(radar))
        ventana.cambiar_texto(self.cifra_adsb, str(adsb))
        ventana.cambiar_texto(self.cifra_blancos_puros, str(blancos_puros))

        if self.avion_seleccionado is None:
            return
        if self.avion_seleccionado in estado["aviones"]:
            texto = mapa.texto_informacion(estado["aviones"][self.avion_seleccionado], self.avion_seleccionado)
        else:
            texto = ("El avión seleccionado ya no está a la vista (más de "
                     + str(simulacion.SEGUNDOS_PARA_CADUCAR) + " s sin mensajes).")
        ventana.escribir_texto(self.cuadro_info, texto)

    def actualizar_aviso_simulacion(self):
        """Aviso encima del mapa: cuántos mensajes se simulan y con qué filtros de la pestaña Datos."""
        if len(self.filas_todas) == 0:
            texto = "Abre un fichero .ast para simular sus trayectorias."
        elif self.opciones_filtros is None:
            texto = ("Se simulan los " + con_miles(len(self.filas_visibles))
                     + " mensajes de la pestaña Datos (sin filtros).")
        else:
            texto = ("Se simulan los " + con_miles(len(self.filas_visibles)) + " mensajes filtrados en Datos. "
                     + "Filtros activos: " + filtros.describir_filtros(self.opciones_filtros) + ".")
        ventana.cambiar_texto(self.etiqueta_aviso_simulacion, texto)

    def actualizar_mensaje_mapa(self):
        """Si en el mapa no hay nada que ver, pone en el centro un mensaje que explica por qué y qué hacer."""
        mensaje = ""
        if self.recuentos is None and self.hilo is not None:
            mensaje = "Decodificando el fichero..."
        elif len(self.filas_todas) == 0:
            mensaje = "No hay ningún fichero cargado.\nAbre un fichero .ast con el botón de arriba a la derecha."
        elif len(self.filas_visibles) == 0:
            mensaje = "Los filtros de la pestaña Datos no dejan ningún mensaje.\nQuita o cambia los filtros en Datos."
        elif self.estado_simulacion is not None:
            sistema = self.selector_sistema.get()
            mensajes = self.estado_simulacion["mensajes_por_categoria"]
            if sistema == "ADS-B" and mensajes[21] == 0:
                mensaje = ("No hay mensajes ADS-B (CAT021) entre los filtrados en Datos.\n"
                           "Elige «Radar» o «Ambos» en Sistema, o cambia los filtros en Datos.")
            elif sistema == "Radar" and mensajes[48] == 0:
                mensaje = ("No hay mensajes de radar (CAT048) entre los filtrados en Datos.\n"
                           "Elige «ADS-B» o «Ambos» en Sistema, o cambia los filtros en Datos.")
            elif len(self.marcadores) == 0:
                mensaje = ("No hay aviones a la vista a las " + hora_sin_decimales(self.estado_simulacion["segundo"])
                           + ".\nPulsa Reproducir o elige otra hora.")

        if mensaje == "":
            self.mensaje_mapa.place_forget()
        else:
            ventana.cambiar_texto(self.etiqueta_mensaje_mapa, mensaje)
            self.mensaje_mapa.place(relx=0.5, rely=0.5, anchor="center")

    # =========================================================================
    # Utilidades de la ventana
    # =========================================================================

    def poner_estado(self, texto, color):
        """Texto de la barra de estado y color del punto que lo acompaña."""
        self.etiqueta_estado.configure(text=texto)
        self.punto_estado.configure(text_color=color)

    def poner_progreso(self, porcentaje):
        """Barra de progreso de la barra de estado (0-100)."""
        self.barra_progreso.set(porcentaje / 100)
        self.etiqueta_porcentaje.configure(text=str(porcentaje) + " %")

    def actualizar_botones(self):
        """
        Activa o desactiva cada control según la situación (R15): sin datos no se puede filtrar,
        exportar ni simular, y mientras se decodifica o se exporta no se puede tocar nada.
        """
        trabajando = self.hilo is not None
        hay_datos = len(self.filas_todas) > 0 and not trabajando

        ventana.cambiar_estado(self.boton_abrir, not trabajando)

        controles_datos = [self.selector_categoria, self.casilla_blancos_puros, self.casilla_transponder_fijo,
                           self.casilla_en_tierra, self.casilla_solo_fl, self.entrada_altitud,
                           self.entrada_aeronave, self.boton_aplicar, self.boton_quitar,
                           self.boton_exportar_todo]
        for control in controles_datos:
            ventana.cambiar_estado(control, hay_datos)

        hay_filtrado = hay_datos and self.opciones_filtros is not None and len(self.filas_visibles) > 0
        ventana.cambiar_estado(self.boton_exportar_filtrado, hay_filtrado)
        ventana.cambiar_estado(self.boton_anterior, hay_datos and self.pagina_actual > 0)
        ventana.cambiar_estado(self.boton_siguiente,
                               hay_datos and self.pagina_actual < self.numero_de_paginas() - 1)

        hay_simulacion = hay_datos and len(self.filas_visibles) > 0
        controles_simulacion = [self.boton_paso, self.boton_reset, self.selector_velocidad,
                                self.selector_sistema, self.casilla_etiquetas, self.casilla_estelas,
                                self.entrada_hora, self.boton_ir]
        for control in controles_simulacion:
            ventana.cambiar_estado(control, hay_simulacion)
        ventana.cambiar_estado(self.boton_play, hay_simulacion and not self.reproduciendo)
        ventana.cambiar_estado(self.boton_pausa, hay_simulacion and self.reproduciendo)

    def mostrar_error_inesperado(self, tipo, valor, traza):
        """Cualquier error no previsto en un botón se muestra en un diálogo, sin traza (R14)."""
        messagebox.showerror("Error inesperado",
                             "Ha ocurrido un error inesperado:\n" + str(valor)
                             + "\n\nLos datos cargados siguen disponibles.")


def con_miles(numero):
    """Escribe un entero con punto de miles: 189594 -> '189.594'."""
    return format(numero, ",").replace(",", ".")


def formatear_segundos(segundos):
    """Escribe un tiempo con una cifra decimal y coma: 17.04 -> '17,0 s'."""
    return format(segundos, ".1f").replace(".", ",") + " s"


def hora_sin_decimales(segundos):
    """Hora del día hh:mm:ss a partir de los segundos desde medianoche: 14400 -> '04:00:00'."""
    return lector.formatear_hora(segundos)[:8]


def leer_hora(texto):
    """Convierte un texto hh:mm en segundos desde medianoche ('06:30' -> 23400), o None si no es válido."""
    partes = texto.strip().split(":")
    if len(partes) != 2:
        return None
    try:
        horas = int(partes[0])
        minutos = int(partes[1])
    except ValueError:
        return None
    if horas < 0 or horas > 23 or minutos < 0 or minutos > 59:
        return None
    return horas * 3600 + minutos * 60


def main():
    sys.setswitchinterval(INTERVALO_CAMBIO_DE_HILO_S)
    aplicacion = Aplicacion()
    aplicacion.raiz.mainloop()


if __name__ == "__main__":
    main()
