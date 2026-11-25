"""
Conversión de coordenadas del radar a WGS84. Es un port de GeoUtils.cs (el código de la asignatura),
con los mismos nombres para poder comparar. Ángulos en radianes y distancias en metros.
Al final están la posición del radar de Barcelona y el filtro geográfico.
"""

import math


# =============================================================================
# Clases de coordenadas (igual que en GeoUtils.cs)
# =============================================================================

class CoordinatesWGS84:
    """Lat y Lon en radianes, Height en metros."""
    def __init__(self, lat=0.0, lon=0.0, height=0.0):
        self.Lat = lat
        self.Lon = lon
        self.Height = height


class CoordinatesXYZ:
    """Cartesianas, en metros."""
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.X = x
        self.Y = y
        self.Z = z


class CoordinatesPolar:
    """Esféricas del radar: Rho en metros, Theta y Elevation en radianes."""
    def __init__(self, rho=0.0, theta=0.0, elevation=0.0):
        self.Rho = rho
        self.Theta = theta
        self.Elevation = elevation


class CoordinatesUVH:
    """Estereográficas (todo en metros)."""
    def __init__(self, u=0.0, v=0.0, height=0.0):
        self.U = u
        self.V = v
        self.Height = height


# =============================================================================
# Matrices (en vez de portar GeneralMatrix_v2.cs, solo hacen falta estas dos)
# =============================================================================

def multiplicar_matriz_vector(matriz, vector):
    """Matriz 3x3 por vector de 3."""
    resultado = [0.0, 0.0, 0.0]
    for fila in range(3):
        suma = 0.0
        for columna in range(3):
            suma = suma + matriz[fila][columna] * vector[columna]
        resultado[fila] = suma
    return resultado


def transponer_matriz(matriz):
    """Traspuesta de una 3x3."""
    traspuesta = [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]
    for fila in range(3):
        for columna in range(3):
            traspuesta[columna][fila] = matriz[fila][columna]
    return traspuesta


# =============================================================================
# GeoUtils
# =============================================================================

