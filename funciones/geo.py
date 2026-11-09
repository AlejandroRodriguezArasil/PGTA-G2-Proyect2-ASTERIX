"""
geo.py

Paso 3 del flujo: COORDENADAS.
    lectura -> decodificación -> coordenadas -> QNH -> CSV

Port a Python de las funciones de GeoUtils.cs (código de la asignatura,
carpeta Coordinate-transform) que hacen falta. Se mantienen los nombres del
original para poder compararlos línea a línea. Cada función indica su
apartado de TransLib (SASSC-TRANSLIB-SRD-98-0154, cadena ARTAS):

    Cadena de CAT048 (radar -> WGS84):
        CalculateElevation                       SR5   (elevación a partir de la altura)
        change_radar_spherical2radar_cartesian   SR7
        change_radar_cartesian2geocentric        SR10
        change_geocentric2geodesic               SR17

    Proyección estereográfica (la usará el P3):
        change_geodesic2geocentric               SR18
        setCenterProjection                      (prepara SR14)
        change_geocentric2system_cartesian       SR14
        change_system_cartesian2stereographic    SR15

Diferencias con el original:
    - En C# algunas funciones son estáticas. Aquí todas son métodos normales y
      se llaman a través de una única instancia, GEO_UTILS.
    - GeneralMatrix_v2.cs no se porta: las matrices son listas de Python y solo
      hacen falta dos operaciones (multiplicar matriz por vector y transponer).
    - Los ángulos van en radianes y las distancias en metros, como en el original.

Al final del fichero están los datos del proyecto: posición del radar de
Barcelona y límites del filtro geográfico, los dos dados por el enunciado.
"""

import math


# =============================================================================
# Clases de coordenadas (mismos nombres y atributos que en GeoUtils.cs)
# =============================================================================

class CoordinatesWGS84:
    """Coordenadas geodésicas: Lat y Lon en radianes, Height en metros."""
    def __init__(self, lat=0.0, lon=0.0, height=0.0):
        self.Lat = lat
        self.Lon = lon
        self.Height = height


class CoordinatesXYZ:
    """Coordenadas cartesianas X, Y, Z en metros."""
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.X = x
        self.Y = y
        self.Z = z


class CoordinatesPolar:
    """Coordenadas esféricas del radar: Rho en metros, Theta y Elevation en radianes."""
    def __init__(self, rho=0.0, theta=0.0, elevation=0.0):
        self.Rho = rho
        self.Theta = theta
        self.Elevation = elevation


class CoordinatesUVH:
    """Coordenadas estereográficas: U y V en metros y Height en metros."""
    def __init__(self, u=0.0, v=0.0, height=0.0):
        self.U = u
        self.V = v
        self.Height = height


# =============================================================================
# Operaciones de matrices (sustituyen a GeneralMatrix_v2.cs)
# =============================================================================

def multiplicar_matriz_vector(matriz, vector):
    """Multiplica una matriz 3x3 por un vector de 3 componentes."""
    resultado = [0.0, 0.0, 0.0]
    for fila in range(3):
        suma = 0.0
        for columna in range(3):
            suma = suma + matriz[fila][columna] * vector[columna]
        resultado[fila] = suma
    return resultado


def transponer_matriz(matriz):
    """Devuelve la traspuesta de una matriz 3x3."""
    traspuesta = [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]
    for fila in range(3):
        for columna in range(3):
            traspuesta[columna][fila] = matriz[fila][columna]
    return traspuesta


# =============================================================================
# GeoUtils
# =============================================================================

