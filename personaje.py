"""El personaje del jugador.

Acá vive el rectangulo de fisica y la animacion del personaje, separado de la
escena. La escena le pasa los textos y le dice cuando saltar o agachar; el
personaje no sabe nada de escenas ni de obstaculos.

La idea que ordena todo el archivo: **el rectangulo manda**. El sprite se dibuja
centrado sobre el rectangulo, nunca al reves, asi que el rectangulo que decide
las colisiones es siempre el que se ve en pantalla.
"""
import pygame

import constantes


RUTA_PERSONAJES = "assets/personajes"


# --- Carga de imagenes ---------------------------------------------------

def cargar_textura(ruta, alto_objetivo, ancho_objetivo=None):
    """Carga un sprite, le recorta el margen y lo escala.

    El recorte hace falta porque los sprites vienen sobre un lienco mas grande
    que el dibujo: sin el, el personaje apareceria con un margen invisible que
    haria mal las colisiones.

    La escala preserva la proporcion y se hace por alto, salvo que se pase un
    ancho_objetivo. Eso es lo que necesita el proyectil, que es muy alargado y
    si se escalara por alto saldia gigante.

    Si el archivo no existe, o esta vacio, devuelve None. El juego tiene que
    andar aunque falte un asset.
    """
    try:
        imagen = pygame.image.load(ruta)
    except (pygame.error, FileNotFoundError):
        return None

    caja = imagen.get_bounding_rect()
    if caja.w == 0 or caja.h == 0:
        return None

    if (caja.x, caja.y, caja.w, caja.h) != (0, 0, imagen.get_width(), imagen.get_height()):
        imagen = imagen.subsurface(caja).copy()

    if ancho_objetivo is None:
        escala = alto_objetivo / caja.h
    else:
        escala = ancho_objetivo / caja.w

    # smoothscale y no scale: los sprites de origen son muy grandes y hay que
    # reducirlos mucho, y el filtrado evita que queden bordes irregulares.
    return pygame.transform.smoothscale(
        imagen,
        (
            max(1, round(caja.w * escala)),
            max(1, round(caja.h * escala)),
        ),
    )


def cargar_animacion(rutas, alto_objetivo):
    """Carga los fotogramas de una animacion.

    Devuelve la lista de fotogramas, o None si no se pudo cargar ninguno.
    """
    fotogramas = [cargar_textura(ruta, alto_objetivo) for ruta in rutas]
    fotogramas = [fotograma for fotograma in fotogramas if fotograma is not None]
    return fotogramas or None


def rutas_de_equipo(equipo):
    """Las rutas de los tres estados de animacion de un equipo."""
    carpeta = f"{RUTA_PERSONAJES}/{equipo.lower()}"
    return {
        "correr": [f"{carpeta}/correr_{n}.png" for n in range(constantes.FOTOGRAMAS_CORRER)],
        "saltar": [f"{carpeta}/saltar.png"],
        "agacharse": [f"{carpeta}/agacharse.png"],
    }


def cargar_texturas(equipo="CT"):
    """Carga los sprites de un equipo, con el alto que corresponde a cada estado.

    El estado parado usa ALTO_PERSONAJE y el agachado, ALTO_PERSONAJE_AGACHADO.
    """
    rutas = rutas_de_equipo(equipo)
    return {
        "correr": cargar_animacion(rutas["correr"], constantes.ALTO_PERSONAJE),
        "saltar": cargar_animacion(rutas["saltar"], constantes.ALTO_PERSONAJE),
        "agacharse": cargar_animacion(
            rutas["agacharse"], constantes.ALTO_PERSONAJE_AGACHADO
        ),
    }


# --- El personaje --------------------------------------------------------