class GeoUtils:
    """La clase GeoUtils del .cs, solo con lo que usamos."""

    # Constantes del original
    FEET2METERS = 0.3048
    NM2METERS = 1852.0
    DEGS2RADS = math.pi / 180.0
    RADS2DEGS = 180.0 / math.pi
    ALMOST_ZERO = 1e-10
    REQUIERED_PRECISION = 1e-8      # la errata ya venía en el original

    def __init__(self):
        """Elipsoide WGS84, como el constructor por defecto del .cs."""
        self.A = 6378137.0              # semieje mayor (m)
        self.B = 6356752.3142           # semieje menor (m)
        self.E2 = 0.00669437999013      # excentricidad^2
        self.centerProjection = None
        self.T1 = None
        self.R1 = None
        self.R_S = 0                    # radio terrestre en el centro de proyección
        # Caché de matrices por radar. La clave es el objeto del radar, así que hay que
        # usar siempre el mismo (si no, el diccionario crece con cada mensaje).
        self.rotationMatrixHT = {}
        self.translationMatrixHT = {}

    # ----- Utilidades ----------------------------------------------------------

    def LatLon2Radians(self, d1, d2, d3, ns):
        """Grados, minutos y segundos a radianes (ns = 1 si es Sur u Oeste)."""
        grados = d1 + (d2 / 60.0) + (d3 / 3600.0)
        if ns == 1:
            grados = -grados
        return grados * GeoUtils.DEGS2RADS

    def CalculateRotationMatrix(self, lat, lon):
        """Matriz de rotación para un punto de latitud y longitud dadas."""
        return [
            [-math.sin(lon), math.cos(lon), 0.0],
            [-math.sin(lat) * math.cos(lon), -math.sin(lat) * math.sin(lon), math.cos(lat)],
            [math.cos(lat) * math.cos(lon), math.cos(lat) * math.sin(lon), math.sin(lat)],
        ]

    def CalculateTranslationMatrix(self, c, A, E2):
        """Posición geocéntrica del punto c."""
        nu = A / math.sqrt(1 - E2 * math.sin(c.Lat) ** 2)
        return [
            (nu + c.Height) * math.cos(c.Lat) * math.cos(c.Lon),
            (nu + c.Height) * math.cos(c.Lat) * math.sin(c.Lon),
            (nu * (1 - E2) + c.Height) * math.sin(c.Lat),
        ]

    def ObtainRotationMatrix(self, radarCoordinates):
        """Igual que CalculateRotationMatrix pero guardando el resultado de cada radar."""
        if radarCoordinates not in self.rotationMatrixHT:
            matriz = self.CalculateRotationMatrix(radarCoordinates.Lat, radarCoordinates.Lon)
            self.rotationMatrixHT[radarCoordinates] = matriz
        return self.rotationMatrixHT[radarCoordinates]

    def ObtainTranslationMatrix(self, radarCoordinates):
        """Lo mismo para el vector de traslación."""
        if radarCoordinates not in self.translationMatrixHT:
            vector = self.CalculateTranslationMatrix(radarCoordinates, self.A, self.E2)
            self.translationMatrixHT[radarCoordinates] = vector
        return self.translationMatrixHT[radarCoordinates]

    # ----- Cadena de CAT048: radar -> WGS84 ----------------------------------

    def CalculateElevation(self, centerCoordinates, R, rho, h):
        """
        Elevación (rad) de un blanco a distancia rho y altura h, vista desde el radar.
        El = asin((2R(h - hR) + h^2 - hR^2 - rho^2) / (2 rho (R + hR)))
        """
        if rho < GeoUtils.ALMOST_ZERO or R == -1.0 or centerCoordinates is None:
            return 0.0   # para no dividir por cero
        altura_radar = centerCoordinates.Height
        seno = (2 * R * (h - altura_radar) + h * h - altura_radar * altura_radar - rho * rho) / \
               (2 * rho * (R + altura_radar))
        if -1.0 < seno < 1.0:
            return math.asin(seno)
        return math.pi / 2.0

    def change_radar_spherical2radar_cartesian(self, polarCoordinates):
        """Esféricas a cartesianas del radar (X este, Y norte, Z arriba)."""
        resultado = CoordinatesXYZ()
        resultado.X = polarCoordinates.Rho * math.cos(polarCoordinates.Elevation) * math.sin(polarCoordinates.Theta)
        resultado.Y = polarCoordinates.Rho * math.cos(polarCoordinates.Elevation) * math.cos(polarCoordinates.Theta)
        resultado.Z = polarCoordinates.Rho * math.sin(polarCoordinates.Elevation)
        return resultado

    def change_radar_cartesian2geocentric(self, radarCoordinates, cartesianCoordinates):
        """Cartesianas del radar a geocéntricas: se gira con R^T y se suma la posición del radar."""
        traslacion = self.ObtainTranslationMatrix(radarCoordinates)
        rotacion = self.ObtainRotationMatrix(radarCoordinates)

        vector = [cartesianCoordinates.X, cartesianCoordinates.Y, cartesianCoordinates.Z]
        girado = multiplicar_matriz_vector(transponer_matriz(rotacion), vector)

        return CoordinatesXYZ(girado[0] + traslacion[0],
                              girado[1] + traslacion[1],
                              girado[2] + traslacion[2])

    def change_geocentric2geodesic(self, c):
        """
        Geocéntricas a latitud, longitud (rad) y altura (m).
        La latitud se itera hasta que cambia menos de REQUIERED_PRECISION (máx. 50 vueltas).
        """
        resultado = CoordinatesWGS84()
        b = 6356752.3142    # en el original también está a mano

        if abs(c.X) < GeoUtils.ALMOST_ZERO and abs(c.Y) < GeoUtils.ALMOST_ZERO:
            # punto en el eje de los polos
            if abs(c.Z) < GeoUtils.ALMOST_ZERO:
                resultado.Lat = math.pi / 2.0
            else:
                resultado.Lat = (math.pi / 2.0) * ((c.Z / abs(c.Z)) + 0.5)
            resultado.Lon = 0.0
            resultado.Height = abs(c.Z) - b
            return resultado

        d_xy = math.sqrt(c.X * c.X + c.Y * c.Y)
        # primera aproximación
        resultado.Lat = math.atan((c.Z / d_xy) /
                                  (1 - (self.A * self.E2) / math.sqrt(d_xy * d_xy + c.Z * c.Z)))
        nu = self.A / math.sqrt(1 - self.E2 * math.sin(resultado.Lat) ** 2)
        resultado.Height = (d_xy / math.cos(resultado.Lat)) - nu

        if resultado.Lat >= 0:
            latitud_anterior = -0.1
        else:
            latitud_anterior = 0.1
        vueltas = 0
        while abs(resultado.Lat - latitud_anterior) > GeoUtils.REQUIERED_PRECISION and vueltas < 50:
            vueltas = vueltas + 1
            latitud_anterior = resultado.Lat
            resultado.Lat = math.atan((c.Z * (1 + resultado.Height / nu)) /
                                      (d_xy * ((1 - self.E2) + (resultado.Height / nu))))
            nu = self.A / math.sqrt(1 - self.E2 * math.sin(resultado.Lat) ** 2)
            resultado.Height = d_xy / math.cos(resultado.Lat) - nu

        resultado.Lon = math.atan2(c.Y, c.X)
        return resultado

    # ----- Proyección estereográfica (para el P3) ------------------------------

    def change_geodesic2geocentric(self, c):
        """Lat, lon y altura a geocéntricas."""
        nu = self.A / math.sqrt(1 - self.E2 * math.sin(c.Lat) ** 2)
        resultado = CoordinatesXYZ()
        resultado.X = (nu + c.Height) * math.cos(c.Lat) * math.cos(c.Lon)
        resultado.Y = (nu + c.Height) * math.cos(c.Lat) * math.sin(c.Lon)
        resultado.Z = (nu * (1 - self.E2) + c.Height) * math.sin(c.Lat)
        return resultado

    def setCenterProjection(self, c):
        """Fija el centro de la proyección (a altura 0) y prepara R_S, T1 y R1."""
        centro = CoordinatesWGS84(c.Lat, c.Lon, 0.0)
        self.centerProjection = centro
        # radio de curvatura del meridiano
        self.R_S = (self.A * (1.0 - self.E2)) / (1 - self.E2 * math.sin(centro.Lat) ** 2) ** 1.5
        self.T1 = self.CalculateTranslationMatrix(centro, self.A, self.E2)
        self.R1 = self.CalculateRotationMatrix(centro.Lat, centro.Lon)
        return self.centerProjection

    def change_geocentric2system_cartesian(self, geo):
        """R1 x (geocéntricas - T1). Antes hay que llamar a setCenterProjection."""
        if self.centerProjection is None:
            return None
        vector = [geo.X - self.T1[0], geo.Y - self.T1[1], geo.Z - self.T1[2]]
        girado = multiplicar_matriz_vector(self.R1, vector)
        return CoordinatesXYZ(girado[0], girado[1], girado[2])

    def change_system_cartesian2stereographic(self, c):
        """Cartesianas del sistema a U, V y altura."""
        resultado = CoordinatesUVH()
        d_xy2 = c.X * c.X + c.Y * c.Y
        resultado.Height = math.sqrt(d_xy2 +
                                     (c.Z + self.centerProjection.Height + self.R_S) *
                                     (c.Z + self.centerProjection.Height + self.R_S)) - self.R_S
        k = (2 * self.R_S) / (2 * self.R_S + self.centerProjection.Height + c.Z + resultado.Height)
        resultado.U = k * c.X
        resultado.V = k * c.Y
        return resultado


