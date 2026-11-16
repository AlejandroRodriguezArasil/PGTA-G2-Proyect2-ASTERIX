"""
prueba_recuentos.py

Comprobación de los recuentos (no forma parte de la aplicación): decodifica los tres
ficheros de la asignatura y compara los recuentos con los esperados.

Uso, desde la carpeta raíz del código: python -m pruebas.prueba_recuentos
(con -m, Python encuentra la carpeta funciones/).
Los ficheros se buscan en ../Docs.Proyecto 2/Aterix files/, relativo a la carpeta raíz del código.
"""

import os

from funciones.decodificar import decodificar_fichero

# Esta carpeta es pruebas/: se sube dos niveles para llegar al lado de la carpeta del código
CARPETA_AST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "Docs.Proyecto 2", "Aterix files")

RADAR = {"registros_048": 503698, "filas_048": 95522, "filas_048_sin_fl": 12318}
ADSB = {"registros_021": 975101, "filas_021": 94072}
CERO_048 = {"registros_048": 0, "filas_048": 0, "filas_048_sin_fl": 0}
CERO_021 = {"registros_021": 0, "filas_021": 0}

PRUEBAS = [
    ("asterix_radar.ast", RADAR, CERO_021),
    ("asterix_adsb.ast", CERO_048, ADSB),
    ("asterix_combinado.ast", RADAR, ADSB),
]

# Nombre en inglés de cada recuento, para escribir el resultado
NOMBRE_RECUENTO = {
    "bloques_desincronizados": "desynchronized blocks",
    "registros_048": "CAT048 records",
    "filas_048": "CAT048 rows",
    "filas_048_sin_fl": "CAT048 rows without FL",
    "registros_021": "CAT021 records",
    "filas_021": "CAT021 rows",
}


def probar_fichero(nombre_fichero, esperado_048, esperado_021):
    """Decodifica un fichero y compara sus recuentos con los esperados. Devuelve True si cuadran todos."""
    print(nombre_fichero)
    _, recuentos = decodificar_fichero(os.path.join(CARPETA_AST, nombre_fichero))

    esperado = {"bloques_desincronizados": 0}
    esperado.update(esperado_048)
    esperado.update(esperado_021)

    todo_bien = True
    for clave in esperado:
        if recuentos[clave] == esperado[clave]:
            resultado = "OK"
        else:
            resultado = "MISMATCH (expected " + str(esperado[clave]) + ")"
            todo_bien = False
        print("  " + NOMBRE_RECUENTO[clave].ljust(26) + str(recuentos[clave]).rjust(8) + "   " + resultado)
    print("  time: " + format(recuentos["segundos"], ".1f") + " s")
    return todo_bien


def main():
    todo_bien = True
    for nombre_fichero, esperado_048, esperado_021 in PRUEBAS:
        if not probar_fichero(nombre_fichero, esperado_048, esperado_021):
            todo_bien = False
    if todo_bien:
        print("All counts match.")
    else:
        print("Some counts do NOT match.")


if __name__ == "__main__":
    main()
