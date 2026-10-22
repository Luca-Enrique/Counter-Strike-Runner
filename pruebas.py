"""Verificaciones automaticas del motor y del personaje.

Las primeras comprobaban funciones puras de juego.py. Ahora ademas arman
personajes de verdad y los hacen correr fotograma a fotograma.

No abren ninguna ventana: el controlador de video de SDL se pone en modo
"dummy" al arrancar, asi que las pruebas corren tambien en una maquina sin
pantalla.

Se ejecuta con:

    python pruebas.py

Devuelve 0 si todo pasa y 1 si algo falla.
"""
import os
import tempfile
from pathlib import Path

# Tiene que estar antes de importar juego, para que las pruebas corran tambien
# en una maquina sin pantalla (un servidor de integracion continua, por
# ejemplo). setdefault no pisa la variable si ya estaba puesta.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

import constantes
import fondo
import generar_ranking
import juego
import obstaculo
import personaje
import ranking


# Ventanas raras, para comprobar que la imagen entra siempre entera.
TAMANOS_DE_VENTANA = [
    (1920, 1080),
    (1280, 720),
    (1024, 768),
    (800, 600),
    (2560, 1080),
    (500, 900),
    (200, 150),
    (1, 1),
]


def casi_igual(valor, esperado, tolerancia=0.001):
    """Compara dos flotantes sin exigir que sean identicos bit a bit."""
    return abs(valor - esperado) <= tolerancia


def imagen_entra(ancho_ventana, alto_ventana):
    """Dice si la imagen entra completa y centrada en esa ventana.

    Se usa el mismo calcular_destino que el juego, para que la prueba mida la
    geometria que de verdad se dibuja y no un recalculo aparte.
    """
    x, y, ancho, alto = juego.calcular_destino(ancho_ventana, alto_ventana)
    return (x >= 0 and y >= 0
            and x + ancho <= ancho_ventana
            and y + alto <= alto_ventana)


# --- Ayudantes para el personaje -----------------------------------------
DELTA = 1.0 / constantes.FPS

# Con que equipo se prueba la escena de partida. Los controles no dependen del
# equipo, asi que alcanza con uno solo.
EQUIPO_DE_PRUEBA = "CT"


def personaje_en_suelo():
    """Un personaje recien creado, apoyado y sin sprites."""
    return personaje.Personaje()

def juego_stub(tamano_ventana=None):
    """Un Juego stub: solo lo que necesitan las escenas para probarse.

    No abre ventana. Las escenas solo necesitan las fuentes, los retratos, el
    tamano de la ventana para mapear el raton y un sitio donde anotar el cambio
    de escena. Los eventos se escriben a mano.
    """

    class JuegoStub:
        fuentes = juego.cargar_fuentes()
        lienzo = juego.Lienzo()

        def __init__(self):
            self.cambio_de_escena = None
            self.ultimo_puntaje = 0
            self.ultimas_personas = 0
            self.equipo = "CT"
            self.retratos_equipo = {}
            self.ruta_ranking = ranking.RUTA_RANKING
            self.ruta_ranking_html = ranking.RUTA_RANKING.with_name("ranking.html")
            self.navegador_abierto = None
            self.abrir_navegador = self._anotar_apertura
            self.ventana = VentanaDePrueba(
                tamano_ventana or (constantes.ANCHO, constantes.ALTO)
            )

        def _anotar_apertura(self, url):
            self.navegador_abierto = url

        def abrir_ranking(self):
            try:
                self.abrir_navegador(self.ruta_ranking_html.resolve().as_uri())
            except OSError:
                pass

        def cambiar_escena(self, nombre):
            self.cambio_de_escena = nombre

        def salir(self):
            pass

    return JuegoStub()


class VentanaDePrueba:
    """Una ventana falsa: solo el tamano, para probar el mapeo del raton."""

    def __init__(self, tamano):
        self._tamano = tamano

    def get_size(self):
        return self._tamano


def escena_de_juego():
    """Una EscenaJuego con el equipo pedido."""
    stub = juego_stub()
    stub.equipo = EQUIPO_DE_PRUEBA
    escena = juego.EscenaJuego(stub)
    escena.inicializar()
    return escena


def escena_de_equipo(tamano_ventana=None):
    """Una EscenaEquipo con el juego stub."""
    escena = juego.EscenaEquipo(juego_stub(tamano_ventana))
    escena.inicializar()
    return escena


def tecla(tipo, key):
    return pygame.event.Event(tipo, key=key)


def boton(tipo, numero, posicion=None):
    return pygame.event.Event(tipo, button=numero, pos=posicion or (0, 0))


def movimiento(x, y=0):
    """Un movimiento del raton a esa posicion."""
    return pygame.event.Event(pygame.MOUSEMOTION, pos=(x, y))