# =============================================================================
# Datos del proyecto
# =============================================================================

# Una sola instancia para todo el programa
GEO_UTILS = GeoUtils()

# Radar de Barcelona (enunciado): 41° 18' 02,5284" N, 02° 06' 07,4095" E
# Su altura es la del terreno más la de la antena.
ELEVACION_TERRENO_RADAR_M = 2.007
ALTURA_ANTENA_RADAR_M = 25.25
RADAR_BCN = CoordinatesWGS84(GEO_UTILS.LatLon2Radians(41, 18, 2.5284, 0),
                             GEO_UTILS.LatLon2Radians(2, 6, 7.4095, 0),
                             ELEVACION_TERRENO_RADAR_M + ALTURA_ANTENA_RADAR_M)

# Rt = 6371 km, lo da el enunciado para calcular la elevación
RADIO_TIERRA_M = 6371000.0

# Filtro geográfico: 40,9 < lat < 41,7 y 1,5 < lon < 2,6 (grados)
LATITUD_MINIMA_DEG = 40.9
LATITUD_MAXIMA_DEG = 41.7
LONGITUD_MINIMA_DEG = 1.5
LONGITUD_MAXIMA_DEG = 2.6

def posicion_wgs84_048(rho_nm, theta_deg, altura_m):
    """
    Pasa un blanco CAT048 (rho y theta de I048/040, más su altura) a WGS84.
    Elevación -> cartesianas del radar -> geocéntricas -> geodésicas.
    Devuelve (lat, lon, altura) en grados y metros.
    """
    rho_m = rho_nm * GeoUtils.NM2METERS
    azimut_rad = theta_deg * GeoUtils.DEGS2RADS

    elevacion_rad = GEO_UTILS.CalculateElevation(RADAR_BCN, RADIO_TIERRA_M, rho_m, altura_m)
    esfericas = CoordinatesPolar(rho_m, azimut_rad, elevacion_rad)
    cartesianas_radar = GEO_UTILS.change_radar_spherical2radar_cartesian(esfericas)
    geocentricas = GEO_UTILS.change_radar_cartesian2geocentric(RADAR_BCN, cartesianas_radar)
    geodesicas = GEO_UTILS.change_geocentric2geodesic(geocentricas)

    latitud_deg = geodesicas.Lat * GeoUtils.RADS2DEGS
    longitud_deg = geodesicas.Lon * GeoUtils.RADS2DEGS
    return latitud_deg, longitud_deg, geodesicas.Height


def dentro_de_zona(latitud_deg, longitud_deg):
    """Comprueba si el punto cae dentro del filtro geográfico (sin incluir los bordes)."""
    if not LATITUD_MINIMA_DEG < latitud_deg < LATITUD_MAXIMA_DEG:
        return False
    if not LONGITUD_MINIMA_DEG < longitud_deg < LONGITUD_MAXIMA_DEG:
        return False
    return True