class GeoUtils:
    """Port de la clase GeoUtils de GeoUtils.cs (solo las funciones necesarias)."""

    # Constantes de GeoUtils.cs (mismos nombres)
    FEET2METERS = 0.3048
    NM2METERS = 1852.0
    DEGS2RADS = math.pi / 180.0
    RADS2DEGS = 180.0 / math.pi
    ALMOST_ZERO = 1e-10
    REQUIERED_PRECISION = 1e-8      # el nombre lleva la errata del original

    def __init__(self):
        """Constructor por defecto de GeoUtils.cs: elipsoide WGS84."""
        self.A = 6378137.0              # semieje mayor (m)
        self.B = 6356752.3142           # semieje menor (m)
        self.E2 = 0.00669437999013      # excentricidad al cuadrado
        self.centerProjection = None    # centro de la proyección estereográfica
        self.T1 = None                  # traslación al centro de proyección
        self.R1 = None                  # rotación al centro de proyección
        self.R_S = 0                    # radio de la Tierra en el centro de proyección
        # Matrices ya calculadas para cada radar (ObtainRotationMatrix y
        # ObtainTranslationMatrix). La clave es el propio objeto del radar, así
        # que hay que usar SIEMPRE el mismo objeto CoordinatesWGS84 para el radar;
        # si se creara uno por mensaje, el diccionario crecería sin parar.
        self.rotationMatrixHT = {}
        self.translationMatrixHT = {}

    # ----- Utilidades ----------------------------------------------------------

    def LatLon2Radians(self, d1, d2, d3, ns):
        """
        GeoUtils.LatLon2Radians: grados, minutos y segundos a radianes.
        ns = 0 para Norte/Este y 1 para Sur/Oeste.
        """
        grados = d1 + (d2 / 60.0) + (d3 / 3600.0)
        if ns == 1:
            grados = -grados
        return grados * GeoUtils.DEGS2RADS

    def CalculateRotationMatrix(self, lat, lon):
        """GeoUtils.CalculateRotationMatrix: matriz de rotación (TransLib, ecuación 7)."""
        return [
            [-math.sin(lon), math.cos(lon), 0.0],
            [-math.sin(lat) * math.cos(lon), -math.sin(lat) * math.sin(lon), math.cos(lat)],
            [math.cos(lat) * math.cos(lon), math.cos(lat) * math.sin(lon), math.sin(lat)],
        ]

    def CalculateTranslationMatrix(self, c, A, E2):
        """GeoUtils.CalculateTranslationMatrix: posición geocéntrica del punto c (TransLib, ecuación 8)."""
        nu = A / math.sqrt(1 - E2 * math.sin(c.Lat) ** 2)
        return [
            (nu + c.Height) * math.cos(c.Lat) * math.cos(c.Lon),
            (nu + c.Height) * math.cos(c.Lat) * math.sin(c.Lon),
            (nu * (1 - E2) + c.Height) * math.sin(c.Lat),
        ]

    def ObtainRotationMatrix(self, radarCoordinates):
        """GeoUtils.ObtainRotationMatrix: calcula la matriz una vez por radar y la reutiliza."""
        if radarCoordinates not in self.rotationMatrixHT:
            matriz = self.CalculateRotationMatrix(radarCoordinates.Lat, radarCoordinates.Lon)
            self.rotationMatrixHT[radarCoordinates] = matriz
        return self.rotationMatrixHT[radarCoordinates]

    def ObtainTranslationMatrix(self, radarCoordinates):
        """GeoUtils.ObtainTranslationMatrix: calcula el vector una vez por radar y lo reutiliza."""
        if radarCoordinates not in self.translationMatrixHT:
            vector = self.CalculateTranslationMatrix(radarCoordinates, self.A, self.E2)
            self.translationMatrixHT[radarCoordinates] = vector
        return self.translationMatrixHT[radarCoordinates]

    # ----- Cadena de CAT048: radar -> WGS84 ----------------------------------

    def CalculateElevation(self, centerCoordinates, R, rho, h):
        """
        GeoUtils.CalculateElevation. TransLib SR5.
        Ángulo de elevación (radianes) de un blanco a distancia rho (m) y altura h (m),
        visto desde un radar a altura centerCoordinates.Height, con radio terrestre R:
            El = asin( (2R(h - hR) + h^2 - hR^2 - rho^2) / (2 rho (R + hR)) )
        """
        if rho < GeoUtils.ALMOST_ZERO or R == -1.0 or centerCoordinates is None:
            return 0.0   # se evita dividir por cero, como en el original
        altura_radar = centerCoordinates.Height
        seno = (2 * R * (h - altura_radar) + h * h - altura_radar * altura_radar - rho * rho) / \
               (2 * rho * (R + altura_radar))
        if -1.0 < seno < 1.0:
            return math.asin(seno)
        return math.pi / 2.0

    def change_radar_spherical2radar_cartesian(self, polarCoordinates):
        """
        GeoUtils.change_radar_spherical2radar_cartesian. TransLib SR7 (ecuación 4).
        X = rho cos(El) sin(Az),  Y = rho cos(El) cos(Az),  Z = rho sin(El)
        X apunta al este, Y al norte y Z hacia arriba, con origen en el radar.
        """
        resultado = CoordinatesXYZ()
        resultado.X = polarCoordinates.Rho * math.cos(polarCoordinates.Elevation) * math.sin(polarCoordinates.Theta)
        resultado.Y = polarCoordinates.Rho * math.cos(polarCoordinates.Elevation) * math.cos(polarCoordinates.Theta)
        resultado.Z = polarCoordinates.Rho * math.sin(polarCoordinates.Elevation)
        return resultado

    def change_radar_cartesian2geocentric(self, radarCoordinates, cartesianCoordinates):
        """
        GeoUtils.change_radar_cartesian2geocentric. TransLib SR10.
        Geocéntricas = (matriz de rotación del radar)^T x cartesianas del radar + posición del radar.
        """
        traslacion = self.ObtainTranslationMatrix(radarCoordinates)
        rotacion = self.ObtainRotationMatrix(radarCoordinates)

        vector = [cartesianCoordinates.X, cartesianCoordinates.Y, cartesianCoordinates.Z]
        girado = multiplicar_matriz_vector(transponer_matriz(rotacion), vector)

        return CoordinatesXYZ(girado[0] + traslacion[0],
                              girado[1] + traslacion[1],
                              girado[2] + traslacion[2])

    def change_geocentric2geodesic(self, c):
        """
        GeoUtils.change_geocentric2geodesic. TransLib SR17.
        De X, Y, Z geocéntricas a latitud y longitud (radianes) y altura (m).
        La latitud se calcula de forma iterativa hasta que cambia menos de
        REQUIERED_PRECISION, con un máximo de 50 vueltas, igual que el original.
        """
        resultado = CoordinatesWGS84()
        b = 6356752.3142    # semieje menor, escrito así en el original

        if abs(c.X) < GeoUtils.ALMOST_ZERO and abs(c.Y) < GeoUtils.ALMOST_ZERO:
            # Punto sobre el eje de los polos
            if abs(c.Z) < GeoUtils.ALMOST_ZERO:
                resultado.Lat = math.pi / 2.0
            else:
                resultado.Lat = (math.pi / 2.0) * ((c.Z / abs(c.Z)) + 0.5)
            resultado.Lon = 0.0
            resultado.Height = abs(c.Z) - b
            return resultado

        d_xy = math.sqrt(c.X * c.X + c.Y * c.Y)
        # Primera aproximación (TransLib, fórmula 20)
        resultado.Lat = math.atan((c.Z / d_xy) /
                                  (1 - (self.A * self.E2) / math.sqrt(d_xy * d_xy + c.Z * c.Z)))
        nu = self.A / math.sqrt(1 - self.E2 * math.sin(resultado.Lat) ** 2)
        resultado.Height = (d_xy / math.cos(resultado.Lat)) - nu

        # Iteración (TransLib, fórmula 20b)
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

    # ----- Proyección estereográfica (P3) --------------------------------------

    def change_geodesic2geocentric(self, c):
        """
        GeoUtils.change_geodesic2geocentric. TransLib SR18.
        De latitud y longitud (radianes) y altura (m) a X, Y, Z geocéntricas.
        """
        nu = self.A / math.sqrt(1 - self.E2 * math.sin(c.Lat) ** 2)
        resultado = CoordinatesXYZ()
        resultado.X = (nu + c.Height) * math.cos(c.Lat) * math.cos(c.Lon)
        resultado.Y = (nu + c.Height) * math.cos(c.Lat) * math.sin(c.Lon)
        resultado.Z = (nu * (1 - self.E2) + c.Height) * math.sin(c.Lat)
        return resultado

    def setCenterProjection(self, c):
        """
        GeoUtils.setCenterProjection. Fija el centro de la proyección estereográfica
        (con altura 0, como en el original) y calcula R_S, T1 y R1.
        """
        centro = CoordinatesWGS84(c.Lat, c.Lon, 0.0)
        self.centerProjection = centro
        # Radio de curvatura en el meridiano (TransLib, ecuación 1)
        self.R_S = (self.A * (1.0 - self.E2)) / (1 - self.E2 * math.sin(centro.Lat) ** 2) ** 1.5
        self.T1 = self.CalculateTranslationMatrix(centro, self.A, self.E2)
        self.R1 = self.CalculateRotationMatrix(centro.Lat, centro.Lon)
        return self.centerProjection

    def change_geocentric2system_cartesian(self, geo):
        """
        GeoUtils.change_geocentric2system_cartesian. TransLib SR14.
        Cartesianas del sistema = R1 x (geocéntricas - T1). Requiere setCenterProjection.
        """
        if self.centerProjection is None:
            return None
        vector = [geo.X - self.T1[0], geo.Y - self.T1[1], geo.Z - self.T1[2]]
        girado = multiplicar_matriz_vector(self.R1, vector)
        return CoordinatesXYZ(girado[0], girado[1], girado[2])

    def change_system_cartesian2stereographic(self, c):
        """
        GeoUtils.change_system_cartesian2stereographic. TransLib SR15.
        De cartesianas del sistema a U, V (plano estereográfico) y altura.
        """
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