def click_equipo(equipo):
    """Un click en la mitad de la pantalla donde esta ese equipo."""
    x = constantes.ANCHO // 4 if equipo == "CT" else constantes.ANCHO * 3 // 4
    return boton(pygame.MOUSEBUTTONDOWN, constantes.BOTON_IZQUIERDO, (x, constantes.ALTO // 2))


def altura_agachado(encender_en=None, fps=constantes.FPS):
    """El alto del rectangulo despues de correr, agachando si se pide."""
    delta = 1.0 / fps
    pers = personaje_en_suelo()
    if encender_en is not None:
        pers.agachar(True)
    for _ in range(int(1.0 / delta)):
        pers.actualizar(delta)
    return pers.rect.height


def apex_con_caida_rapida(tiempo_encendido, delta=DELTA):
    """Cuanto sube el personaje si la caida rapida se enciende a cierto instante.

    Devuelve tambien la posicion en el instante del encendido, para comprobar
    que el cambio no mueve al personaje de golpe.
    """
    pers = _saltar()
    encendida_en = None
    mas_alto = pers.posicion_y

    transcurrido = 0.0
    while transcurrido < 2.0:
        if encendida_en is None and transcurrido >= tiempo_encendido:
            encendida_en = pers.posicion_y
            pers.agachar(True)
        pers.actualizar(delta)
        mas_alto = min(mas_alto, pers.posicion_y)
        transcurrido += delta

    return constantes.SUELO_Y - mas_alto, encendida_en


def correr(pers, fotogramas, delta=DELTA):
    """Avanza el personaje y devuelve la linea de los pies mas baja que tubo."""
    mas_baja = pers.posicion_y
    for _ in range(fotogramas):
        pers.actualizar(delta)
        mas_baja = min(mas_baja, pers.posicion_y)
    return mas_baja


def altura_del_salto(delta=DELTA):
    """Cuanto sube el personaje en un salto completo."""
    pers = _saltar()
    return constantes.SUELO_Y - correr(pers, int(2 / delta), delta)


def _saltar():
    """Un personaje que acaba de saltar."""
    pers = personaje_en_suelo()
    pers.saltar()
    return pers


def _duracion_del_salto(delta=DELTA):
    """Cuantos segundos tarda el personaje en volver al suelo."""
    pers = _saltar()
    transcurrido = 0.0
    while pers.en_suelo is False and transcurrido < 5:
        pers.actualizar(delta)
        transcurrido += delta
    return transcurrido


def _agachado(agachado):
    """Un personaje en el estado pedido."""
    pers = personaje_en_suelo()
    pers.agachar(agachado)
    return pers


def _alto_de(pers):
    return pers.rect.height


def _arranca_apoyado():
    pers = personaje_en_suelo()
    return (pers.en_suelo
            and pers.tiempo_en_el_aire == 0.0
            and pers.rect.bottom == constantes.SUELO_Y)


def _sin_doble_salto():
    """El segundo salto, en el aire, tiene que ignorarse."""
    simple = _saltar()
    doble = _saltar()
    doble.saltar()
    return trayectorias_identicas(simple, doble)


def _pies_no_se_mueven():
    """Agacharse y levantarse no levanta ni baja los pies."""
    return (_agachado(True).rect.bottom
            == _agachado(False).rect.bottom
            == constantes.SUELO_Y)


def _agachar_en_el_aire_no_hace_nada():
    """El agachado no aplica en el aire."""
    pers = _saltar()
    pers.actualizar(DELTA)
    pers.agachar(True)
    return (not pers.agachado
            and pers.rect.height == constantes.ALTO_PERSONAJE)


def _altura_tras_agacharse():
    """El alto del personaje que estaba agachado al saltar."""
    pers = _agachado(True)
    pers.saltar()
    return pers.rect.height


def altura_desde_agachado(delta=DELTA):
    """Cuanto sube un personaje que estaba agachado."""
    pers = _agachado(True)
    pers.saltar()
    return constantes.SUELO_Y - correr(pers, int(2 / delta), delta)


# --- Los controles

def _salta_con(evento):
    """El evento hace saltar al personaje."""
    escena = escena_de_juego()
    escena.manejar_eventos(evento)
    return not escena.personaje.en_suelo


def _agacha_con(al_agachar, agachado, al_soltar=None):
    """El primer evento agacha, y el segundo lo levanta si viene."""
    escena = escena_de_juego()
    escena.manejar_eventos(al_agachar)
    if al_soltar is not None:
        escena.manejar_eventos(al_soltar)
    return escena.personaje.agachado == agachado


def _dos_agachadores_no_se_pisan():
    """Con los dos agachadores apretados, soltar uno tiene que dejar al otro.

    Este es el caso que un if/elif directo romperia.
    """
    escena = escena_de_juego()
    escena.manejar_eventos(tecla(pygame.KEYDOWN, pygame.K_DOWN))
    escena.manejar_eventos(
        boton(pygame.MOUSEBUTTONDOWN, constantes.BOTON_DERECHO)
    )

    escena.manejar_eventos(tecla(pygame.KEYUP, pygame.K_DOWN))
    if not escena.personaje.agachado:
        return False   # todavia esta apretado el click: deberia seguir agachado

    escena.manejar_eventos(
        boton(pygame.MOUSEBUTTONUP, constantes.BOTON_DERECHO)
    )
    return not escena.personaje.agachado


def _agachar_en_el_aire_no_agacha():
    """El sprite de agachar es solo del suelo: en el aire va el de salto."""
    pers = _saltar()
    pers.actualizar(DELTA)
    pers.agachar(True)
    return (not pers.agachado
            and pers.rect.height == constantes.ALTO_PERSONAJE
            and pers.fotograma_actual() == "saltar")


def _vuelve_antes_si_cae_rapido():
    """Con la caida rapida, el personaje vuelve al suelo antes."""
    def volver(rapido):
        pers = _saltar()
        if rapido:
            pers.agachar(True)
        transcurrido = 0.0
        while not pers.en_suelo and transcurrido < 3:
            pers.actualizar(DELTA)
            transcurrido += DELTA
        return transcurrido

    return volver(True) < volver(False)


def _caida_rapida_es_continua():
    """Encender la caida rapida no puede dar un salto de posicion.

    Si se encendiera despues de reiniciar la parabola sin medir donde esta el
    personaje, este se moveria de golpe.
    """
    for instante in (0.02, 0.10, 0.25, 0.40, 0.55):
        pers = _saltar()
        transcurrido = 0.0
        while transcurrido < instante:
            pers.actualizar(DELTA)
            transcurrido += DELTA

        antes = pers.posicion_y
        pers.agachar(True)
        if antes != pers.posicion_y:
            return False
    return True


# --- Los sprites

def _texturas(equipo):
    """Las texturas del equipo, ya con el agachado estirado.

    Se aplica recortar_agachado porque es lo que hace el juego, no cargar_texturas
    sola: las pruebas tienen que medir lo que se ve en pantalla.
    """
    return personaje.recortar_agachado(personaje.cargar_texturas(equipo))


def _texturas_completas(equipo):
    """Los tres estados tienen al menos un fotograma."""
    texturas = _texturas(equipo)
    return all(texturas.get(estado) for estado in ("correr", "saltar", "agacharse"))


def _altos_de_sprite():
    """Los altos con los que quedaron los sprites de correr y de agacharse."""
    texturas = _texturas("CT")
    return (
        texturas["correr"][0].get_height(),
        texturas["agacharse"][0].get_height(),
    )


def _agachado_entra_en_la_hitbox():
    """El sprite de agachar no se dibuja mas ancho que la hitbox.

    El de agachar se recorta, asi que su ancho es el que de verdad ocupa el
    torso. No puede pasar del ancho de la hitbox: un dibujo mas ancho golpearia
    obstaculos que no se ven.
    """
    for equipo in ("CT", "T"):
        texturas = _texturas(equipo)
        if not texturas.get("correr") or not texturas.get("agacharse"):
            return False
        ancho_hitbox = max(f.get_width() for f in texturas["correr"])
        for f in texturas["agacharse"]:
            if f.get_width() > ancho_hitbox:
                return False
    return True


def _agachado_sale_del_sprite_de_agachar():
    """El agachado usa el sprite de agacharse, no el de correr recortado.

    Es el bug que se corrigio: al agacharse se veia la pose de correr con las
    piernas cortadas. Ahora se recorta el sprite de agacharse. Se comprueba que
    el resultado sea el recorte del sprite de agacharse y que NO sea igual al
    recorte del de correr.
    """
    for equipo in ("CT", "T"):
        texturas = _texturas(equipo)
        if not texturas.get("correr") or not texturas.get("agacharse"):
            return False

        agachado = texturas["agacharse"][0]

        # Tiene que ser el pedazo de arriba del sprite de agacharse.
        esperado = personaje._recortar_torso(
            personaje.cargar_texturas(equipo)["agacharse"][0]
        )
        if agachado.get_size() != esperado.get_size():
            return False
        if pygame.image.tobytes(agachado, "RGBA") != pygame.image.tobytes(
            esperado, "RGBA"
        ):
            return False

        # Y no puede ser el sprite de correr recortado.
        correr = max(texturas["correr"], key=lambda f: f.get_width())
        recorte_correr = personaje._recortar_torso(correr)
        if pygame.image.tobytes(agachado, "RGBA") == pygame.image.tobytes(
            recorte_correr, "RGBA"
        ):
            return False
    return True


def _agachado_distingue_equipos():
    """El agachado de CT y el de T no son el mismo sprite.

    Si el recorte usara siempre el de CT, jugar con T veria al personaje de CT
    agachado.
    """
    recortes = {}
    for equipo in ("CT", "T"):
        texturas = _texturas(equipo)
        if not texturas.get("agacharse"):
            return False
        recortes[equipo] = texturas["agacharse"][0]

    return pygame.image.tobytes(recortes["CT"], "RGBA") != pygame.image.tobytes(
        recortes["T"], "RGBA"
    )


def _agachado_conserva_su_alto():
    """El recorte del agachado tiene que dar exactamente los 56 px de alto.

    Ese alto es el que hace pasar al personaje por debajo de un obstaculo alto.
    """
    for equipo in ("CT", "T"):
        texturas = _texturas(equipo)
        if not texturas.get("agacharse"):
            return False
        if texturas["agacharse"][0].get_height() != constantes.ALTO_PERSONAJE_AGACHADO:
            return False
    return True


def _fotograma_de_correr_correcto():
    """El sprite de correr sale con el alto pedido.

    El ancho no se comprueba: lo decide la imagen de origen, que conserva su
    proporcion dentro de un rectangulo de ancho comun.
    """
    for equipo in ("CT", "T"):
        texturas = _texturas(equipo)
        if not texturas.get("correr"):
            return False
        altos = {f.get_height() for f in texturas["correr"]}
        if altos != {constantes.ALTO_PERSONAJE}:
            return False
    return True


def _dibuja_sin_sprites():
    """Sin sprites, dibujar pinta un rectangulo del tamano del personaje.

    Es el caso de respaldo: el juego tiene que arrancar aunque falte un asset.
    """
    pygame.init()
    lienzo = pygame.Surface((constantes.ANCHO, constantes.ALTO))
    lienzo.fill(constantes.COLOR_FONDO)

    pers = personaje_en_suelo()
    pers.dibujar(lienzo)

    # se mira un pixel del centro del personaje, que tiene que ser el color de
    # reemplazo y no el del fondo
    return lienzo.get_at(pers.rect.center) == constantes.COLOR_PERSONAJE_SIN_SPRITE


def _aterriza():
    """Dice si el personaje vuelve al suelo y se queda ahi, sin hundirse."""
    pers = _saltar()
    correr(pers, 90)
    if not pers.en_suelo or pers.posicion_y != constantes.SUELO_Y:
        return False

    # otros dos segundos apoyado: no se debe seguir bajando
    correr(pers, 120)
    return pers.posicion_y == constantes.SUELO_Y and pers.en_suelo


def trayectorias_identicas(primero, segundo, delta=DELTA, fotogramas=90):
    """Corre dos personajes en paralelo y dice si siguen siendo iguales."""
    for _ in range(fotogramas):
        primero.actualizar(delta)
        segundo.actualizar(delta)
        if primero.posicion_y != segundo.posicion_y:
            return False
    return primero.posicion_y == segundo.posicion_y


def _escena_titulo():
    """Una EscenaTitulo con el juego stub."""
    escena = juego.EscenaTitulo(juego_stub())
    escena.inicializar()
    return escena


def _espacio_abre_la_eleccion():
    escena = _escena_titulo()
    escena.manejar_eventos(tecla(pygame.KEYDOWN, pygame.K_SPACE))
    return escena.juego.cambio_de_escena == "equipo"


def _elegir(equipo):
    """El equipo que queda elegido y la escena a la que se entra."""
    escena = escena_de_equipo()
    escena.manejar_eventos(click_equipo(equipo))
    return escena.juego.equipo, escena.juego.cambio_de_escena


def _click_va_por_la_mitad():
    """El mismo equipo se elige en cualquier punto de su mitad."""
    for equipo, rango in (("CT", (0, constantes.ANCHO // 2 - 1)),
                          ("T", (constantes.ANCHO // 2, constantes.ANCHO - 1))):
        for x in rango:
            escena = escena_de_equipo()
            escena.manejar_eventos(
                boton(pygame.MOUSEBUTTONDOWN, constantes.BOTON_IZQUIERDO, (x, 0))
            )
            if escena.juego.equipo != equipo:
                return False
    return True


def _click_derecho_no_elige():
    """Solo el click izquierdo elige: el derecho es el de agacharse."""
    escena = escena_de_equipo()
    escena.manejar_eventos(
        boton(pygame.MOUSEBUTTONDOWN, constantes.BOTON_DERECHO, (constantes.ANCHO - 1, 0))
    )
    return (escena.juego.equipo, escena.juego.cambio_de_escena) == ("CT", None)


def _esc_vuelve_al_titulo():
    escena = escena_de_equipo()
    escena.manejar_eventos(tecla(pygame.KEYDOWN, pygame.K_ESCAPE))
    return escena.juego.cambio_de_escena == "titulo"


def _dibuja_los_dos_equipos():
    """La pantalla de eleccion dibuja los dos nombres y no falla al pintar."""
    escena = escena_de_equipo()
    lienzo = juego.Lienzo()
    lienzo.superficie.fill(constantes.COLOR_FONDO)

    escena.dibujar(lienzo.superficie)

    for equipo in ("CT", "T"):
        if not juego.NOMBRES_DE_EQUIPO[equipo]:
            return False

    # Los dos nombres se dibujan con el color de su equipo. Se recorre la
    # banda donde van los nombres y se busca el color de cada uno.
    for equipo in ("CT", "T"):
        color = juego.COLOR_DE_EQUIPO[equipo]
        if not any(
            lienzo.superficie.get_at((x, y))[:3] == color
            for y in (438, 442, 446)
            for x in range(0, constantes.ANCHO, 2)
        ):
            return False
    return True


def _nombres_no_se_pisan():
    """Cada nombre cae en su mitad: el de CT a la izquierda, el de T a la derecha.

    Antes los dos se centraban en el medio de la pantalla y se pisaban, asi que
    el color de un equipo aparecia en la mitad del otro.
    """
    escena = escena_de_equipo()
    lienzo = juego.Lienzo()
    lienzo.superficie.fill(constantes.COLOR_FONDO)
    escena.dibujar(lienzo.superficie)

    mitad = constantes.ANCHO // 2
    for equipo, en_su_mitad in (("CT", lambda x: x < mitad),
                                ("T", lambda x: x >= mitad)):
        color = juego.COLOR_DE_EQUIPO[equipo]
        for y in (438, 442, 446):
            for x in range(0, constantes.ANCHO, 2):
                if lienzo.superficie.get_at((x, y))[:3] == color:
                    if not en_su_mitad(x):
                        return False
    return True


def _resaltado_con_teclas():
    """A/D y las flechas mueven el resaltado de un equipo al otro."""
    escena = escena_de_equipo()
    if escena.resaltado != "CT":
        return False

    for key, esperado in (
        (pygame.K_RIGHT, "T"),
        (pygame.K_d, "T"),
        (pygame.K_LEFT, "CT"),
        (pygame.K_a, "CT"),
    ):
        escena.manejar_eventos(tecla(pygame.KEYDOWN, key))
        if escena.resaltado != esperado:
            return False
    return True


def _hover_resalta():
    """Apuntar el raton a una mitad resalta el equipo de esa mitad."""
    escena = escena_de_equipo()
    escena.manejar_eventos(movimiento(constantes.ANCHO - 1))
    if escena.resaltado != "T":
        return False

    escena.manejar_eventos(movimiento(0))
    return escena.resaltado == "CT"


def _espacio_confirma_el_resaltado():
    """SPACE confirma el equipo resaltado con el teclado."""
    escena = escena_de_equipo()
    escena.manejar_eventos(tecla(pygame.KEYDOWN, pygame.K_RIGHT))
    escena.manejar_eventos(tecla(pygame.KEYDOWN, pygame.K_SPACE))
    return (escena.juego.equipo, escena.juego.cambio_de_escena) == ("T", "juego")


def _enter_confirma_el_resaltado():
    """ENTER confirma el equipo resaltado, que arranca en CT."""
    escena = escena_de_equipo()
    escena.manejar_eventos(tecla(pygame.KEYDOWN, pygame.K_RETURN))
    return (escena.juego.equipo, escena.juego.cambio_de_escena) == ("CT", "juego")


def _eleccion_dibuja_el_fondo():
    """La pantalla de eleccion pinta el mismo fondo que el titulo."""
    escena = escena_de_equipo()
    if escena.fondo is None:
        return False

    lienzo = juego.Lienzo()
    lienzo.superficie.fill(constantes.COLOR_FONDO)
    escena.actualizar(DELTA)
    escena.dibujar(lienzo.superficie)

    return any(
        lienzo.superficie.get_at((x, y))[:3] != constantes.COLOR_FONDO
        for y in range(0, constantes.ALTO, 20)
        for x in range(0, constantes.ANCHO, 20)
    )


def _mapea_el_raton_al_lienzo():
    """Un punto de la ventana se traduce a su lugar en el lienzo virtual.

    En 1920x1080 el lienzo ocupa toda la ventana al doble de escala, asi que la
    mitad del CT en el lienzo (x=240) esta en la ventana en x=480.
    """
    tamano = (1920, 1080)
    return (
        casi_igual(juego.a_coordenadas_del_lienzo((480, 0), tamano)[0], 240)
        and casi_igual(juego.a_coordenadas_del_lienzo((1440, 0), tamano)[0], 720)
        and casi_igual(juego.a_coordenadas_del_lienzo((960, 0), tamano)[0], 480)
    )


def _click_en_pantalla_completa():
    """En pantalla completa el click elige el equipo donde se ve.

    Antes se comparaba la coordenada cruda de la ventana con la mitad del
    lienzo, asi que con la ventana al doble de escala la zona de x=480 a x=960
    elegia T aunque en pantalla se viera CT.
    """
    for x, esperado in ((480, "CT"), (1440, "T")):
        escena = escena_de_equipo((1920, 1080))
        escena.manejar_eventos(
            boton(pygame.MOUSEBUTTONDOWN, constantes.BOTON_IZQUIERDO, (x, 540))
        )
        if (escena.juego.equipo, escena.juego.cambio_de_escena) != (esperado, "juego"):
            return False
    return True


def _fondo_se_desplaza():
    """El fondo del titulo avanza con el tiempo."""
    fondo_titulo = fondo.Fondo()
    fondo_titulo.actualizar(1.0)
    return fondo_titulo.desplazamiento > 0.0


def _fondo_rota_de_escenario():
    """Pasado el tiempo, el fondo pasa al escenario siguiente."""
    fondo_titulo = fondo.Fondo()
    primero = fondo_titulo.indice
    fondo_titulo.actualizar(constantes.SEGUNDOS_POR_FONDO)
    if fondo_titulo.indice == primero:
        return False

    # Despues de dar la vuelta a todos, vuelve al primero.
    for _ in range(len(fondo_titulo.nombres) - 1):
        fondo_titulo.actualizar(constantes.SEGUNDOS_POR_FONDO)
    return fondo_titulo.indice == primero


def _titulo_dibuja_el_fondo():
    """La pantalla de titulo pinta su fondo y no falla al dibujar."""
    escena = _escena_titulo()
    if escena.fondo is None:
        return False

    lienzo = juego.Lienzo()
    lienzo.superficie.fill(constantes.COLOR_FONDO)
    escena.actualizar(DELTA)
    escena.dibujar(lienzo.superficie)

    # Con el fondo andando, algun pixel deja de ser el color de fondo plano.
    return any(
        lienzo.superficie.get_at((x, y))[:3] != constantes.COLOR_FONDO
        for y in range(0, constantes.ALTO, 20)
        for x in range(0, constantes.ANCHO, 20)
    )


def _dibuja_sin_retratos():
    """Sin los archivos de retrato, la pantalla se dibuja igual.

    El equipo se elige por la mitad de la pantalla, no mirando la imagen, asi
    que la eleccion tiene que funcionar aunque falten los assets.
    """
    stub = juego_stub()
    stub.retratos_equipo = {"CT": None, "T": None}
    escena = juego.EscenaEquipo(stub)
    escena.inicializar()

    lienzo = juego.Lienzo()
    lienzo.superficie.fill(constantes.COLOR_FONDO)
    escena.dibujar(lienzo.superficie)

    escena.manejar_eventos(click_equipo("T"))
    return escena.juego.equipo == "T" and escena.juego.cambio_de_escena == "juego"


def _texturas_de_la_partida(equipo):
    """Las texturas que carga la escena de partida para un equipo."""
    stub = juego_stub()
    stub.equipo = equipo
    escena = juego.EscenaJuego(stub)
    escena.inicializar()
    return escena.personaje.texturas


def _carga_sprites_del_equipo():
    """La partida carga los sprites del equipo elegido, y CT y T son distintos.

    CT y T pueden medir lo mismo (los dos sprites de correr salen de 76 px de
    ancho), asi que no se compara el tamano sino el contenido: si la escena
    cargara siempre el mismo equipo, los pixeles serian iguales.
    """
    ct = _texturas_de_la_partida("CT")
    tt = _texturas_de_la_partida("T")
    for estado in ("correr", "saltar", "agacharse"):
        a, b = ct.get(estado), tt.get(estado)
        if not a or not b:
            return False
        if pygame.image.tobytes(a[0], "RGBA") == pygame.image.tobytes(b[0], "RGBA"):
            return False
    return True


# --- Ayudantes para los obstaculos ---------------------------------------

def _soltar_sobre_el_jugador(escena, tipo):
    """Un obstaculo del tipo pedido, alineado con el jugador y sin spawns."""
    cada_uno = obstaculo.Obstaculo(tipo, escena.juego.equipo)
    cada_uno.x = float(escena.personaje.rect.left)
    cada_uno.rect.left = round(cada_uno.x)
    escena.obstaculos = [cada_uno]
    escena.tiempo_para_obstaculo = 99.0
    return cada_uno


def _zonas_por_puntaje():
    """Los cuatro escenarios, con los bordes exactos de cada umbral."""
    return (
        juego.zona_de_puntaje(0) == "inicial"
        and juego.zona_de_puntaje(499) == "inicial"
        and juego.zona_de_puntaje(500) == "combate"
        and juego.zona_de_puntaje(999) == "combate"
        and juego.zona_de_puntaje(1000) == "bombas"
        and juego.zona_de_puntaje(1499) == "bombas"
        and juego.zona_de_puntaje(1500) == "avanzada"
        and juego.zona_de_puntaje(9999) == "avanzada"
    )


def _dificultad_creciente_y_acotada():
    """La velocidad sube y el intervalo baja, con tope en la zona avanzada."""
    return (
        casi_igual(
            juego.velocidad_obstaculo(0),
            constantes.VELOCIDAD_OBSTACULO_MIN,
        )
        and casi_igual(
            juego.velocidad_obstaculo(750),
            (constantes.VELOCIDAD_OBSTACULO_MIN + constantes.VELOCIDAD_OBSTACULO_MAX) / 2,
        )
        and casi_igual(
            juego.velocidad_obstaculo(1500),
            constantes.VELOCIDAD_OBSTACULO_MAX,
        )
        and casi_igual(
            juego.velocidad_obstaculo(3000),
            constantes.VELOCIDAD_OBSTACULO_MAX,
        )
        and casi_igual(juego.intervalo_obstaculo(0), constantes.INTERVALO_MIN)
        and casi_igual(
            juego.intervalo_obstaculo(1500),
            constantes.INTERVALO_MAX,
        )
        and casi_igual(
            juego.intervalo_obstaculo(3000),
            constantes.INTERVALO_MAX,
        )
        and juego.velocidad_obstaculo(750) > juego.velocidad_obstaculo(0)
        and juego.intervalo_obstaculo(750) < juego.intervalo_obstaculo(0)
    )


def _la_persona_es_del_rival():
    """Si el jugador es CT aparece un T, y al reves."""
    return (
        obstaculo.rival_de("CT") == "T"
        and obstaculo.rival_de("T") == "CT"
        and obstaculo.ruta_de("persona", "CT").endswith("persona_t.png")
        and obstaculo.ruta_de("persona", "T").endswith("persona_ct.png")
    )


def _la_caja_no_arrastra_pixeles_sueltos():
    """La caja se recorta a su cuerpo visible, no a un pixel perdido."""
    imagen = obstaculo.cargar_obstaculo("caja")
    if imagen is None:
        return False

    ancho, alto = imagen.get_size()
    return (
        alto == constantes.ALTO_OBSTACULO_CAJA
        and ancho < 70
        and casi_igual(ancho / alto, 448 / 440)
    )


def _el_obstaculo_avanza_hacia_la_izquierda():
    caja = obstaculo.Obstaculo("caja", "CT", constantes.ANCHO)
    inicio = caja.rect.left
    caja.actualizar(1.0, 300.0)
    return caja.rect.left == inicio - 300


def _el_obstaculo_sale_de_pantalla():
    caja = obstaculo.Obstaculo("caja", "CT")
    caja.x = -500.0
    caja.rect.left = round(caja.x)
    return caja.fuera_de_pantalla()


def _el_proyectil_va_por_encima_del_agachado():
    caja = obstaculo.Obstaculo("caja", "CT")
    proyectil = obstaculo.Obstaculo("proyectil", "CT")
    return (
        caja.rect.bottom == constantes.SUELO_Y
        and proyectil.rect.bottom
        == constantes.SUELO_Y - constantes.ALTO_PERSONAJE_AGACHADO - 1
    )


def _el_salto_pasa_sobre_una_caja():
    """En el punto mas alto, el personaje queda por encima de una caja."""
    pers = personaje.Personaje()
    pers.saltar()
    pers.actualizar(-constantes.VELOCIDAD_SALTO / constantes.GRAVEDAD)
    caja = obstaculo.Obstaculo("caja", "CT")
    caja.x = float(pers.rect.left)
    caja.rect.left = round(caja.x)
    return not caja.colisiona(pers.rect)


def _agachado_pasa_bajo_el_proyectil():
    escena = escena_de_juego()
    escena.personaje.agachar(True)
    _soltar_sobre_el_jugador(escena, "proyectil")
    escena.actualizar(DELTA)
    return escena.juego.cambio_de_escena is None


def _de_pie_golpea_el_proyectil():
    escena = escena_de_juego()
    _soltar_sobre_el_jugador(escena, "proyectil")
    escena.actualizar(DELTA)
    return escena.juego.cambio_de_escena == "gameover"


def _chocar_termina_la_partida():
    escena = escena_de_juego()
    _soltar_sobre_el_jugador(escena, "caja")
    escena.actualizar(DELTA)
    return (
        escena.juego.cambio_de_escena == "gameover"
        and escena.juego.ultimo_puntaje == escena.puntaje
    )


def _aparece_un_obstaculo():
    escena = escena_de_juego()
    escena._elegir_tipo = lambda: "caja"
    escena.tiempo_para_obstaculo = 0.0
    escena.actualizar(DELTA)
    return len(escena.obstaculos) == 1 and escena.obstaculos[0].tipo == "caja"


def _los_obstaculos_se_descartan():
    escena = escena_de_juego()
    _soltar_sobre_el_jugador(escena, "caja")
    escena.obstaculos[0].x = -500.0
    escena.obstaculos[0].rect.left = -500
    escena.actualizar(DELTA)
    return escena.obstaculos == []


def _cuenta_las_personas_una_vez():
    escena = escena_de_juego()
    persona = _soltar_sobre_el_jugador(escena, "persona")
    persona.x = float(escena.personaje.rect.left - persona.rect.width - 10)
    persona.rect.left = round(persona.x)
    escena.actualizar(DELTA)
    escena.actualizar(DELTA)
    return escena.personas_superadas == 1


def _el_fondo_de_la_partida_no_rota():
    un_fondo = fondo.Fondo(rotar=False)
    antes = un_fondo.indice
    for _ in range(int(constantes.SEGUNDOS_POR_FONDO * 60)):
        un_fondo.actualizar(1.0 / 60)
    return un_fondo.indice == antes


def _el_fondo_cambia_de_escenario():
    un_fondo = fondo.Fondo(rotar=False)
    un_fondo.cambiar_escenario("bombas")
    cambio = un_fondo.nombres[un_fondo.indice] == "bombas"
    un_fondo.cambiar_escenario("no-existe")
    return cambio and un_fondo.nombres[un_fondo.indice] == "bombas"


def _la_partida_usa_el_fondo_de_la_zona():
    escena = escena_de_juego()
    escena.puntaje = constantes.UMBRAL_ZONA_BOMBAS
    escena._actualizar_fondo(DELTA)
    return escena.fondo.nombres[escena.fondo.indice] == "bombas"


def _el_fondo_de_la_partida_va_mas_lento():
    escena = escena_de_juego()
    escena._actualizar_fondo(DELTA)
    return (
        casi_igual(
            escena.fondo.velocidad,
            juego.velocidad_obstaculo(0) * constantes.FACTOR_PARALLAX_FONDO,
        )
        and escena.fondo.velocidad < juego.velocidad_obstaculo(0)
    )


def _el_suelo_se_escala_a_la_franja():
    un_suelo = fondo.Suelo()
    return (
        un_suelo.imagen is not None
        and un_suelo.imagen.get_height() == constantes.ALTO - constantes.SUELO_Y
    )


def _el_suelo_avanza_con_su_velocidad():
    un_suelo = fondo.Suelo()
    un_suelo.velocidad = 300.0
    un_suelo.actualizar(0.5)
    return casi_igual(un_suelo.desplazamiento, 150.0)


def _la_partida_mueve_el_suelo_con_los_obstaculos():
    escena = escena_de_juego()
    escena.puntaje = 750
    escena._actualizar_fondo(DELTA)
    return (
        escena.suelo is not None
        and casi_igual(
            escena.suelo.velocidad,
            juego.velocidad_obstaculo(750) * constantes.FACTOR_PARALLAX_SUELO,
        )
    )


def _la_partida_dibuja_el_suelo_del_asset():
    escena = escena_de_juego()
    if escena.suelo is None or escena.suelo.imagen is None:
        return False

    lienzo = juego.Lienzo()
    escena.dibujar(lienzo.superficie)
    color = tuple(lienzo.superficie.get_at((0, constantes.SUELO_Y)))[:3]
    esperado = tuple(escena.suelo.imagen.get_at((0, 0)))[:3]
    return color == esperado


def _el_suelo_sin_asset_no_rompe():
    un_suelo = fondo.Suelo()
    un_suelo.imagen = None
    lienzo = juego.Lienzo()
    un_suelo.dibujar(lienzo.superficie)
    color = tuple(lienzo.superficie.get_at((0, constantes.SUELO_Y)))[:3]
    return color == constantes.COLOR_SUELO


def _gameover_pasa_a_iniciales():
    stub = juego_stub()
    stub.ultimo_puntaje = 777
    escena = juego.EscenaGameOver(stub)
    escena.inicializar()

    lienzo = juego.Lienzo()
    escena.dibujar(lienzo.superficie)
    escena.manejar_eventos(tecla(pygame.KEYDOWN, pygame.K_SPACE))
    return escena.juego.cambio_de_escena == "iniciales"


def _gameover_esc_vuelve_al_titulo():
    stub = juego_stub()
    stub.ultimo_puntaje = 777
    escena = juego.EscenaGameOver(stub)
    escena.inicializar()
    escena.manejar_eventos(tecla(pygame.KEYDOWN, pygame.K_ESCAPE))
    return escena.juego.cambio_de_escena == "titulo"


def _chocar_guarda_las_personas():
    """El game over guarda el puntaje y las personas superadas de la partida."""
    escena = escena_de_juego()
    escena.personas_superadas = 4
    _soltar_sobre_el_jugador(escena, "caja")
    escena.actualizar(DELTA)
    return (
        escena.juego.ultimo_puntaje == escena.puntaje
        and escena.juego.ultimas_personas == 4
    )


# --- Ayudantes para el ranking -------------------------------------------

def _escena_iniciales(ruta_ranking):
    """Una EscenaIniciales apuntada a un ranking temporal."""
    stub = juego_stub()
    stub.ruta_ranking = ruta_ranking
    stub.ruta_ranking_html = ruta_ranking.with_name("ranking.html")
    stub.ultimo_puntaje = 1250
    stub.ultimas_personas = 37
    stub.equipo = "T"
    escena = juego.EscenaIniciales(stub)
    escena.inicializar()
    return escena


def _teclea(escena, texto):
    """Escribe un texto letra por letra, como si se tipeara."""
    for letra in texto:
        escena.manejar_eventos(tecla(pygame.KEYDOWN, ord(letra)))
    return escena


def _iniciales_por_flechas():
    """Las flechas cambian la letra y mueven el slot, dando la vuelta."""
    escena = _escena_iniciales(ranking.RUTA_RANKING)
    escena.manejar_eventos(tecla(pygame.KEYDOWN, pygame.K_UP))
    if escena.letras[0] != "B":
        return False

    escena.manejar_eventos(tecla(pygame.KEYDOWN, pygame.K_DOWN))
    if escena.letras[0] != "A":
        return False

    # Bajar desde A tiene que dar la vuelta a Z, no quedarse pegado.
    escena.manejar_eventos(tecla(pygame.KEYDOWN, pygame.K_DOWN))
    if escena.letras[0] != "Z":
        return False

    escena.manejar_eventos(tecla(pygame.KEYDOWN, pygame.K_RIGHT))
    if escena.slot != 1:
        return False

    escena.manejar_eventos(tecla(pygame.KEYDOWN, pygame.K_RIGHT))
    escena.manejar_eventos(tecla(pygame.KEYDOWN, pygame.K_RIGHT))
    return escena.slot == 2


def _slot_no_se_pasa_del_borde():
    """El cursor se queda en 0 o en 2, no da la vuelta."""
    escena = _escena_iniciales(ranking.RUTA_RANKING)
    escena.manejar_eventos(tecla(pygame.KEYDOWN, pygame.K_LEFT))
    si_izquierda = escena.slot == 0
    escena.manejar_eventos(tecla(pygame.KEYDOWN, pygame.K_RIGHT))
    escena.manejar_eventos(tecla(pygame.KEYDOWN, pygame.K_RIGHT))
    return si_izquierda and escena.slot == 2


def _tipeo_directo():
    """Una letra de la A a la Z se escribe y avanza el slot."""
    escena = _escena_iniciales(ranking.RUTA_RANKING)
    _teclea(escena, "luc")
    return "".join(escena.letras) == "LUC"


def _guardar_escribe_el_ranking(tmp):
    """Confirmar agrega la partida, regenera el HTML y abre el navegador."""
    ruta = tmp / "ranking.txt"
    escena = _escena_iniciales(ruta)
    _teclea(escena, "luc")
    escena.manejar_eventos(tecla(pygame.KEYDOWN, pygame.K_RETURN))

    if not escena.guardado:
        return False

    partidas = ranking.leer_partidas(ruta, avisar=lambda _: None)
    guardada = (
        len(partidas) == 1
        and partidas[0].iniciales == "LUC"
        and partidas[0].puntaje == 1250
        and partidas[0].equipo == "T"
        and partidas[0].personas == 37
    )
    html_creado = ruta.with_name("ranking.html").exists()
    abierto = escena.juego.navegador_abierto is not None

    escena.manejar_eventos(tecla(pygame.KEYDOWN, pygame.K_RETURN))
    return (
        guardada
        and html_creado
        and abierto
        and escena.juego.cambio_de_escena == "titulo"
    )


def _esc_cancela_sin_guardar(tmp):
    """ESC sale de las iniciales y no escribe nada."""
    ruta = tmp / "ranking.txt"
    escena = _escena_iniciales(ruta)
    _teclea(escena, "luc")
    escena.manejar_eventos(tecla(pygame.KEYDOWN, pygame.K_ESCAPE))
    return (
        escena.juego.cambio_de_escena == "titulo"
        and not ruta.exists()
        and escena.juego.navegador_abierto is None
    )


def _error_al_guardar_no_rompe(tmp):
    """Si el ranking no se puede escribir, se avisa y el juego sigue.

    Para forzar el error se usa un archivo como si fuera carpeta: crear el
    directorio padre o abrir el archivo tira OSError.
    """
    estorbo = tmp / "estorbo"
    estorbo.write_text("no soy una carpeta", encoding="utf-8")

    stub = juego_stub()
    stub.ruta_ranking = estorbo / "ranking.txt"
    stub.ruta_ranking_html = estorbo / "ranking.html"
    escena = juego.EscenaIniciales(stub)
    escena.inicializar()
    escena.manejar_eventos(tecla(pygame.KEYDOWN, pygame.K_RETURN))

    dibujo = True
    try:
        escena.dibujar(juego.Lienzo().superficie)
    except Exception:
        dibujo = False

    return (
        escena.error is not None
        and not escena.guardado
        and escena.juego.cambio_de_escena is None
        and dibujo
    )


def con_carpeta_temporal(comprobar):
    """Arma una funcion que corre `comprobar` dentro de una carpeta temporal.

    Las pruebas del ranking tienen que escribir archivos de verdad, asi que
    cada una trabaja en su propio directorio y no toca el ranking.txt real.
    """
    def correr():
        with tempfile.TemporaryDirectory() as carpeta:
            return comprobar(Path(carpeta))
    return correr


# --- Ayudantes para los datos --------------------------------------------

LINEAS_DE_EJEMPLO = (
    "LUC;1250;CT;2026-10-16 14:32:05;37\n"
    "LUC;980;CT;2026-10-16 14:35:12;29\n"
    "ANA;1500;T;2026-10-16 15:02:44;45\n"
    "LUC;640;T;2026-10-16 15:10:01;19\n"
)


def _escribe(tmp, contenido, nombre="ranking.txt"):
    ruta = tmp / nombre
    ruta.write_text(contenido, encoding="utf-8")
    return ruta


def _parsear():
    partida = ranking.parsear_linea("LUC;1250;CT;2026-10-16 14:32:05;37")
    return (
        partida.iniciales == "LUC"
        and partida.puntaje == 1250
        and partida.equipo == "CT"
        and partida.personas == 37
        and partida.fecha.year == 2026
        and partida.fecha.hour == 14
    )


def _lineas_invalidas(tmp):
    """Las lineas mal formadas se saltean con aviso y no cortan la lectura."""
    ruta = _escribe(
        tmp,
        "LUC;1250;CT;2026-10-16 14:32:05;37\n"
        "esto no es una partida\n"
        "XX;100;CT;2026-10-16 14:32:05;1\n"
        "LUC;no-es-numero;CT;2026-10-16 14:32:05;1\n"
        "LUC;100;XX;2026-10-16 14:32:05;1\n"
        "LUC;100;CT;16-10-2026;1\n",
    )
    avisos = []
    partidas = ranking.leer_partidas(ruta, avisar=avisos.append)
    return len(partidas) == 1 and len(avisos) == 5


def _archivo_inexistente(tmp):
    ruta = tmp / "nuevo.txt"
    partidas = ranking.leer_partidas(ruta, avisar=lambda _: None)
    return partidas == [] and ruta.exists()


def _agregar_es_append(tmp):
    """Agregar no pisa lo anterior: el ranking es historico."""
    ruta = _escribe(tmp, LINEAS_DE_EJEMPLO)
    ranking.agregar_partida(ruta, "ana", 1700, "CT", 50)
    ranking.agregar_partida(ruta, "BOB", 30, "T", 2)
    return len(ranking.leer_partidas(ruta, avisar=lambda _: None)) == 6


def _orden_y_empates(tmp):
    """Puntaje descendente y, en empate, gana la partida mas antigua."""
    ruta = _escribe(
        tmp,
        "ENP;900;CT;2026-10-16 14:00:00;1\n"
        "VIE;900;T;2026-09-01 09:00:00;2\n"
        "ALT;1500;CT;2026-10-16 14:32:05;3\n",
    )
    orden = ranking.clasificar(ranking.leer_partidas(ruta, avisar=lambda _: None))
    return (
        [partida.iniciales for partida in orden] == ["ALT", "VIE", "ENP"]
    )


def _top_recorta(tmp):
    ruta = _escribe(
        tmp,
        "".join(
            "PA{};{};CT;2026-10-16 14:{:02d}:00;1\n".format(
                chr(ord("A") + indice), indice * 10, indice
            )
            for indice in range(15)
        ),
    )
    mejores = ranking.top(ranking.leer_partidas(ruta, avisar=lambda _: None))
    return (
        len(mejores) == 10
        and mejores[0].puntaje == 140
        and mejores[-1].puntaje == 50
    )


def _cuenta_y_ratio(tmp):
    """D cuenta todas las partidas del jugador; K/D se redondea a un decimal."""
    ruta = _escribe(tmp, LINEAS_DE_EJEMPLO)
    partidas = ranking.leer_partidas(ruta, avisar=lambda _: None)
    cantidades = ranking.contar_por_iniciales(partidas)
    return (
        cantidades["LUC"] == 3
        and cantidades["ANA"] == 1
        and ranking.ratio(37, 3) == "12.3"
        and ranking.ratio(45, 1) == "45.0"
    )


def _generar_html(tmp):
    """El HTML tiene las columnas, el top 10 y el link a estilos.css."""
    ruta = _escribe(tmp, LINEAS_DE_EJEMPLO)
    salida = generar_ranking.generar_html(ruta, tmp / "salida.html")
    texto = salida.read_text(encoding="utf-8")

    tiene_columnas = all(
        columna in texto
        for columna in ("POS", "INICIALES", "EQUIPO", "SCORE", "K/D", "FECHA")
    )
    tiene_css = 'href="estilos.css"' in texto
    tiene_filas = texto.count("<tr class=\"fila") == 4
    ordenado = texto.index("ANA") < texto.index("LUC")
    return tiene_columnas and tiene_css and tiene_filas and ordenado


def _generar_html_escapa():
    """El generador escapa lo que llega, aunque los datos ya esten validados.

    Los datos validos no pueden traer HTML, pero la funcion no tiene que confiar
    en eso: se le pasa una partida armada a mano para comprobarlo.
    """
    from datetime import datetime

    tramposa = ranking.Partida(
        "<B>", 100, "CT", datetime(2026, 10, 16, 14, 0, 0), 1
    )
    fila = generar_ranking._fila_html(1, tramposa, 1)
    return "<B>" not in fila and "&lt;B&gt;" in fila


def _generar_html_vacio(tmp):
    """Sin partidas el HTML se genera igual, con un aviso en la tabla."""
    ruta = tmp / "vacio.txt"
    salida = generar_ranking.generar_html(ruta, tmp / "salida.html")
    texto = salida.read_text(encoding="utf-8")
    return salida.exists() and "TODAVIA NO HAY PARTIDAS" in texto


def _iniciales_validas():
    """Las iniciales y el equipo se normalizan a mayusculas."""
    return (
        ranking.validar_iniciales("luc") == "LUC"
        and ranking.validar_equipo("ct") == "CT"
    )


def _iniciales_invalidas():
    """Lo que no son 3 letras tiene que rechazarse."""
    for malo in ("LU", "LUCAS", "LU1", "L C", ""):
        try:
            ranking.validar_iniciales(malo)
        except ValueError:
            continue
        return False
    return True


def casos():
    """Arma la lista de (descripcion, condicion) a verificar."""
    # La altura del salto sale de la formula de docs/ESPECIFICACION.md:
    # altura = velocidad^2 / (2 * gravedad).
    altura_salto = constantes.VELOCIDAD_SALTO ** 2 / (2 * constantes.GRAVEDAD)

    # personaje.py
    # Los personajes se arman adentro de cada prueba, no una vez para todas.
    # Si se compartieran, una prueba que mueve un personaje romperia otra que
    # necesita que este recien creado.
    return [
        ("calcular_escala en 1920x1080 da 2.0",
         casi_igual(juego.calcular_escala(1920, 1080), 2.0)),

        ("calcular_escala en 1920x540 da 1.0: manda el ancho, no se recorta",
         casi_igual(juego.calcular_escala(1920, 540), 1.0)),

        ("calcular_escala en 800x600 da 800/960: manda el ancho, sobra alto",
         casi_igual(juego.calcular_escala(800, 600), 800 / constantes.ANCHO)),

        ("la imagen entra completa y centrada en toda una tanda de ventanas",
         all(imagen_entra(ancho, alto) for ancho, alto in TAMANOS_DE_VENTANA)),

        ("una ventana 16:9 no deja barras (1280x720)",
         juego.calcular_destino(1280, 720) == (0, 0, 1280, 720)),

        ("una ventana 4:3 deja barras de 75 px arriba y abajo (800x600)",
         juego.calcular_destino(800, 600) == (0, 75, 800, 450)),

        ("recortar_delta deja intacto un fotograma normal",
         casi_igual(juego.recortar_delta(0.016), 0.016, 0.000001)),

        ("recortar_delta recorta una congelacion de la maquina",
         juego.recortar_delta(0.5) == constantes.TOPE_DELTA),

        ("recortar_delta de cero sigue siendo cero",
         juego.recortar_delta(0) == 0),

        ("la altura del salto es la que dice la especificacion (168.75 px)",
         casi_igual(altura_salto, 168.75, 0.01)),

        # --- El personaje: la fisica

        ("el personaje arranca apoyado en el suelo y sin salto en curso",
         lambda: _arranca_apoyado()),

        ("el personaje sube de verdad al saltar",
         lambda: correr(_saltar(), 20) < constantes.SUELO_Y - 100),

        ("el personaje vuelve al suelo despues del salto y se queda ahi",
         _aterriza()),

        ("el salto real mide lo mismo que la formula (168.75 px)",
         casi_igual(altura_del_salto(), 168.75, 0.5)),

        ("no hay doble salto: apretar en el aire no cambia la trayectoria",
         lambda: _sin_doble_salto()),

        ("el salto dura 0.75 s: el doble de lo que tarda en subir",
         casi_igual(_duracion_del_salto(), 0.75, 0.05)),

        ("la altura del salto es la misma a 30 que a 60 por segundo",
         casi_igual(altura_del_salto(1 / 30), altura_del_salto(1 / 60), 0.5)),

        # --- El personaje: el agachado

        ("parado mide ALTO_PERSONAJE de alto",
         lambda: _alto_de(_agachado(False)) == constantes.ALTO_PERSONAJE),

        ("agachado mide ALTO_PERSONAJE_AGACHADO, mas bajo que parado",
         lambda: _alto_de(_agachado(True)) == constantes.ALTO_PERSONAJE_AGACHADO),

        ("agacharse no cambia la posicion horizontal",
         lambda: _agachado(True).rect.x == constantes.JUGADOR_X),

        ("agacharse no cambia el ancho de la hitbox",
         lambda: _agachado(True).rect.width == _agachado(False).rect.width),

        ("agacharse y levantarse no despega los pies del suelo",
         lambda: _pies_no_se_mueven()),

        ("agacharse en el aire no hace nada",
         lambda: _agachar_en_el_aire_no_hace_nada()),

        ("salir de un agachado con ESPACIO levanta al personaje de nuevo",
         lambda: _altura_tras_agacharse() == constantes.ALTO_PERSONAJE),

        ("la altura del salto es la misma saliendo de un agachado",
         lambda: casi_igual(altura_desde_agachado(), altura_del_salto(), 0.5)),

        # --- El personaje: el puntaje

        ("el puntaje son los segundos enteros por diez",
         [juego.calcular_puntaje(s) for s in (0, 0.5, 1, 1.99, 2, 59.9)]
         == [0, 0, 10, 10, 20, 590]),
# --- Los controles

        # docs/TEMATICA.md pide estos cuatro controles: SPACE/ARRIBA/CLICK IZQ
        # para saltar, y ABAJO/CLICK DER para agacharse.

        ("ESPACIO salta",
         lambda: _salta_con(tecla(pygame.KEYDOWN, pygame.K_SPACE))),

        ("ARRIBA salta",
         lambda: _salta_con(tecla(pygame.KEYDOWN, pygame.K_UP))),

        ("el click izquierdo salta",
         lambda: _salta_con(boton(pygame.MOUSEBUTTONDOWN, constantes.BOTON_IZQUIERDO))),

        ("ABAJO agacha en el suelo",
         lambda: _agacha_con(tecla(pygame.KEYDOWN, pygame.K_DOWN), True)),

        ("soltar ABAJO levanta",
         lambda: _agacha_con(
             tecla(pygame.KEYDOWN, pygame.K_DOWN), False,
             tecla(pygame.KEYUP, pygame.K_DOWN),
         )),

        ("el click derecho agacha en el suelo",
         lambda: _agacha_con(
             boton(pygame.MOUSEBUTTONDOWN, constantes.BOTON_DERECHO), True)),

        ("soltar el click derecho levanta",
         lambda: _agacha_con(
             boton(pygame.MOUSEBUTTONDOWN, constantes.BOTON_DERECHO), False,
             boton(pygame.MOUSEBUTTONUP, constantes.BOTON_DERECHO),
         )),

        ("con ABAJO y el click derecho, soltar uno NO levanta",
         lambda: _dos_agachadores_no_se_pisan()),

        ("el boton central no hace nada",
         lambda: not _salta_con(boton(pygame.MOUSEBUTTONDOWN, 2))),

        ("W tambien salta",
         lambda: _salta_con(tecla(pygame.KEYDOWN, pygame.K_w))),

        ("S tambien agacha en el suelo",
         lambda: _agacha_con(tecla(pygame.KEYDOWN, pygame.K_s), True)),

        ("soltar S levanta",
         lambda: _agacha_con(
             tecla(pygame.KEYDOWN, pygame.K_s), False,
             tecla(pygame.KEYUP, pygame.K_s),
         )),

        # --- La caida rapida

        ("agachar en el aire NO agacha el sprite: sigue el de salto",
         lambda: _agachar_en_el_aire_no_agacha()),

        ("agachar en el aire baja mas rapido",
         lambda: _vuelve_antes_si_cae_rapido()),

        ("agachar en el aire acorta el resto de la subida",
         lambda: apex_con_caida_rapida(0.30)[0] < apex_con_caida_rapida(99)[0]),

        ("encender la caida rapida no mueve al personaje de golpe",
         lambda: _caida_rapida_es_continua()),

        ("la caida rapida da el mismo apex a 30 que a 60 por segundo",
         lambda: casi_igual(
             apex_con_caida_rapida(0.30, 1 / 60)[0],
             apex_con_caida_rapida(0.30, 1 / 30)[0], 0.5)),

        ("el salto normal no cambio: 168.75 px, sin caida rapida",
         lambda: casi_igual(apex_con_caida_rapida(99)[0], 168.75, 0.5)),

        # --- Los sprites

        ("los sprites de los dos equipos se cargan y traen los tres estados",
         _texturas_completas("CT") and _texturas_completas("T")),

        ("los sprites del equipo salen con el alto pedido (96 parado, 56 agachado)",
         _altos_de_sprite() == (constantes.ALTO_PERSONAJE, constantes.ALTO_PERSONAJE_AGACHADO)),

        ("agachar usa el sprite de agacharse, no el de correr recortado",
         _agachado_sale_del_sprite_de_agachar()),

        ("el agachado de CT y el de T son distintos",
         _agachado_distingue_equipos()),

        ("el sprite de agachar conserva los 56 px de alto al recortarse",
         _agachado_conserva_su_alto()),

        ("el sprite de agachar nunca se dibuja mas ancho que la hitbox",
         _agachado_entra_en_la_hitbox()),

        ("el fotograma de correr sale con el alto pedido",
         _fotograma_de_correr_correcto()),

        ("cargar_textura devuelve None si el archivo no existe, sin fallar",
         personaje.cargar_textura("assets/no_existe_este_archivo.png", 96) is None),

        ("sin sprites el juego dibuja un rectangulo igual de grande",
         _dibuja_sin_sprites()),

        # --- La eleccion de personaje
        # docs/TEMATICA.md pide elegir entre CT y T antes de empezar, y
        # docs/ESPECIFICACION.md dice que ese equipo se guarda en el ranking.

        ("ESPACIO en el titulo lleva a la pantalla de eleccion, no a la partida",
         _espacio_abre_la_eleccion()),

        ("click en la mitad izquierda elige CT y arranca la partida",
         _elegir("CT") == ("CT", "juego")),

        ("click en la mitad derecha elige T y arranca la partida",
         _elegir("T") == ("T", "juego")),

        ("el click se decide por la mitad de la pantalla, no por el retrato",
         _click_va_por_la_mitad()),

        ("el click derecho no elige ni avanza de escena",
         _click_derecho_no_elige()),

        ("ESC en la eleccion vuelve al titulo",
         _esc_vuelve_al_titulo()),

        ("la partida carga los sprites del equipo elegido (CT y T son distintos)",
         _carga_sprites_del_equipo()),

        ("la eleccion dibuja los dos retratos y los dos nombres",
         _dibuja_los_dos_equipos()),

        ("la eleccion dibuja aunque falten los retratos",
         _dibuja_sin_retratos()),

        ("los nombres de los equipos no se pisan: cada uno cae en su mitad",
         _nombres_no_se_pisan()),

        ("A/D y las flechas mueven el resaltado de la eleccion",
         _resaltado_con_teclas()),

        ("apuntar con el raton resalta el equipo de esa mitad",
         _hover_resalta()),

        ("el raton se mapea del tamano de la ventana al lienzo",
         _mapea_el_raton_al_lienzo()),

        ("en pantalla completa el click elige el equipo donde se ve",
         _click_en_pantalla_completa()),

        ("SPACE confirma el equipo resaltado",
         _espacio_confirma_el_resaltado()),

        ("ENTER confirma el equipo resaltado",
         _enter_confirma_el_resaltado()),

        ("la eleccion dibuja el mismo fondo que el titulo",
         _eleccion_dibuja_el_fondo()),

        # --- El fondo del titulo
        ("el fondo del titulo avanza con el tiempo",
         _fondo_se_desplaza()),

        ("el fondo del titulo rota por los escenarios",
         _fondo_rota_de_escenario()),

        ("el titulo dibuja el fondo encima del color plano",
         _titulo_dibuja_el_fondo()),

        # --- Zonas y dificultad
        ("cada puntaje cae en su zona, con los bordes exactos",
         _zonas_por_puntaje),

        ("la dificultad crece y se topa en la zona avanzada",
         _dificultad_creciente_y_acotada),

        # --- Obstaculos
        ("la persona obstaculo es del equipo rival",
         _la_persona_es_del_rival),

        ("la caja no arrastra pixeles sueltos en la hitbox",
         _la_caja_no_arrastra_pixeles_sueltos),

        ("el obstaculo avanza hacia la izquierda",
         _el_obstaculo_avanza_hacia_la_izquierda),

        ("el obstaculo se descarta cuando sale de pantalla",
         _el_obstaculo_sale_de_pantalla),

        ("los de suelo van en el suelo y el proyectil por encima",
         _el_proyectil_va_por_encima_del_agachado),

        ("en el punto mas alto del salto se pasa sobre una caja",
         _el_salto_pasa_sobre_una_caja),

        ("agachado se pasa bajo el proyectil",
         _agachado_pasa_bajo_el_proyectil),

        ("de pie el proyectil golpea",
         _de_pie_golpea_el_proyectil),

        ("chocar con un obstaculo termina la partida",
         _chocar_termina_la_partida),

        ("despues del intervalo aparece un obstaculo",
         _aparece_un_obstaculo),

        ("los obstaculos que salen se descartan de la lista",
         _los_obstaculos_se_descartan),

        ("cada persona superada se cuenta una sola vez",
         _cuenta_las_personas_una_vez),

        # --- Fondo de la partida y game over
        ("el fondo de la partida no rota: lo elige el puntaje",
         _el_fondo_de_la_partida_no_rota),

        ("el fondo puede cambiar de escenario a mano",
         _el_fondo_cambia_de_escenario),

        ("la partida usa el escenario de la zona del puntaje",
         _la_partida_usa_el_fondo_de_la_zona),

        ("el fondo de la partida va mas lento que los obstaculos",
         _el_fondo_de_la_partida_va_mas_lento),

        ("el suelo ocupa la franja inferior",
         _el_suelo_se_escala_a_la_franja),

        ("el suelo avanza con su velocidad",
         _el_suelo_avanza_con_su_velocidad),

        ("la partida mueve el suelo con los obstaculos",
         _la_partida_mueve_el_suelo_con_los_obstaculos),

        ("la partida dibuja el suelo del asset",
         _la_partida_dibuja_el_suelo_del_asset),

        ("el suelo sin asset usa el color de respaldo",
         _el_suelo_sin_asset_no_rompe),

        ("la pantalla de game over esta registrada",
         "gameover" in juego.ESCENAS),

        ("la pantalla de iniciales esta registrada",
         "iniciales" in juego.ESCENAS),

        ("game over muestra el puntaje y pasa a las iniciales",
         _gameover_pasa_a_iniciales),

        ("ESC en game over vuelve al titulo sin guardar",
         _gameover_esc_vuelve_al_titulo),

        ("el choque guarda el puntaje y las personas superadas",
         _chocar_guarda_las_personas),

        # --- Iniciales
        ("las flechas cambian la letra y mueven el slot, dando la vuelta",
         _iniciales_por_flechas),

        ("el cursor de iniciales no se pasa de los bordes",
         _slot_no_se_pasa_del_borde),

        ("una letra de la A a la Z se escribe directo",
         _tipeo_directo),

        ("confirmar guarda la partida, regenera el HTML y abre el navegador",
         con_carpeta_temporal(_guardar_escribe_el_ranking)),

        ("ESC en las iniciales cancela y no guarda nada",
         con_carpeta_temporal(_esc_cancela_sin_guardar)),

        ("si el ranking no se puede escribir, se avisa y el juego sigue",
         con_carpeta_temporal(_error_al_guardar_no_rompe)),

        # --- Datos del ranking
        ("una linea bien formada se parsea campo por campo",
         _parsear),

        ("las lineas mal formadas se saltean con aviso",
         con_carpeta_temporal(_lineas_invalidas)),

        ("un ranking inexistente se crea vacio",
         con_carpeta_temporal(_archivo_inexistente)),

        ("agregar una partida nunca pisa las anteriores",
         con_carpeta_temporal(_agregar_es_append)),

        ("el ranking ordena por puntaje y desempata por fecha",
         con_carpeta_temporal(_orden_y_empates)),

        ("el top 10 recorta la lista sin reordenarla",
         con_carpeta_temporal(_top_recorta)),

        ("D cuenta las partidas del jugador y K/D usa un decimal",
         con_carpeta_temporal(_cuenta_y_ratio)),

        ("las iniciales y el equipo se normalizan a mayusculas",
         _iniciales_validas),

        ("lo que no son 3 letras se rechaza",
         _iniciales_invalidas),

        # --- Generacion del HTML
        ("el HTML tiene las columnas, el top 10, el CSS y el orden correcto",
         con_carpeta_temporal(_generar_html)),

        ("el HTML escapa el contenido de los datos",
         _generar_html_escapa),

        ("sin partidas el HTML se genera igual, con un aviso",
         con_carpeta_temporal(_generar_html_vacio)),
    ]


def main():
    total = 0
    falladas = 0

    for descripcion, comprobar in casos():
        total += 1
        # Se acepta la condicion ya calculada o una funcion que la arma en el
        # momento. Las funciones se necesitan cuando la prueba empieza de cero
        # con un personaje nuevo.
        if comprobar() if callable(comprobar) else comprobar:
            print(f"  OK     {descripcion}")
        else:
            print(f"  FALLA  {descripcion}")
            falladas += 1

    print()
    if falladas:
        print(f"Fallaron {falladas} de {total} pruebas.")
    else:
        print(f"Pasaron las {total} pruebas.")

    return 1 if falladas else 0


if __name__ == "__main__":
    raise SystemExit(main())
