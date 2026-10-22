"""Los obstaculos que el jugador tiene que esquivar.

Vive aparte, como personaje.py: sabe moverse y dibujarse, pero no sabe nada de
escenas ni de puntaje. La escena decide cuando aparece cada uno y con que
velocidad avanza.

El rectangulo manda, igual que en el personaje: el dibujo se centra sobre el
rectangulo que decide la colision, nunca al reves.
"""
import pygame

import constantes
import personaje


RUTA_OBSTACULO = "assets/obstaculos/{}.png"
RUTA_PERSONA = "assets/obstaculos/persona_{}.png"

# Los tipos que pueden aparecer. La escena elige uno al azar.
TIPOS = ("caja", "barril", "barricada", "c4", "persona", "proyectil")

# Alto con el que se dibuja cada tipo. El proyectil es la excepcion y tiene su
# propio par de constantes porque se escala por largo.
ALTOS = {
    "caja": constantes.ALTO_OBSTACULO_CAJA,
    "barril": constantes.ALTO_OBSTACULO_BARRIL,
    "barricada": constantes.ALTO_OBSTACULO_BARRICADA,
    "c4": constantes.ALTO_OBSTACULO_C4,
    "persona": constantes.ALTO_OBSTACULO_PERSONA,
}

# Los que vuelan a la altura de la cabeza: hay que agacharse para pasar.
AEREOS = ("proyectil",)

# Ancho de reserva cuando falta la imagen, para que el rectangulo de respaldo
# no quede desproporcionado.
PROPORCION_SIN_SPRITE = 0.8

# Los sprites escalados se guardan por (tipo, equipo). Sin esto, cada aparicion
# volveria a leer y escalar un PNG de mas de un megabyte, y el juego tendria
# tirones cada pocos segundos.
_CACHE = {}


def rival_de(equipo):
    """El equipo contrario al elegido, que es el que aparece como obstaculo."""
    return "T" if equipo == "CT" else "CT"


def ruta_de(tipo, equipo="CT"):
    """La ruta del sprite de un tipo.

    La persona es del equipo rival: si el jugador eligio CT, aparece un T.
    """
    if tipo == "persona":
        return RUTA_PERSONA.format(rival_de(equipo).lower())
    return RUTA_OBSTACULO.format(tipo)


def cargar_obstaculo(tipo, equipo="CT"):
    """Carga el sprite de un tipo, escalado a su tamano de juego.

    Devuelve None si falta el archivo, y la escena lo dibuja como un
    rectangulo del color de respaldo.
    """
    clave = (tipo, equipo)
    if clave in _CACHE:
        return _CACHE[clave]

    ruta = ruta_de(tipo, equipo)
    if tipo == "proyectil":
        imagen = personaje.cargar_textura(
            ruta,
            constantes.ALTO_PROYECTIL,
            constantes.LARGO_PROYECTIL,
            recorte_robusto=True,
        )
    else:
        imagen = personaje.cargar_textura(
            ruta, ALTOS[tipo], recorte_robusto=True
        )

    _CACHE[clave] = imagen
    return imagen


def alto_sin_sprite(tipo):
    """El alto del rectangulo de respaldo cuando falta la imagen."""
    if tipo == "proyectil":
        return constantes.ALTO_PROYECTIL
    return ALTOS[tipo]


def ancho_sin_sprite(tipo):
    """El ancho del rectangulo de respaldo cuando falta la imagen."""
    if tipo == "proyectil":
        return constantes.LARGO_PROYECTIL
    return max(1, round(ALTOS[tipo] * PROPORCION_SIN_SPRITE))


class Obstaculo:
    """Un obstaculo que avanza de derecha a izquierda."""

    def __init__(self, tipo, equipo="CT", x=constantes.ANCHO):
        self.tipo = tipo
        self.equipo = equipo
        self.imagen = cargar_obstaculo(tipo, equipo)
        self.x = float(x)

        if self.imagen is not None:
            ancho, alto = self.imagen.get_size()
        else:
            ancho = ancho_sin_sprite(tipo)
            alto = alto_sin_sprite(tipo)

        self.rect = pygame.Rect(0, 0, ancho, alto)
        self.rect.left = round(self.x)

        if tipo in AEREOS:
            # Apoyado justo arriba de la cabeza agachada: de pie golpea y
            # agachado pasa. El pixel de margen evita que el redondeo los
            # haga tocarse.
            self.rect.bottom = (
                constantes.SUELO_Y - constantes.ALTO_PERSONAJE_AGACHADO - 1
            )
        else:
            self.rect.bottom = constantes.SUELO_Y

        # Para contar cada persona una sola vez aunque tarde varios fotogramas
        # en terminar de pasar al jugador.
        self.contada = False

    def actualizar(self, delta, velocidad):
        """Avanza a la izquierda a la velocidad dada, en pixeles por segundo."""
        self.x -= velocidad * delta
        self.rect.left = round(self.x)

    def dibujar(self, superficie):
        if self.imagen is None:
            superficie.fill(constantes.COLOR_OBSTACULO_SIN_SPRITE, self.rect)
            return

        superficie.blit(self.imagen, self.imagen.get_rect(center=self.rect.center))

    def fuera_de_pantalla(self):
        """True cuando ya salio por la izquierda y se puede descartar."""
        return self.rect.right < 0

    def paso_al_jugador(self, x_jugador):
        """True si ya quedo a la izquierda del jugador."""
        return self.rect.right < x_jugador

    def colisiona(self, rect):
        """True si el obstaculo se superpone con el rectangulo dado."""
        return self.rect.colliderect(rect)
