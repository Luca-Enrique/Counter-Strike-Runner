"""El fondo y el suelo que se desplazan de derecha a izquierda.

El fondo lo usa la pantalla de titulo como muestra de los escenarios, la
eleccion de personaje y la partida, que elige el escenario segun el puntaje.
El suelo es la franja de piso que se dibuja debajo de la linea del suelo.

El escenario se escala para cubrir el lienzo por alto y se dibuja en varias
copias, la segunda espejada, para que el bucle no deje una costura visible.
El suelo se escala al alto de su franja y se repite sin espejo.

Vive aparte, como personaje.py, porque no depende de ninguna escena.
"""
import pygame

import constantes


RUTA_ESCENARIO = "assets/escenario/fondo_{}.png"
RUTA_SUELO = "assets/escenario/suelo.png"

# Las imagenes escaladas y sus espejos se guardan por (nombre, alto). Asi no se
# vuelve a leer ni a escalar un archivo cada vez que una escena cambia de
# escenario, y las pruebas no cargan lo mismo una y otra vez.
_CACHE = {}
_CACHE_ESPEJO = {}
_CACHE_SUELO = {}


def cargar_fondo(nombre, alto):
    """Carga un escenario y lo escala para cubrir el lienzo por alto.

    Devuelve None si el archivo no existe, y la escena queda con el color de
    fondo. El juego arranca aunque falte el asset.
    """
    clave = (nombre, alto)
    if clave in _CACHE:
        return _CACHE[clave]

    try:
        imagen = pygame.image.load(RUTA_ESCENARIO.format(nombre))
    except (pygame.error, FileNotFoundError):
        return None

    ancho = round(imagen.get_width() * alto / imagen.get_height())
    escalada = pygame.transform.smoothscale(imagen, (ancho, alto))
    _CACHE[clave] = escalada
    return escalada


def _cargar_espejo(nombre, alto):
    """La version espejada del escenario, tambien cacheada."""
    clave = (nombre, alto)
    if clave in _CACHE_ESPEJO:
        return _CACHE_ESPEJO[clave]

    imagen = cargar_fondo(nombre, alto)
    if imagen is None:
        return None

    espejo = pygame.transform.flip(imagen, True, False)
    _CACHE_ESPEJO[clave] = espejo
    return espejo


class Fondo:
    """El fondo desplazandose.

    En el titulo y en la eleccion rota de escenario cada ciertos segundos. La
    partida lo crea con rotar=False y le cambia el escenario segun el puntaje.
    """

    def __init__(
        self,
        nombres=None,
        alto=constantes.ALTO,
        rotar=True,
        alfa=constantes.ALFA_OSCURECIDO_FONDO,
    ):
        self.nombres = nombres or constantes.FONDOS
        self.alto = alto
        self.rotar = rotar
        self.alfa = alfa
        self.velocidad = constantes.VELOCIDAD_FONDO
        self.indice = 0
        self.desplazamiento = 0.0
        self.tiempo_en_escenario = 0.0
        self.imagen = cargar_fondo(self.nombres[self.indice], self.alto)
        self.espejo = None
        self._capa = None
        self._capa_alfa = None
        self._preparar_espejo()

    def actualizar(self, delta):
        """Mueve el fondo y, si corresponde, pasa al escenario siguiente."""
        self.desplazamiento += self.velocidad * delta

        if not self.rotar:
            return

        self.tiempo_en_escenario += delta
        while self.tiempo_en_escenario >= constantes.SEGUNDOS_POR_FONDO:
            self.tiempo_en_escenario -= constantes.SEGUNDOS_POR_FONDO
            self._siguiente()

    def cambiar_escenario(self, nombre):
        """Pasa al escenario pedido, si existe y no es el actual.

        Se conserva el desplazamiento para que el cambio no se note como un
        salto en la imagen.
        """
        if nombre not in self.nombres:
            return

        indice = self.nombres.index(nombre)
        if indice == self.indice:
            return

        self.indice = indice
        self.imagen = cargar_fondo(self.nombres[self.indice], self.alto)
        self._preparar_espejo()

    def dibujar(self, superficie):
        """Pinta el escenario y lo oscurece para que lo de encima se lea."""
        if self.imagen is None:
            return

        self._dibujar_copias(superficie)
        self._oscurecer(superficie)

    def _dibujar_copias(self, superficie):
        """Pinta las copias del escenario que entran en la superficie."""
        ancho = self.imagen.get_width()
        # La copia va con un periodo de dos anchos: normal, espejada, normal...
        desplazado = int(self.desplazamiento % (2 * ancho))

        indice = 0
        x = -desplazado
        while x < superficie.get_width():
            copia = self.imagen if indice % 2 == 0 else self.espejo
            superficie.blit(copia, (x, 0))
            indice += 1
            x += ancho

    def _oscurecer(self, superficie):
        """Pinta una capa oscura sobre el fondo, para que el texto se lea."""
        if (
            self._capa is None
            or self._capa.get_size() != superficie.get_size()
            or self._capa_alfa != self.alfa
        ):
            self._capa = pygame.Surface(superficie.get_size(), pygame.SRCALPHA)
            self._capa.fill((*constantes.COLOR_FONDO, self.alfa))
            self._capa_alfa = self.alfa

        superficie.blit(self._capa, (0, 0))

    def _siguiente(self):
        self.indice = (self.indice + 1) % len(self.nombres)
        self.imagen = cargar_fondo(self.nombres[self.indice], self.alto)
        self._preparar_espejo()

    def _preparar_espejo(self):
        """La version espejada de la copia actual, o None si no hay imagen."""
        self.espejo = _cargar_espejo(self.nombres[self.indice], self.alto)


def cargar_suelo(alto):
    """Carga el suelo y lo escala al alto de la franja inferior.

    Devuelve None si el archivo no existe, y la escena usa el color de
    respaldo. El juego arranca aunque falte el asset.
    """
    if alto in _CACHE_SUELO:
        return _CACHE_SUELO[alto]

    try:
        imagen = pygame.image.load(RUTA_SUELO)
    except (pygame.error, FileNotFoundError):
        return None

    ancho = max(1, round(imagen.get_width() * alto / imagen.get_height()))
    escalada = pygame.transform.smoothscale(imagen, (ancho, alto))
    _CACHE_SUELO[alto] = escalada
    return escalada


class Suelo:
    """La franja de piso que se desplaza debajo de la linea del suelo.

    Usa el asset completo escalado al alto de la franja y lo repite en copias
    consecutivas. Los bordes del asset ya coinciden, asi que no hace falta el
    espejo que usa el fondo.
    """

    def __init__(self, alto=constantes.ALTO - constantes.SUELO_Y):
        self.alto = alto
        self.imagen = cargar_suelo(alto)
        self.velocidad = constantes.VELOCIDAD_FONDO
        self.desplazamiento = 0.0

    def actualizar(self, delta):
        """Avanza el piso a la velocidad pedida, en pixeles por segundo."""
        self.desplazamiento += self.velocidad * delta

    def dibujar(self, superficie):
        """Pinta las copias del piso que entran en la superficie."""
        if self.imagen is None:
            superficie.fill(
                constantes.COLOR_SUELO,
                (0, constantes.SUELO_Y, superficie.get_width(), self.alto),
            )
            return

        ancho = self.imagen.get_width()
        desplazado = int(self.desplazamiento % ancho)
        x = -desplazado
        while x < superficie.get_width():
            superficie.blit(self.imagen, (x, constantes.SUELO_Y))
            x += ancho