# Una sola instancia de GeoUtils para todo el programa (ver la nota del constructor)
GEO_UTILS = GeoUtils()

# Radar de Barcelona (datos del enunciado): 41° 18' 02,5284" N, 02° 06' 07,4095" E.
# Altura = elevación del terreno (2,007 m) + altura de la antena (25,25 m).
ELEVACION_TERRENO_RADAR_M = 2.007
ALTURA_ANTENA_RADAR_M = 25.25
RADAR_BCN = CoordinatesWGS84(GEO_UTILS.LatLon2Radians(41, 18, 2.5284, 0),
                             GEO_UTILS.LatLon2Radians(2, 6, 7.4095, 0),
                             ELEVACION_TERRENO_RADAR_M + ALTURA_ANTENA_RADAR_M)

# Radio terrestre para la elevación (Rt = 6371 km, dato del enunciado)
RADIO_TIERRA_M = 6371000.0

# Filtro geográfico del enunciado: 40,9° N < lat < 41,7° N y 1,5° E < lon < 2,6° E
LATITUD_MINIMA_DEG = 40.9
LATITUD_MAXIMA_DEG = 41.7
LONGITUD_MINIMA_DEG = 1.5
LONGITUD_MAXIMA_DEG = 2.6

def posicion_wgs84_048(rho_nm, theta_deg, altura_m):
    """
    Posición WGS84 de un blanco CAT048 a partir de I048/040 y de su altura.
    Sigue la cadena SR5 -> SR7 -> SR10 -> SR17 con el radar de Barcelona.
    Devuelve (latitud_deg, longitud_deg, altura_m).
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
    """True si el punto está dentro del filtro geográfico del enunciado (límites excluidos)."""
    if not LATITUD_MINIMA_DEG < latitud_deg < LATITUD_MAXIMA_DEG:
        return False
    if not LONGITUD_MINIMA_DEG < longitud_deg < LONGITUD_MAXIMA_DEG:
        return False
    return True