class Personaje:
    """El personaje: un rectangulo con fisica y una animacion encima."""

    def __init__(self, texturas=None, x=constantes.JUGADOR_X):
        self.texturas = texturas or {}

        # El ancho es UNO para todos los estados, y sale del fotograma de correr
        # mas ancho. No se puede usar el ancho de cada fotograma por separado:
        # los seis tienen anchos distintos (de 84 a 93 px), asi que el
        # rectangulo engordaria y adelgazaria en cada paso de la animacion y el
        # personaje parpadearia.
        #
        # El agachado tambien usa ese mismo ancho, y no el suyo mas angosto:
        # si la hitbox se achicara al agacharse, pasarian obstaculos que en
        # realidad golpean. Lo que cambia al agacharse es solo el alto.
        self.ancho = self._ancho_de("correr", constantes.ALTO_PERSONAJE)

        self.rect = pygame.Rect(x, 0, self.ancho, constantes.ALTO_PERSONAJE)
        self.rect.bottom = constantes.SUELO_Y

        # posicion_y es la linea de los pies, en coma flotante. El rectangulo
        # se coloca a partir de ella, ya redondeada.
        self.posicion_y = float(constantes.SUELO_Y)

        # Estado del salto en curso. origen_salto es la linea de los pies en el
        # instante del salto, y tiempo_en_el_aire lleva la cuenta.
        self.origen_salto = self.posicion_y
        self.tiempo_en_el_aire = 0.0

        self.en_suelo = True
        self.agachado = False

        self.cuadro_animacion = 0
        self.reloj_animacion = 0.0

    def _ancho_de(self, estado, alto_por_defecto):
        """El ancho que se le da al personaje.

        Es el del fotograma mas ancho del estado, para que todos los fotogramas
        de la animacion entren en el mismo rectangulo.

        Si no hay sprite, se usa la proporcion fija, y por eso las pruebas
        pueden armar un personaje sin ningun archivo.
        """
        anchos = [
            imagen.get_width()
            for imagen in self.texturas.get(estado) or []
            if imagen is not None
        ]
        if anchos:
            return max(anchos)
        return max(1, round(alto_por_defecto * constantes.PROPORCION_PERSONAJE))

    def verificar_texturas(self):
        """Dice si los tres estados tienen los fotogramas que necesitan.

        Se usa desde las pruebas. Que falte un fotograma no rompe el juego (se
        dibuja un rectangulo de color), pero si conviene saberlo.
        """
        faltan = [
            estado
            for estado in ("correr", "saltar", "agacharse")
            if not self.texturas.get(estado)
        ]
        return not faltan, faltan

    # --- Acciones

    def saltar(self):
        """Salta con altura fija. No hace nada si ya esta en el aire.

        La altura no depende de cuanto se mantenga apretada la tecla: sale de la
        velocidad de salto y de la gravedad, que estan fijadas en
        constantes.py. Apretar en el aire no repite el salto.
        """
        if not self.en_suelo:
            return
        self.en_suelo = False
        self.agachado = False
        self.origen_salto = self.posicion_y
        self.tiempo_en_el_aire = 0.0
        self._cambiar_tamano()

    def agachar(self, agachado):
        """Se agacha o se levanta.

        Solo tiene efecto en el suelo: en el aire no hay agachado. Cuando salta
        desde el agachado, el personaje se levanta solo.
        """
        if agachado and not self.en_suelo:
            return
        if self.agachado == agachado:
            return
        self.agachado = agachado
        self._cambiar_tamano()

    def _cambiar_tamano(self):
        """Ajusta el rectangulo al estado, sin despegarlo del suelo.

        El agachado y el salto solo cambian el estado en el suelo, asi que se
        puede anclar la linea de los pies: no se levantan al agacharse ni al
        saltar.
        """
        if self.agachado:
            self.rect.height = constantes.ALTO_PERSONAJE_AGACHADO
        else:
            self.rect.height = constantes.ALTO_PERSONAJE

        # El ancho no se toca: la hitbox es la misma en los dos estados.
        self.rect.bottom = round(self.posicion_y)

    # --- Bucle

    def actualizar(self, delta):
        self.actualizar_fisica(delta)
        self.actualizar_animacion(delta)

    def actualizar_fisica(self, delta):
        """Avanza la caida y se apoya en el suelo si lo toca.

        En el suelo no hay nada que calcular: el personaje ya esta apoyado y se
        queda. Si se dejara acumular velocidad hacia abajo, se hundiria poco a
        poco en el terreno.
        """
        if not self.en_suelo:
            self.tiempo_en_el_aire += delta
            self.posicion_y = self.posicion_en_el_salto(self.tiempo_en_el_aire)

            if self.posicion_y >= constantes.SUELO_Y:
                self.posicion_y = float(constantes.SUELO_Y)
                self.tiempo_en_el_aire = 0.0
                self.en_suelo = True

        self.rect.bottom = round(self.posicion_y)

    def posicion_en_el_salto(self, tiempo):
        """La linea de los pies a `tiempo` segundos de haber saltado.

        Es la solucion exacta de la caida libre:

            y(t) = y0 + v0 * t + (g / 2) * t^2

        donde la gravedad va positiva hacia abajo, asi que v0 sale negativo
        (-900) y el termino de la gravedad frena el ascenso y luego lo acelera
        hacia el suelo.

        Se usa la formula en vez de ir sumando velocidad fotograma a fotograma
        porque asi el punto mas alto cae SIEMPRE en la misma altura, la que dice
        la formula de docs/ESPECIFICACION.md. Integrando a mano el punto mas
        alto queda 7.75 px mas bajo a 60 por segundo, y 16 px mas bajo a 30:
        la altura del salto terminaria dependiendo de la maquina.
        """
        return (
            self.origen_salto
            + constantes.VELOCIDAD_SALTO * tiempo
            + (constantes.GRAVEDAD / 2) * tiempo * tiempo
        )

    def actualizar_animacion(self, delta):
        """Avanza el ciclo de correr.

        Solo avanza en el suelo: en el aire se dibuja el fotograma de salto, y
        en el agachado el suyo.
        """
        fotogramas = self.texturas.get("correr") or []
        if not self.en_suelo or len(fotogramas) < 2:
            return

        self.reloj_animacion += delta
        paso = 1.0 / constantes.FOTOGRAMAS_ANIMACION_POR_SEGUNDO

        while self.reloj_animacion >= paso:
            self.reloj_animacion -= paso
            self.cuadro_animacion = (self.cuadro_animacion + 1) % len(fotogramas)

    def fotograma_actual(self):
        """El estado que le toca por como esta el personaje."""
        if self.agachado:
            return "agacharse"
        if not self.en_suelo:
            return "saltar"
        return "correr"

    def dibujar(self, superficie):
        """Pinta el personaje.

        Si no hay sprite para el estado actual, pinta un rectangulo de color
        con las mismas dimensiones. El juego no se rompe nunca por un asset
        faltante.
        """
        estado = self.fotograma_actual()
        fotogramas = self.texturas.get(estado) or []

        if fotogramas:
            imagen = fotogramas[self.cuadro_animacion % len(fotogramas)]
        else:
            superficie.fill(constantes.COLOR_PERSONAJE_SIN_SPRITE, self.rect)
            return

        # La imagen va centrada sobre el rectangulo: el rectangulo manda
        # porque es el que decide las colisiones.
        posicion = imagen.get_rect(center=self.rect.center)
        superficie.blit(imagen, posicion)