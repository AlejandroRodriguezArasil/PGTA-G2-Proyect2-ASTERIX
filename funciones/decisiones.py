"""
decisiones.py

Dudas del enunciado enviadas al profesor (numeradas como en el correo) y la decisión que
se aplica mientras no responda. Cambiar una decisión es cambiar una línea de este fichero.
Las dudas 7, 9, 10, 11 y 12 no son un valor sino una forma de hacer las cosas: se indica
dónde están aplicadas.
"""

# Duda 1. ¿Qué es presión estándar en CAT021? El BPS va en saltos de 0,8 hPa y nunca cae en 1013-1013,5.
# Decisión: 1013-1013,5 hPa en CAT048 (D14); 1012,8 y 1013,6 hPa en CAT021. (qnh.py)
PRESION_ESTANDAR_048_MINIMA_HPA = 1013.0
PRESION_ESTANDAR_048_MAXIMA_HPA = 1013.5
PRESIONES_ESTANDAR_021_HPA = (1012.8, 1013.6)

# Duda 2. ¿El umbral de 6000 ft se compara con FL x 100 sin corregir?
# Decisión: sí. (qnh.py)
UMBRAL_QNH_FT = 6000

# Duda 3. ¿Qué se hace por debajo de 6000 ft si el avión nunca ha enviado un BP no estándar?
# Decisión: no se corrige y la celda queda vacía (False: se escribe FL x 100). (qnh.py)
SIN_BP_GUARDADO_CELDA_VACIA = True

# Duda 4. ¿Qué lleva la columna de altitud corregida a 6000 ft o más?
# Decisión: celda vacía (False: se escribe FL x 100). (qnh.py)
POR_ENCIMA_DEL_UMBRAL_CELDA_VACIA = True

# Duda 5. ¿El BP guardado se borra al subir de 6000 ft?
# Decisión: se borra al cruzar 6000 ft hacia arriba; un BP no estándar se guarda a cualquier altitud. (qnh.py)
BORRAR_BP_AL_CRUZAR_HACIA_ARRIBA = True

# Duda 6. ¿Se corrige un FL no validado (V = 1) o garbled (G = 1)?
# Decisión: sí, y V y G se guardan en sus columnas. (qnh.py)
CORREGIR_FL_NO_VALIDADO_O_GARBLED = True

# Duda 7. ¿Qué altura se usa para transformar CAT048: FL o altitud corregida?
# Decisión: FL sin corregir. (decodificar.py, procesar_registro_048)

# Duda 8. ¿Y si un mensaje CAT048 no trae FL?
# Decisión: se transforma con h = 0 y la columna H_SIN_FL vale 1. (decodificar.py)
ALTURA_SI_NO_HAY_FL_M = 0.0

# Duda 9. ¿De dónde sale la h WGS84 de CAT021?
# Decisión: FL x 100 ft en metros; sin FL, H vacía y H_SIN_FL = 1. (decodificar.py, procesar_registro_021)

# Duda 10. ¿Se descartan los mensajes sin posición?
# Decisión: sí. (decodificar.py para CAT048 y cat021.py para CAT021)

# Duda 11. ¿El fichero combinado va en un CSV o en uno por categoría?
# Decisión: un solo CSV con la columna CAT, en el orden del fichero. (exportar_csv.py)

# Duda 12. ¿I021/040 se decodifica entero o solo el GBS?
# Decisión: entero. (cat021.py, decode_i021_040)

# Duda 13. ¿TYP = 000 (sin detección) cuenta como blanco puro?
# Decisión: sí. Blanco puro = TYP de I048/020 en esta lista. (filtros.py, es_blanco_puro)
TIPOS_BLANCO_PURO = (0, 1, 2, 3)

# Duda 14. ¿Cómo se identifica el transponder fijo? RAB vale 0 en todos los mensajes; el 7777 sí aparece.
# Decisión: Modo 3/A 7777 o RAB = 1. (filtros.py, es_transponder_fijo)
MODO_3A_TRANSPONDER_FIJO = "7777"
RAB_TRANSPONDER_FIJO = 1
