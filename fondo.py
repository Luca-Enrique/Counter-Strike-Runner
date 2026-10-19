"""El fondo que se desplaza de derecha a izquierda.

Lo usa la pantalla de titulo como muestra de los escenarios, y queda armado
para que la partida lo use cuando tenga escenarios por zona.

El escenario se escala para cubrir el lienzo por alto y se dibuja en varias
copias, la segunda espejada, para que el bucle no deje una costura visible.

Vive aparte, como personaje.py, porque no depende de ninguna escena.
"""
import pygame

import constantes


RUTA_ESCENARIO = "assets/escenario/fondo_{}.png"


def cargar_fondo(nombre, alto):
    """Carga un escenario y lo escala para cubrir el lienzo por alto.

    Devuelve None si el archivo no existe, y la escena queda con el color de
    fondo. El juego arranca aunque falte el asset.
    """
    try:
        imagen = pygame.image.load(RUTA_ESCENARIO.format(nombre))
    except (pygame.error, FileNotFoundError):
        return None

    ancho = round(imagen.get_width() * alto / imagen.get_height())
    return pygame.transform.smoothscale(imagen, (ancho, alto))


class Fondo:
    """El fondo desplazandose. Rota de escenario cada ciertos segundos."""

    def __init__(self, nombres=None, alto=constantes.ALTO):
        self.nombres = nombres or constantes.FONDOS
        self.alto = alto
        self.indice = 0
        self.desplazamiento = 0.0
        self.tiempo_en_escenario = 0.0
        self.imagen = cargar_fondo(self.nombres[self.indice], self.alto)
        self.espejo = None
        self._capa = None
        self._preparar_espejo()

    def actualizar(self, delta):
        """Mueve el fondo y, pasado el tiempo, pasa al escenario siguiente."""
        self.desplazamiento += constantes.VELOCIDAD_FONDO * delta

        self.tiempo_en_escenario += delta
        while self.tiempo_en_escenario >= constantes.SEGUNDOS_POR_FONDO:
            self.tiempo_en_escenario -= constantes.SEGUNDOS_POR_FONDO
            self._siguiente()

    def dibujar(self, superficie):
        """Pinta el escenario y lo oscurece para que el texto de encima se lea."""
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
        if self._capa is None or self._capa.get_size() != superficie.get_size():
            self._capa = pygame.Surface(superficie.get_size(), pygame.SRCALPHA)
            self._capa.fill(
                (*constantes.COLOR_FONDO, constantes.ALFA_OSCURECIDO_FONDO)
            )
        superficie.blit(self._capa, (0, 0))

    def _siguiente(self):
        self.indice = (self.indice + 1) % len(self.nombres)
        self.imagen = cargar_fondo(self.nombres[self.indice], self.alto)
        self._preparar_espejo()

    def _preparar_espejo(self):
        """La version espejada de la copia actual, o None si no hay imagen."""
        if self.imagen is None:
            self.espejo = None
        else:
            self.espejo = pygame.transform.flip(self.imagen, True, False)
