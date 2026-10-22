"""El personaje del jugador.

Acá vive el rectangulo de fisica y el dibujo del personaje, separado de la
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

def _caja_visible(imagen, umbral_alfa=127, area_minima=8):
    """La caja del dibujo, sin los pixeles sueltos que ensucian el lienzo.

    get_bounding_rect() toma cualquier pixel con algo de alfa. Unos pocos
    pixeles perdidos lejos del sprite estiran la caja y dejan el dibujo
    descentrado respecto de la hitbox. Se usan las componentes conexas de la
    mascara y se descartan las que ocupan menos de area_minima pixeles.
    """
    mascara = pygame.mask.from_surface(imagen, umbral_alfa)
    cajas = [
        rect
        for rect in mascara.get_bounding_rects()
        if rect.w * rect.h >= area_minima
    ]
    if not cajas:
        return imagen.get_bounding_rect()

    caja = cajas[0].copy()
    for otra in cajas[1:]:
        caja.union_ip(otra)
    return caja


def cargar_textura_original(ruta, recorte_robusto=False):
    """Carga un sprite y le recorta el margen, sin escalarlo todavia.

    El recorte hace falta porque los sprites vienen sobre un lienco mas grande
    que el dibujo: sin el, la imagen apareceria con un margen invisible.

    Con recorte_robusto se ignoran los pixeles sueltos del lienzo (ver
    _caja_visible). Lo usan los obstaculos, que pueden traer basura lejos del
    dibujo y necesitan que la hitbox coincida con lo que se ve.

    Sirve para las imagenes que se dibujan sueltas, que se van a escalar segun
    el alto de la pantalla.

    Si el archivo no existe, o esta vacio, devuelve None.
    """
    try:
        imagen = pygame.image.load(ruta)
    except (pygame.error, FileNotFoundError):
        return None

    caja = _caja_visible(imagen) if recorte_robusto else imagen.get_bounding_rect()
    if caja.w == 0 or caja.h == 0:
        return None

    if (caja.x, caja.y, caja.w, caja.h) != (0, 0, imagen.get_width(), imagen.get_height()):
        imagen = imagen.subsurface(caja).copy()

    return imagen


def cargar_textura(ruta, alto_objetivo, ancho_objetivo=None, recorte_robusto=False):
    """Carga un sprite, le recorta el margen y lo escala.

    El recorte hace falta porque los sprites vienen sobre un lienco mas grande
    que el dibujo: sin el, el personaje apareceria con un margen invisible que
    haria mal las colisiones. recorte_robusto se pasa a cargar_textura_original.

    La escala preserva la proporcion y se hace por alto, salvo que se pase un
    ancho_objetivo. Eso es lo que necesita el proyectil, que es muy alargado y
    si se escalara por alto saldia gigante.

    Si el archivo no existe, o esta vacio, devuelve None. El juego tiene que
    andar aunque falte un asset.
    """
    imagen = cargar_textura_original(ruta, recorte_robusto)
    if imagen is None:
        return None

    return _escalar(imagen, alto_objetivo, ancho_objetivo)


def _escalar(imagen, alto_objetivo, ancho_objetivo=None):
    """Escala la imagen al alto pedido, o al ancho si se pasa un ancho.

    La proporcion se conserva, salvo que el ancho pedido sea MENOR que el que
    sale de la proporcion: en ese caso hay que encoger, porque un dibujo que se
    sale de la hitbox golpearia cosas que no se ven. Ahi se estira hasta el
    ancho pedido y el alto queda al que de.
    """
    escala = (alto_objetivo / imagen.get_height() if ancho_objetivo is None
              else ancho_objetivo / imagen.get_width())

    ancho = max(1, round(imagen.get_width() * escala))
    alto = max(1, round(imagen.get_height() * escala))

    # smoothscale y no scale: los sprites de origen son muy grandes y hay que
    # reducirlos mucho, y el filtrado evita que queden bordes irregulares.
    return pygame.transform.smoothscale(imagen, (ancho, alto))

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
    """Carga los sprites de un estado.

    Devuelve la lista de fotogramas, o None si no se pudo cargar ninguno.
    """
    fotogramas = [cargar_textura(ruta, alto_objetivo) for ruta in rutas]
    fotogramas = [fotograma for fotograma in fotogramas if fotograma is not None]
    return fotogramas or None


def rutas_de_equipo(equipo):
    """Las rutas de los tres estados de un equipo."""
    carpeta = f"{RUTA_PERSONAJES}/{equipo.lower()}"
    return {
        "correr": [f"{carpeta}/correr_{n}.png" for n in range(constantes.FOTOGRAMAS_CORRER)],
        "saltar": [f"{carpeta}/saltar.png"],
        "agacharse": [f"{carpeta}/agacharse.png"],
    }


def cargar_texturas(equipo="CT"):
    """Carga los sprites de un equipo, con el alto que corresponde a cada estado.

    Correr y saltar usan ALTO_PERSONAJE. El agachado tambien se carga a ese
    alto: despues recortar_agachado le saca las piernas y lo deja en
    ALTO_PERSONAJE_AGACHADO, conservando la cabeza del mismo tamano.
    """
    rutas = rutas_de_equipo(equipo)
    return {
        "correr": cargar_animacion(rutas["correr"], constantes.ALTO_PERSONAJE),
        "saltar": cargar_animacion(rutas["saltar"], constantes.ALTO_PERSONAJE),
        "agacharse": cargar_animacion(rutas["agacharse"], constantes.ALTO_PERSONAJE),
    }


def recortar_agachado(texturas):
    """Recorta el sprite de agachar para que entre en la hitbox.

    El sprite de agachar se carga al mismo alto que correr (ALTO_PERSONAJE)
    para que la cabeza quede del mismo tamano. Despues se le recorta el torso:
    se muestran los primeros ALTO_PERSONAJE_AGACHADO pixeles y se ocultan las
    piernas. Sin el recorte, el sprite completo se saldria de la hitbox
    agachada.

    El corte se hace sobre el sprite de agachar, no sobre el de correr: lo que
    se ve agachado es la pose de agacharse. El alto del recorte es el mismo que
    el de la hitbox, asi que lo que se ve y lo que colisiona miden igual.
    """
    if not texturas.get("agacharse"):
        return texturas

    torso = _recortar_torso(texturas["agacharse"][0])
    if torso is None:
        return texturas

    # El torso reemplaza al sprite de agachar. Se repite por cada fotograma
    # para no romper la interfaz, que siempre espera una lista.
    texturas["agacharse"] = [torso for _ in texturas["agacharse"]]
    return texturas


def _recortar_torso(imagen):
    """La parte de arriba de la imagen, hasta ALTO_PERSONAJE_AGACHADO de alto.

    El corte es por filas: se queda con las primeras. En un sprite de persona,
    la cabeza esta arriba, asi que esto se lleva las piernas.

    Despues del corte se recorta el margen transparente que queda, para que el
    torso visible quede centrado y no ocupe mas ancho del que de verdad usa. No
    se reescala nada: la cabeza conserva el tamano que traia.
    """
    ancho, alto = imagen.get_size()
    alto_recorte = min(constantes.ALTO_PERSONAJE_AGACHADO, alto)

    corte = imagen.subsurface((0, 0, ancho, alto_recorte)).copy()

    caja = corte.get_bounding_rect()
    if caja.w == 0 or caja.h == 0:
        return corte

    return corte.subsurface(caja).copy()


# --- El personaje --------------------------------------------------------

class Personaje:
    """El personaje: un rectangulo con fisica y un sprite encima."""

    def __init__(self, texturas=None, x=constantes.JUGADOR_X):
        self.texturas = texturas or {}

        # El ancho es UNO para todos los estados, y sale del sprite de correr.
        # No se usa el ancho del sprite que se dibuja en cada momento: el
        # rectangulo manda sobre el dibujo, no al reves.
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
        self.velocidad_inicial = constantes.VELOCIDAD_SALTO
        self.tiempo_en_el_aire = 0.0

        self.en_suelo = True
        self.agachado = False
        self.caida_rapida = False

    def _ancho_de(self, estado, alto_por_defecto):
        """El ancho que se le da al personaje.

        Es el del sprite de correr, para que la hitbox no dependa del estado que
        se esta dibujando.

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
        self.velocidad_inicial = constantes.VELOCIDAD_SALTO
        self.tiempo_en_el_aire = 0.0
        self.caida_rapida = False
        self._cambiar_tamano()

    def agachar(self, agachado):
        """Se agacha, se levanta, o cae mas rapido si esta en el aire.

        En el suelo es el agachado de verdad: el rectangulo baja de 96 a 56 px.

        En el aire no hay agachado, pero el mismo control sirve para la CAIDA
        RAPIDA: el personaje baja mas rapido y llega antes al suelo. Agachar en
        el aire tambien acorta el resto de la subida.
        """
        if not self.en_suelo:
            self._caer_mas_rapido(agachado)
            return

        if self.agachado == agachado:
            return
        self.agachado = agachado
        self._cambiar_tamano()

    def _caer_mas_rapido(self, agachado):
        """Enciende o apaga la caida rapida, sin romper el salto en curso.

        Cambiar la gravedad a mitad de vuelo partira la solucion cerrada en dos.
        Para no perder la posicion ni la velocidad, se mide donde esta el
        personaje justo antes del cambio y se reinicia la parabola desde ahi.
        """
        if self.caida_rapida == agachado:
            return

        # Donde esta y hacia donde va ahora mismo.
        posicion_actual = self.posicion_en_el_salto(self.tiempo_en_el_aire)
        velocidad_actual = self.velocidad_en_el_salto(self.tiempo_en_el_aire)

        self.origen_salto = posicion_actual
        self.velocidad_inicial = velocidad_actual
        self.tiempo_en_el_aire = 0.0
        self.caida_rapida = agachado

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
            + self.velocidad_inicial * tiempo
            + (self.gravedad_actual() / 2) * tiempo * tiempo
        )

    def velocidad_en_el_salto(self, tiempo):
        """La velocidad vertical a `tiempo` segundos de haber saltado.

        Sale de derivar la posicion: es la pendiente de la parabola. Se usa para
        reiniciar el vuelo cuando cambia la gravedad en el aire, para que el
        cambio no de un tirón.
        """
        return self.velocidad_inicial + self.gravedad_actual() * tiempo

    def gravedad_actual(self):
        """La gravedad que se está usando ahora: la normal, o la de la caida rapida."""
        if self.caida_rapida:
            return constantes.GRAVEDAD * constantes.GRAVEDAD_CAIDA_RAPIDA
        return constantes.GRAVEDAD

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
            imagen = fotogramas[0]
        else:
            superficie.fill(constantes.COLOR_PERSONAJE_SIN_SPRITE, self.rect)
            return

        # La imagen va centrada sobre el rectangulo: el rectangulo manda
        # porque es el que decide las colisiones.
        posicion = imagen.get_rect(center=self.rect.center)
        superficie.blit(imagen, posicion)