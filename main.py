"""
Programa principal (python main.py). La clase Aplicacion une los botones de la ventana con funciones/.
El .ast se decodifica una vez en un hilo y lo demás (tabla, filtros, CSV, simulación) usa las filas en memoria.
"""

import math
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
INTERVALO_REVISION_MS = 100          # cada cuánto se mira cómo va el hilo

# Por el GIL, con el cambio de hilo por defecto (5 ms) el hilo que decodifica casi no deja turno a la
# ventana y se congela. Con 0,5 ms responde bien, aunque decodificar tarda un 10 % más.
INTERVALO_CAMBIO_DE_HILO_S = 0.0005

# El salto siempre es de 1 s, la velocidad solo cambia cada cuánto se da
ESPERA_POR_VELOCIDAD_MS = {"x1": 1000, "x2": 500, "x5": 200, "x10": 100, "x30": 33, "x60": 17}
RETRASO_MAXIMO_S = 1.0      # retraso máximo que se intenta recuperar (ver tic_reloj)

# Para las líneas del resumen que cuelgan de la de arriba
SANGRIA_RESUMEN = "      "

# Sale en la opción Radar / ADS-B cuando está desactivada
AYUDA_SIN_PAREJA = "The other system does not show this aircraft on the map."


class Aplicacion:
    """Ventana principal con todo su estado (datos, filtros, página y simulación)."""

    def __init__(self):
        # Datos
        self.filas_todas = []           # tuplas, una por mensaje
        self.filas_visibles = []        # tras los filtros (no se copian las tuplas)
        self.recuentos = None
        self.nombre_fichero = ""
        self.fichero_decodificando = ""     # "" si no se está decodificando
        self.ruta_exportando = None         # None si no se exporta
        self.cancelar_exportacion = False   # se pone a True si se cierra a media exportación
        self.opciones_filtros = None    # None = sin filtros
        self.pagina_actual = 0

        # Hilo (decodificar o exportar)
        self.hilo = None
        self.porcentaje = 0             # lo escribe el hilo, lo lee la ventana
        self.registros_leidos = 0       # igual, solo al decodificar
        self.resultado_hilo = None
        self.error_hilo = None

        # Simulación
        self.estado_simulacion = None   # None si hay que prepararla
        self.reproduciendo = False
        self.id_reloj = None            # para poder cancelar el after()
        self.instante_siguiente_salto = 0.0
        self.espera_ms = ESPERA_POR_VELOCIDAD_MS["x1"]
        self.marcadores = {}            # (categoría, TA) -> marcador
        self.estelas = {}               # (categoría, TA) -> estela
        self.avion_seleccionado = None
        self.aviones_resaltados = set() # el seleccionado y su pareja
        self.mapa_encuadrado = False
        self.arrastrando_barra = False
        self.segundo_barra = 0          # a dónde se salta al soltar la barra
        self.ultimo_evento_mostrado = 0 # para no repetir eventos en el registro

        # Ventana: las funciones de ventana.py guardan los widgets en self (self.tabla, self.boton_abrir...)
        self.raiz = ventana.crear_ventana_principal()
        # errores no previstos en un diálogo y no como traza
        self.raiz.report_callback_exception = self.mostrar_error_inesperado
        self.raiz.protocol("WM_DELETE_WINDOW", self.al_cerrar_ventana)
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
    # 1. Elegir fichero
    # =========================================================================

    def elegir_fichero(self):
        """Pide el .ast con un diálogo y lo decodifica."""
        ruta = filedialog.askopenfilename(
            title="Choose an ASTERIX file",
            filetypes=[("ASTERIX files", "*.ast"), ("All files", "*.*")])
        if ruta == "":
            return
        self.decodificar_en_segundo_plano(ruta)

    # =========================================================================
    # 2. Decodificar en un hilo aparte
    # =========================================================================

    def decodificar_en_segundo_plano(self, ruta):
        """Lanza la decodificación en otro hilo. Si falla, se quedan los datos que ya había."""
        self.pausa()
        self.fichero_decodificando = os.path.basename(ruta)
        self.etiqueta_fichero.configure(text=self.fichero_decodificando)
        self.mostrar_resumen(None)
        self.etiqueta_detalle_resumen.configure(text="Decoding the file...")

        self.porcentaje = 0
        self.registros_leidos = 0
        self.barra_progreso_tabla.set(0)
        ventana.cambiar_texto(self.etiqueta_progreso_tabla, "Decoding " + self.fichero_decodificando + "...  0 %")
        self.resultado_hilo = None
        self.error_hilo = None
        self.hilo = threading.Thread(target=self.tarea_decodificar, args=(ruta,), daemon=True)
        self.hilo.start()

        self.mostrar_pagina()
        self.actualizar_panel_simulacion()
        self.poner_estado("Decoding " + self.fichero_decodificando + "...", estilo.ESTADO_TRABAJANDO)
        self.poner_progreso(0)
        self.raiz.after(INTERVALO_REVISION_MS, self.revisar_decodificacion)

    def tarea_decodificar(self, ruta):
        """Corre en el hilo, así que no toca la ventana: solo deja el resultado o el error."""
        try:
            self.resultado_hilo = decodificar.decodificar_fichero(ruta, self.guardar_progreso_decodificacion)
        except ValueError as error:
            self.error_hilo = "The file is not ASTERIX or it is damaged:\n" + str(error) + "."
        except PermissionError:
            self.error_hilo = "The file could not be read: there is no permission to open it."
        except OSError:
            self.error_hilo = "The file could not be read (it may have been moved or deleted)."
        except MemoryError:
            self.error_hilo = "There is not enough memory to decode this file."
        except Exception as error:
            self.error_hilo = "Unexpected error while decoding:\n" + str(error)

    def guardar_progreso_decodificacion(self, porcentaje, registros_leidos):
        """Callback de progreso de decodificar_fichero (desde el hilo)."""
        self.porcentaje = porcentaje
        self.registros_leidos = registros_leidos

    def guardar_porcentaje(self, porcentaje):
        """
        Progreso de la exportación. Si se ha cerrado la ventana lanza ExportacionCancelada
        para cortar la escritura.
        """
        if self.cancelar_exportacion:
            raise ExportacionCancelada()
        self.porcentaje = porcentaje

    def revisar_decodificacion(self):
        """Cada 100 ms: mueve las barras y, cuando acaba el hilo, enseña los datos o el error."""
        if self.hilo.is_alive():
            self.poner_progreso(self.porcentaje)
            # la barra grande que sale en lugar de la tabla
            self.barra_progreso_tabla.set(self.porcentaje / 100)
            ventana.cambiar_texto(self.etiqueta_progreso_tabla,
                                  "Decoding " + self.fichero_decodificando + "...  " + str(self.porcentaje) + " %  ·  "
                                  + con_miles(self.registros_leidos) + " records read")
            self.raiz.after(INTERVALO_REVISION_MS, self.revisar_decodificacion)
            return

        self.hilo = None
        fichero_nuevo = self.fichero_decodificando
        self.fichero_decodificando = ""
        if self.error_hilo is not None:
            # se quedan los datos de antes, con su nombre y su resumen
            self.mostrar_resumen(self.recuentos)
            self.poner_progreso(0)
            if self.nombre_fichero == "":
                self.etiqueta_fichero.configure(text="No file loaded")
                self.poner_estado("Could not decode " + fichero_nuevo, estilo.TEXTO_SUAVE)
            else:
                self.etiqueta_fichero.configure(text=self.nombre_fichero)
                self.poner_estado("Could not decode " + fichero_nuevo + "; still showing the data of "
                                  + self.nombre_fichero, estilo.TEXTO_SUAVE)
            self.mostrar_pagina()
            self.actualizar_panel_simulacion()
            messagebox.showerror("Decoding error", self.error_hilo)
            return

        filas, recuentos = self.resultado_hilo
        self.resultado_hilo = None
        self.nombre_fichero = fichero_nuevo
        self.mostrar_datos(filas, recuentos)
        # si ya estamos en Simulation se prepara ahora; si no, al entrar en la pestaña
        if self.selector_pestana.get() == "Simulation":
            self.cambiar_pestana("Simulation")

    # =========================================================================
    # 3. Mostrar los datos: resumen y tabla por páginas
    # =========================================================================

    def mostrar_datos(self, filas, recuentos):
        """Guarda las filas nuevas y enseña el resumen y la primera página."""
        self.filas_todas = filas
        self.filas_visibles = filas
        self.recuentos = recuentos
        self.opciones_filtros = None
        self.pagina_actual = 0
        self.mostrar_resumen(recuentos)

        # anchos según la cabecera y las primeras filas
        muestra = []
        for fila in filas[:FILAS_PARA_MEDIR_ANCHOS]:
            muestra.append(celdas_tabla(fila))
        ventana.ajustar_anchos_columnas(self, muestra)

        self.invalidar_simulacion()
        self.mostrar_pagina()
        self.poner_progreso(100)
        self.poner_estado("Decoded in " + formatear_segundos(recuentos["segundos"]) + " · "
                          + con_miles(len(filas)) + " messages", estilo.ESTADO_LISTO)

    def mostrar_resumen(self, recuentos):
        """Rellena la tarjeta de resumen. Con None la deja vacía."""
        if recuentos is None:
            for cifra in (self.cifra_leidos, self.cifra_filas, self.cifra_descartados, self.cifra_tiempo):
                cifra.configure(text="—")
            self.etiqueta_detalle_resumen.configure(text="Open an .ast file to see its summary.")
            return

        leidos = recuentos["registros_048"] + recuentos["registros_021"]
        filas = recuentos["filas_048"] + recuentos["filas_021"]
        fuera_de_zona = recuentos["descartados_048_fuera_de_zona"] + recuentos["descartados_021_fuera_de_zona"]
        sin_posicion = recuentos["descartados_048_sin_posicion"] + recuentos["descartados_021_sin_posicion"]

        self.cifra_leidos.configure(text=con_miles(leidos))
        self.cifra_filas.configure(text=con_miles(filas))
        self.cifra_descartados.configure(text=con_miles(leidos - filas))
        self.cifra_tiempo.configure(text=format(recuentos["segundos"], ".1f"))

        # Líneas cortas para que no se partan en el panel, aunque las cifras tengan 7 dígitos
        lineas = [
            "CAT048: " + con_miles(recuentos["registros_048"]) + " read · " + con_miles(recuentos["filas_048"])
            + " in the table",
            SANGRIA_RESUMEN + con_miles(recuentos["filas_048_sin_fl"]) + " of them without FL",
            "CAT021: " + con_miles(recuentos["registros_021"]) + " read · " + con_miles(recuentos["filas_021"])
            + " in the table",
            "Discarded: " + con_miles(fuera_de_zona) + " outside the area",
            SANGRIA_RESUMEN + con_miles(recuentos["descartados_021_en_tierra"]) + " CAT021 on ground (GBS)",
            SANGRIA_RESUMEN + con_miles(sin_posicion) + " without position",
            "Desynchronized blocks: " + con_miles(recuentos["bloques_desincronizados"]),
        ]
        if recuentos["lectura_parada"] == lector.BLOQUE_CORTADO:
            lineas.append("Incomplete file: the last block was")
            lineas.append("cut off and has not been read.")
        elif recuentos["lectura_parada"] == lector.LEN_NO_VALIDO:
            lineas.append("Damaged block (invalid LEN) at byte")
            lineas.append(con_miles(recuentos["octeto_parada"]) + ": read up to there.")
        self.etiqueta_detalle_resumen.configure(text="\n".join(lineas))

    def numero_de_paginas(self):
        """Páginas de la tabla (mínimo 1)."""
        paginas = (len(self.filas_visibles) + FILAS_POR_PAGINA - 1) // FILAS_POR_PAGINA
        if paginas == 0:
            paginas = 1
        return paginas

    def mostrar_pagina(self):
        """Vuelve a llenar la tabla con la página actual."""
        for elemento in self.tabla.get_children():
            self.tabla.delete(elemento)

        total = len(self.filas_visibles)
        primera = self.pagina_actual * FILAS_POR_PAGINA
        ultima = min(primera + FILAS_POR_PAGINA, total)
        for numero_fila in range(primera, ultima):
            celdas = celdas_tabla(self.filas_visibles[numero_fila])
            if numero_fila % 2 == 1:
                self.tabla.insert("", "end", values=celdas, tags=("alterna",))
            else:
                self.tabla.insert("", "end", values=celdas)
        self.tabla.yview_moveto(0)

        self.etiqueta_pagina.configure(text="Page " + con_miles(self.pagina_actual + 1)
                                       + " of " + con_miles(self.numero_de_paginas()))
        if total == 0:
            self.etiqueta_total.configure(text="")
        else:
            texto = ("Showing " + con_miles(primera + 1) + "-" + con_miles(ultima)
                     + " of " + con_miles(total) + " messages")
            if self.opciones_filtros is not None:
                texto = texto + " (" + con_miles(len(self.filas_todas)) + " unfiltered)"
            self.etiqueta_total.configure(text=texto)

        self.actualizar_estado_vacio_tabla()
        self.actualizar_botones()

    def actualizar_estado_vacio_tabla(self):
        """Con la tabla vacía pone encima la barra de progreso o un mensaje de por qué no hay filas."""
        if self.fichero_decodificando != "":
            self.estado_vacio_tabla.place_forget()
            self.progreso_tabla.place(relx=0.5, rely=0.45, anchor="center")
            return
        self.progreso_tabla.place_forget()

        boton = ""
        if self.recuentos is None:
            mensaje = "Open an .ast file to start.\nIts CAT048 and CAT021 messages will be decoded."
            boton = "abrir"
        elif len(self.filas_todas) == 0:
            mensaje = ("No message in the file passes the mandatory discards\n"
                       "(no position, outside the geographic area or CAT021 on ground).")
        elif len(self.filas_visibles) == 0:
            mensaje = "No message matches the filters."
            boton = "quitar"
        else:
            self.estado_vacio_tabla.place_forget()
            return

        self.etiqueta_vacio_tabla.configure(text=mensaje)
        if boton == "abrir":
            self.boton_vacio_tabla.configure(text="Open .ast file", command=self.elegir_fichero)
            self.boton_vacio_tabla.pack(pady=(0, 24))
        elif boton == "quitar":
            self.boton_vacio_tabla.configure(text="Clear filters", command=self.quitar_filtros)
            self.boton_vacio_tabla.pack(pady=(0, 24))
        else:
            self.boton_vacio_tabla.pack_forget()
        self.estado_vacio_tabla.place(relx=0.5, rely=0.45, anchor="center")

    def pagina_anterior(self):
        """Botón de página anterior."""
        if self.pagina_actual > 0:
            self.pagina_actual = self.pagina_actual - 1
            self.mostrar_pagina()

    def pagina_siguiente(self):
        """Pasa a la página siguiente."""
        if self.pagina_actual < self.numero_de_paginas() - 1:
            self.pagina_actual = self.pagina_actual + 1
            self.mostrar_pagina()

    # =========================================================================
    # 4. Filtrar
    # =========================================================================

    def leer_opciones_filtros(self):
        """Lee el panel de filtros y devuelve las opciones, o None si la altitud no es un número."""
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
                altitud = float(texto_altitud.replace(",", "."))
            except ValueError:
                altitud = None
            # float() acepta "nan" e "inf", y eso no es una altitud
            if altitud is None or not math.isfinite(altitud):
                messagebox.showwarning("Invalid altitude",
                                       "The maximum altitude must be a number in ft, for example 6000.")
                return None
            opciones["altitud_maxima_ft"] = altitud

        opciones["aeronave"] = self.entrada_aeronave.get().strip()
        return opciones

    def aplicar_filtros(self):
        """Aplica a la vez todos los filtros marcados."""
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
        self.poner_estado("Filtered: " + con_miles(len(self.filas_visibles)) + " of "
                          + con_miles(len(self.filas_todas)) + " messages", estilo.ESTADO_LISTO)

    def aplicar_filtros_con_intro(self, evento):
        """Intro en un campo de los filtros hace lo mismo que el botón de aplicar."""
        if ventana.esta_activo(self.boton_aplicar):
            self.aplicar_filtros()

    def quitar_filtros(self):
        """Botón "Clear filters": deja el panel como al principio y vuelve a enseñar todo."""
        self.selector_categoria.set("Both")
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
        self.poner_estado("No filters: " + con_miles(len(self.filas_todas)) + " messages", estilo.ESTADO_LISTO)

    # =========================================================================
    # 5. Exportar a CSV
    # =========================================================================

    def exportar_todo(self):
        """Exporta todas las filas decodificadas."""
        nombre_base = os.path.splitext(self.nombre_fichero)[0]
        self.exportar(self.filas_todas, nombre_base + ".csv")

    def exportar_filtrado(self):
        """Como exportar_todo, pero solo con las filas filtradas."""
        nombre_base = os.path.splitext(self.nombre_fichero)[0]
        self.exportar(self.filas_visibles, nombre_base + "_filtered.csv")

    def exportar(self, filas, nombre_sugerido):
        """Pregunta dónde guardar el CSV y empieza a escribirlo."""
        ruta = filedialog.asksaveasfilename(
            title="Save CSV", initialfile=nombre_sugerido, defaultextension=".csv",
            filetypes=[("CSV separated by ';'", "*.csv")])
        if ruta == "":
            return
        self.empezar_exportacion(ruta, filas)

    def empezar_exportacion(self, ruta, filas):
        """Escribe el CSV en otro hilo para que no se congele la ventana."""
        self.porcentaje = 0
        self.resultado_hilo = None
        self.error_hilo = None
        self.ruta_exportando = ruta
        self.cancelar_exportacion = False
        self.hilo = threading.Thread(target=self.tarea_exportar, args=(ruta, filas), daemon=True)
        self.hilo.start()
        self.actualizar_botones()
        self.poner_estado("Exporting " + con_miles(len(filas)) + " messages...", estilo.ESTADO_TRABAJANDO)
        self.poner_progreso(0)
        self.raiz.after(INTERVALO_REVISION_MS, self.revisar_exportacion)

    def tarea_exportar(self, ruta, filas):
        """Hilo de la exportación; igual que tarea_decodificar, no toca la ventana."""
        instante_inicio = time.time()
        try:
            exportar_csv.exportar(ruta, filas, self.guardar_porcentaje)
            self.resultado_hilo = (ruta, len(filas), time.time() - instante_inicio)
        except ExportacionCancelada:
            return              # ventana cerrada, el CSV a medias lo borra revisar_exportacion
        except PermissionError:
            self.error_hilo = ("The CSV could not be saved: the file is open in another program\n"
                               "or there is no permission to write in that folder. If it is open in Excel,\n"
                               "close it and try again.")
        except OSError:
            self.error_hilo = "The CSV could not be saved in that folder. Try another one."
        except Exception as error:
            self.error_hilo = "Unexpected error while exporting:\n" + str(error)

    def revisar_exportacion(self):
        """Mira cada 100 ms cómo va la exportación y avisa al acabar."""
        if self.hilo.is_alive():
            self.poner_progreso(self.porcentaje)
            self.raiz.after(INTERVALO_REVISION_MS, self.revisar_exportacion)
            return

        self.hilo = None
        ruta_exportada = self.ruta_exportando
        self.ruta_exportando = None
        if self.cancelar_exportacion:
            # se cerró a medias: se borra el CSV incompleto (el hilo ya lo ha cerrado) y se sale
            try:
                os.remove(ruta_exportada)
            except OSError:
                pass                    # si lo tiene abierto otro programa, se cierra igual
            self.raiz.destroy()
            return
        self.actualizar_botones()
        if self.error_hilo is not None:
            self.poner_progreso(0)
            self.poner_estado("Could not export", estilo.TEXTO_SUAVE)
            messagebox.showerror("Export error", self.error_hilo)
            return

        ruta, numero_filas, segundos = self.resultado_hilo
        self.poner_progreso(100)
        self.poner_estado("Exported in " + formatear_segundos(segundos) + ": " + ruta, estilo.ESTADO_LISTO)
        messagebox.showinfo("Export finished",
                            "Saved " + con_miles(numero_filas) + " messages to:\n" + ruta)

    # =========================================================================
    # 6. Simular en el mapa
    # =========================================================================

    def cambiar_pestana(self, pestana):
        """Cambia entre Data y Simulation. Al ir a Data la simulación se queda en pausa."""
        if pestana == "Data":
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
        Para cuando cambian los datos o los filtros: para la simulación y vacía mapa, listas y eventos.
        Se vuelve a preparar al entrar en Simulation o al tocar uno de sus controles.
        """
        self.pausa()
        mapa.borrar_todos(self)
        self.estado_simulacion = None
        self.avion_seleccionado = None
        self.aviones_resaltados = set()
        self.casilla_seguir.deselect()
        self.vaciar_registro_eventos()
        self.lista_en_vuelo.vaciar()
        self.lista_en_tierra.vaciar()
        ventana.configurar_barra_tiempo(self, 0, 1, "--:--", "--:--")
        ventana.escribir_texto(self.cuadro_info, ventana.TEXTO_SIN_AVION)
        self.actualizar_panel_simulacion()

    def preparar_simulacion(self):
        """Prepara la simulación con los mensajes filtrados y dibuja el primer segundo."""
        self.estado_simulacion = simulacion.preparar(self.filas_visibles)
        inicio = self.estado_simulacion["inicio"]
        fin = self.estado_simulacion["fin"]
        ventana.configurar_barra_tiempo(self, inicio, fin, hora_sin_decimales(inicio)[:5],
                                        hora_sin_decimales(fin)[:5])
        self.vaciar_registro_eventos()
        mapa.redibujar_todos(self, self.estado_simulacion["aviones"])
        mapa.actualizar_resaltado(self, self.estado_simulacion["aviones"])
        self.actualizar_panel_simulacion()
        self.actualizar_botones()

    def play(self):
        """Arranca el reloj de la simulación."""
        if self.estado_simulacion is None:
            self.preparar_simulacion()
        if simulacion.ha_terminado(self.estado_simulacion):
            messagebox.showinfo("Simulation", "The simulation has reached the end of the data.\n"
                                              "Press Reset or choose a time to start again.")
            return
        if self.reproduciendo:
            return
        self.reproduciendo = True
        self.actualizar_botones()
        self.poner_estado("Playing at " + self.selector_velocidad.get(), estilo.ESTADO_LISTO)
        self.instante_siguiente_salto = time.perf_counter() + self.espera_ms / 1000
        self.id_reloj = self.raiz.after(self.espera_ms, self.tic_reloj)

    def pausa(self):
        """Para el reloj."""
        if self.reproduciendo:
            self.poner_estado("Simulation paused", estilo.TEXTO_SUAVE)
        self.reproduciendo = False
        if self.id_reloj is not None:
            self.raiz.after_cancel(self.id_reloj)
            self.id_reloj = None
        self.actualizar_botones()

    def tic_reloj(self):
        """
        Un tic del reloj: salto de 1 s y se programa el siguiente con after().
        En Windows after() va a saltos de unos 15,6 ms, así que se espera hasta la hora prevista
        del salto y no un tiempo fijo. Con más de RETRASO_MAXIMO_S de retraso ya no se recupera.
        """
        self.id_reloj = None
        if not self.reproduciendo:
            return
        self.dar_un_salto()
        if simulacion.ha_terminado(self.estado_simulacion):
            self.pausa()
            self.poner_estado("End of the data: press Reset to start again", estilo.TEXTO_SUAVE)
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
        """Avanza 1 s: mueve los aviones con mensaje nuevo, quita los caducados y actualiza los paneles."""
        cambiados, caducados = simulacion.avanzar_un_segundo(self.estado_simulacion)
        for identificador in caducados:
            mapa.borrar_avion(self, identificador)
        aviones = self.estado_simulacion["aviones"]
        for identificador in cambiados:
            if mapa.sistema_visible(self, identificador[0]):
                mapa.dibujar_avion(self, identificador, aviones[identificador])
        # la etiqueta puede cambiar de silueta (o ponerse/quitarse) solo en estos aviones
        direcciones = set()
        for identificador in cambiados:
            direcciones.add(identificador[1])
        for identificador in caducados:
            direcciones.add(identificador[1])
        mapa.actualizar_etiquetas_de(self, aviones, direcciones)
        mapa.actualizar_resaltado(self, aviones)
        self.seguir_avion(cambiados)
        self.actualizar_panel_simulacion()

    def seguir_avion(self, cambiados):
        """Con Seguir marcada, centra el mapa en el seleccionado solo si se ha movido."""
        if self.casilla_seguir.get() == 0 or self.avion_seleccionado is None:
            return
        if self.avion_seleccionado not in self.marcadores:
            self.casilla_seguir.deselect()
            return
        if self.avion_seleccionado in cambiados:
            mapa.centrar_en_avion(self, self.estado_simulacion["aviones"][self.avion_seleccionado])

    def avanzar_un_segundo(self):
        """Botón +1 s (vale en pausa y en marcha)."""
        if self.estado_simulacion is None:
            self.preparar_simulacion()
        if not simulacion.ha_terminado(self.estado_simulacion):
            self.dar_un_salto()

    def reset_simulacion(self):
        """Vuelve al principio de los datos, en pausa."""
        self.pausa()
        if self.estado_simulacion is None:
            self.preparar_simulacion()
            return
        self.saltar_a_segundo(self.estado_simulacion["inicio"])

    def ir_a_hora(self):
        """Salta a la hora hh:mm del campo de texto."""
        segundo = leer_hora(self.entrada_hora.get())
        if segundo is None:
            messagebox.showwarning("Invalid time", "Type the time as hh:mm, for example 06:30.")
            return
        if self.estado_simulacion is None:
            self.preparar_simulacion()
        inicio = self.estado_simulacion["inicio"]
        fin = self.estado_simulacion["fin"]
        # se acepta el minuto en que empiezan los datos (08:00 aunque empiecen a las 08:00:03)
        if segundo < inicio - inicio % 60 or segundo > fin:
            messagebox.showwarning("Time outside the data",
                                   "The data go from " + hora_sin_decimales(inicio) + " to "
                                   + hora_sin_decimales(fin) + " UTC.")
            return
        self.saltar_a_segundo(segundo)

    def ir_a_hora_con_intro(self, evento):
        """Intro en el campo de la hora, igual que el botón "Ir"."""
        if ventana.esta_activo(self.boton_ir):
            self.ir_a_hora()

    def mover_barra_tiempo(self, valor):
        """
        Mientras se arrastra la barra solo cambia el reloj. El salto se hace al soltar,
        porque saltar en cada movimiento trabaría la barra.
        """
        self.arrastrando_barra = True
        self.segundo_barra = int(valor)
        ventana.cambiar_texto(self.etiqueta_reloj, hora_sin_decimales(self.segundo_barra))

    def soltar_barra_tiempo(self, evento):
        """Al soltar la barra se salta a la hora elegida."""
        if not self.arrastrando_barra:
            return                          # clic sin arrastrar, o barra desactivada
        self.arrastrando_barra = False
        if self.estado_simulacion is None:
            self.preparar_simulacion()
            return
        self.saltar_a_segundo(self.segundo_barra)

    def saltar_a_segundo(self, segundo):
        """
        Lleva la simulación a ese segundo y redibuja el mapa. El registro de eventos se vacía
        porque ir_a_segundo recalcula los aviones sin generar eventos.
        """
        simulacion.ir_a_segundo(self.estado_simulacion, segundo)
        self.vaciar_registro_eventos()
        mapa.redibujar_todos(self, self.estado_simulacion["aviones"])
        mapa.actualizar_resaltado(self, self.estado_simulacion["aviones"])
        if self.casilla_seguir.get() == 1 and self.avion_seleccionado in self.marcadores:
            mapa.centrar_en_avion(self, self.estado_simulacion["aviones"][self.avion_seleccionado])
        self.actualizar_panel_simulacion()

    def vaciar_registro_eventos(self):
        """Vacía el registro de eventos de la ventana."""
        self.registro_eventos.vaciar()
        self.ultimo_evento_mostrado = 0

    def cambiar_velocidad(self, velocidad):
        """Cambia la espera entre saltos (el salto sigue siendo de 1 s)."""
        self.espera_ms = ESPERA_POR_VELOCIDAD_MS[velocidad]
        self.instante_siguiente_salto = time.perf_counter()
        if self.reproduciendo:
            self.poner_estado("Playing at " + velocidad, estilo.ESTADO_LISTO)

    def cambiar_sistema(self, sistema):
        """Selector de sistema: redibuja solo los aviones de Radar, de ADS-B o de los dos."""
        if self.estado_simulacion is not None:
            mapa.redibujar_todos(self, self.estado_simulacion["aviones"])
            mapa.actualizar_resaltado(self, self.estado_simulacion["aviones"])
        self.actualizar_panel_simulacion()

    def cambiar_etiquetas(self):
        """Enseña u oculta las etiquetas de los aviones."""
        if self.estado_simulacion is not None:
            mapa.actualizar_etiquetas(self, self.estado_simulacion["aviones"])

    def cambiar_estelas(self):
        """Casilla de las estelas."""
        if self.estado_simulacion is not None:
            mapa.redibujar_todos(self, self.estado_simulacion["aviones"])
            mapa.actualizar_resaltado(self, self.estado_simulacion["aviones"])

    def cambiar_mapa(self, aspecto):
        """Mapa oscuro o claro (hay que volver a pedir las teselas)."""
        mapa.cambiar_aspecto_mapa(self, aspecto == "Dark")

    def cambiar_seguir(self):
        """Al marcar Seguir se centra ya en el avión seleccionado, sin esperar a que se mueva."""
        if self.casilla_seguir.get() == 1 and self.avion_seleccionado in self.marcadores:
            mapa.centrar_en_avion(self, self.estado_simulacion["aviones"][self.avion_seleccionado])

    def seleccionar_avion(self, identificador, centrar):
        """
        Selecciona un avión (se resalta también su pareja) y enseña sus datos en el panel.
        Se centra en él si 'centrar' es True o si Seguir está marcada.
        """
        anterior = self.avion_seleccionado
        self.avion_seleccionado = identificador
        aviones = self.estado_simulacion["aviones"]
        # en tierra solo lleva etiqueta el seleccionado, por eso se repasan el anterior y el nuevo
        direcciones = {identificador[1]}
        if anterior is not None:
            direcciones.add(anterior[1])
        mapa.actualizar_etiquetas_de(self, aviones, direcciones)
        mapa.actualizar_resaltado(self, aviones)
        if centrar or self.casilla_seguir.get() == 1:
            mapa.centrar_en_avion(self, aviones[identificador])
        self.actualizar_panel_simulacion()

    def al_pulsar_avion(self, marcador):
        """Clic en un avión del mapa."""
        self.seleccionar_avion(marcador.data, False)

    def al_pulsar_fila_trafico(self, evento):
        """Clic en una fila del tráfico: selecciona el avión (mejor la silueta de radar) y lo centra."""
        direccion_modo_s = evento.widget.identify_row(evento.y)     # "" si no se ha pulsado en una fila
        if direccion_modo_s == "" or self.estado_simulacion is None:
            return
        identificador = mapa.avion_en_mapa_por_ta(self, direccion_modo_s)
        if identificador is not None:
            self.seleccionar_avion(identificador, True)

    def al_pulsar_evento(self, evento):
        """Al pulsar un evento se selecciona su avión, si sigue en el mapa."""
        fila = evento.widget.identify_row(evento.y)
        direccion_modo_s = self.registro_eventos.ta_de_fila(fila)
        if direccion_modo_s is None or self.estado_simulacion is None:
            return
        identificador = mapa.avion_en_mapa_por_ta(self, direccion_modo_s)
        if identificador is None:
            self.poner_estado("That aircraft is no longer in view.", estilo.TEXTO_SUAVE)
            return
        self.seleccionar_avion(identificador, True)

    def cambiar_sistema_avion(self, sistema):
        """
        Pasa la selección a la pareja del otro sistema (misma TA). 'sistema' no se usa: como solo
        hay dos, pulsar la otra opción siempre es ir a la pareja.
        """
        pareja = mapa.pareja_otro_sistema(self.avion_seleccionado)
        if pareja is None:
            return
        self.avion_seleccionado = pareja
        self.actualizar_panel_simulacion()

    def actualizar_selector_sistema_avion(self):
        """
        Pone el selector Radar / ADS-B del panel según el avión seleccionado; la otra opción solo
        se activa si la pareja está en el mapa. No toca nada si ya estaba igual (si no, parpadea).
        """
        if self.avion_seleccionado is None:
            # se reactivan las dos para que no se quede la ayuda de una pareja que ya no está
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
        Actualiza todo el panel de la simulación (reloj, tráfico, eventos, avión seleccionado...).
        Se llama en cada salto, así que cada parte solo cambia lo que es distinto.
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
            ventana.escribir_contadores_trafico(self, 0, 0)
            ventana.cambiar_texto(self.etiqueta_totales_eventos, "Takeoffs: 0 · Landings: 0")
            return

        # al arrastrar la barra el reloj lo pone mover_barra_tiempo
        if not self.arrastrando_barra:
            ventana.cambiar_texto(self.etiqueta_reloj, hora_sin_decimales(estado["segundo"]))
            self.barra_tiempo.set(estado["segundo"])
        self.actualizar_trafico()
        self.actualizar_registro_eventos()

        if self.avion_seleccionado is None:
            return
        if self.avion_seleccionado in estado["aviones"]:
            texto = mapa.texto_informacion(estado["aviones"][self.avion_seleccionado], self.avion_seleccionado,
                                           simulacion.texto_estado_avion(estado, self.avion_seleccionado))
        else:
            texto = ("The selected aircraft is no longer in view (more than "
                     + str(simulacion.SEGUNDOS_PARA_CADUCAR) + " s without messages).")
        ventana.escribir_texto(self.cuadro_info, texto)

    def actualizar_trafico(self):
        """Panel de tráfico: listas En vuelo / En tierra, sus contadores y las cifras del mapa."""
        estado = self.estado_simulacion
        en_vuelo, en_tierra = simulacion.filas_trafico(estado, mapa.categorias_visibles(self))
        self.lista_en_vuelo.actualizar(en_vuelo)
        self.lista_en_tierra.actualizar(en_tierra)
        ventana.escribir_contadores_trafico(self, len(en_vuelo), len(en_tierra))

        radar, adsb, blancos_puros = mapa.contar_en_mapa(self, estado["aviones"])
        ventana.cambiar_texto(self.cifra_radar, str(radar))
        ventana.cambiar_texto(self.cifra_adsb, str(adsb))
        ventana.cambiar_texto(self.cifra_blancos_puros, str(blancos_puros))

        direccion_seleccionada = None
        if self.avion_seleccionado is not None:
            direccion_seleccionada = self.avion_seleccionado[1]
        self.lista_en_vuelo.seleccionar(direccion_seleccionada)
        self.lista_en_tierra.seleccionar(direccion_seleccionada)

    def actualizar_registro_eventos(self):
        """Añade los eventos nuevos al registro y actualiza los totales."""
        estado = self.estado_simulacion
        nuevos = simulacion.eventos_nuevos(estado, self.ultimo_evento_mostrado)
        if len(nuevos) > 0:
            self.registro_eventos.anadir(nuevos)
            self.ultimo_evento_mostrado = nuevos[-1]["numero"]
        ventana.cambiar_texto(self.etiqueta_totales_eventos, "Takeoffs: " + str(estado["despegues"])
                              + " · Landings: " + str(estado["aterrizajes"]))

    def actualizar_aviso_simulacion(self):
        """Texto de encima del mapa con cuántos mensajes se simulan y qué filtros hay."""
        if len(self.filas_todas) == 0:
            texto = "Open an .ast file to simulate its trajectories."
        elif self.opciones_filtros is None:
            texto = ("Simulating the " + con_miles(len(self.filas_visibles))
                     + " messages of the Data tab (no filters).")
        else:
            texto = ("Simulating the " + con_miles(len(self.filas_visibles)) + " messages filtered in Data. "
                     + "Active filters: " + filtros.describir_filtros(self.opciones_filtros) + ".")
        ventana.cambiar_texto(self.etiqueta_aviso_simulacion, texto)

    def actualizar_mensaje_mapa(self):
        """Mensaje en el centro del mapa cuando no hay nada que ver."""
        mensaje = ""
        if self.fichero_decodificando != "":
            mensaje = "Decoding the file..."
        elif len(self.filas_todas) == 0:
            mensaje = "No file is loaded.\nOpen an .ast file with the button at the top right."
        elif len(self.filas_visibles) == 0:
            mensaje = "The filters of the Data tab leave no messages.\nClear or change the filters in Data."
        elif self.estado_simulacion is not None:
            sistema = self.selector_sistema.get()
            mensajes = self.estado_simulacion["mensajes_por_categoria"]
            if sistema == "ADS-B" and mensajes[21] == 0:
                mensaje = ("There are no ADS-B (CAT021) messages among those filtered in Data.\n"
                           "Choose “Radar” or “Both” in System, or change the filters in Data.")
            elif sistema == "Radar" and mensajes[48] == 0:
                mensaje = ("There are no radar (CAT048) messages among those filtered in Data.\n"
                           "Choose “ADS-B” or “Both” in System, or change the filters in Data.")
            elif len(self.marcadores) == 0:
                mensaje = ("No aircraft in view at " + hora_sin_decimales(self.estado_simulacion["segundo"])
                           + ".\nPress Play or choose another time.")

        if mensaje == "":
            self.mensaje_mapa.place_forget()
        else:
            ventana.cambiar_texto(self.etiqueta_mensaje_mapa, mensaje)
            self.mensaje_mapa.place(relx=0.5, rely=0.5, anchor="center")

    # =========================================================================
    # Utilidades de la ventana
    # =========================================================================

    def poner_estado(self, texto, color):
        """Cambia el texto de la barra de estado y el color del punto."""
        self.etiqueta_estado.configure(text=texto)
        self.punto_estado.configure(text_color=color)

    def poner_progreso(self, porcentaje):
        """Barra de progreso de abajo (porcentaje de 0 a 100)."""
        self.barra_progreso.set(porcentaje / 100)
        self.etiqueta_porcentaje.configure(text=str(porcentaje) + " %")

    def actualizar_botones(self):
        """Activa o desactiva los controles según si hay datos y si el hilo está trabajando."""
        trabajando = self.hilo is not None
        hay_datos = len(self.filas_todas) > 0 and not trabajando

        ventana.cambiar_estado(self.boton_abrir, not trabajando)
        ventana.cambiar_estado(self.boton_vacio_tabla, not trabajando)    # el del centro con la tabla vacía

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
                                self.casilla_seguir, self.entrada_hora, self.boton_ir, self.barra_tiempo]
        for control in controles_simulacion:
            ventana.cambiar_estado(control, hay_simulacion)
        ventana.cambiar_estado(self.boton_play, hay_simulacion and not self.reproduciendo)
        ventana.cambiar_estado(self.boton_pausa, hay_simulacion and self.reproduciendo)

    def al_cerrar_ventana(self):
        """
        Al cerrar la ventana. Si se está exportando pregunta antes; si se cierra igual, el hilo para
        y revisar_exportacion borra el CSV a medias.
        """
        if self.ruta_exportando is None:
            self.raiz.destroy()
            return
        cerrar = messagebox.askyesno("Export in progress", "The CSV is being exported. If you close now, "
                                                             "it will be incomplete.\nClose anyway?")
        if not cerrar:
            return
        if self.ruta_exportando is None:
            self.raiz.destroy()                 # ha acabado mientras se preguntaba
        else:
            self.cancelar_exportacion = True

    def mostrar_error_inesperado(self, tipo, valor, traza):
        """Enseña en un diálogo los errores no previstos de los botones."""
        messagebox.showerror("Unexpected error",
                             "An unexpected error has occurred:\n" + str(valor)
                             + "\n\nThe loaded data are still available.")


class ExportacionCancelada(Exception):
    """Sirve para cortar la exportación si se cierra la ventana."""


def con_miles(numero):
    """Entero con coma de miles, como en inglés: 189594 -> '189,594'."""
    return format(numero, ",")


def formatear_segundos(segundos):
    """17.04 -> '17.0 s'"""
    return format(segundos, ".1f") + " s"


def celdas_tabla(fila):
    """Celdas de una fila para la tabla: las del CSV pero con punto decimal (la interfaz va en inglés)."""
    celdas = []
    for celda in exportar_csv.formatear_fila(fila):
        celdas.append(celda.replace(",", "."))
    return celdas


def hora_sin_decimales(segundos):
    """Segundos desde medianoche a 'hh:mm:ss' (14400 -> '04:00:00')."""
    return lector.formatear_hora(segundos)[:8]


def leer_hora(texto):
    """Pasa 'hh:mm' a segundos desde medianoche; None si no es una hora válida."""
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
