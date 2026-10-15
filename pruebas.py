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

# Tiene que estar antes de importar juego, para que las pruebas corran tambien
# en una maquina sin pantalla (un servidor de integracion continua, por
# ejemplo). setdefault no pisa la variable si ya estaba puesta.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

import constantes
import juego
import personaje


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


def juego_stub():
    """Un Juego stub: solo lo que necesitan las escenas para probarse.

    No abre ventana. Las escenas solo necesitan las fuentes, los retratos y un
    sitio donde anotar el cambio de escena. Los eventos se escriben a mano.
    """
    class JuegoStub:
        fuentes = juego.cargar_fuentes()
        lienzo = juego.Lienzo()

        def __init__(self):
            self.cambio_de_escena = None
            self.equipo = "CT"
            self.retratos_equipo = {}

        def cambiar_escena(self, nombre):
            self.cambio_de_escena = nombre

        def salir(self):
            pass

    return JuegoStub()


def escena_de_juego():
    """Una EscenaJuego con el equipo pedido."""
    stub = juego_stub()
    stub.equipo = EQUIPO_DE_PRUEBA
    escena = juego.EscenaJuego(stub)
    escena.inicializar()
    return escena


def escena_de_equipo():
    """Una EscenaEquipo con el juego stub."""
    escena = juego.EscenaEquipo(juego_stub())
    escena.inicializar()
    return escena


def tecla(tipo, key):
    return pygame.event.Event(tipo, key=key)


def boton(tipo, numero, posicion=None):
    return pygame.event.Event(tipo, button=numero, pos=posicion or (0, 0))


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

    El de agachar se recorta, asi que su ancho es el del fotograma de correr mas
    ancho. No puede pasar de ese: un dibujo mas ancho que la hitbox golpearia
    obstaculos que no se ven.
    """
    for equipo in ("CT", "T"):
        texturas = _texturas(equipo)
        ancho_hitbox = max(f.get_width() for f in texturas["correr"])
        for f in texturas["agacharse"]:
            if f.get_width() > ancho_hitbox:
                return False
    return True


def _agachado_no_se_deforma():
    """Agachar recorta el torso, pero no deforma la imagen.

    Este es el bug que se quiere evitar. El sprite de agachar es un personaje
    parado encogido: si se escalara a 56 px de alto, su proporcion lo dejaria
    angosto y se veria como que el personaje se achica. La solucion fue estirarlo
    en horizontal, pero deformarlo 1.72 veces quedaba peor.

    Ahora se recorta: se muestran los 56 pixeles de arriba del fotograma de
    correr, sin reescalar nada. La comprobacion es que el ancho del agachado sea
    EXACTAMENTE el del fotograma de correr mas ancho: si el recorte volviera a
    escalar, el ancho seria distinto y esta prueba caeria.
    """
    for equipo in ("CT", "T"):
        texturas = _texturas(equipo)
        ancho_correr = max(f.get_width() for f in texturas["correr"])

        for f in texturas["agacharse"]:
            if f.get_width() != ancho_correr:
                return False
    return True


def _agachado_es_el_torso_del_equipo():
    """El agachado sale de recortar el equipo pedido, no de cualquier otro.

    Si el recorte usara siempre el torso de CT, jugar con T veria al personaje
    de CT agachado.
    """
    for equipo in ("CT", "T"):
        texturas = _texturas(equipo)
        referencia = max(texturas["correr"], key=lambda f: f.get_width())
        recorte = texturas["agacharse"][0]

        # El recorte tiene que ser el pedazo de arriba de la imagen de correr.
        if recorte.get_size() != (
            referencia.get_width(),
            constantes.ALTO_PERSONAJE_AGACHADO,
        ):
            return False

        if recorte.get_at((recorte.get_width() // 2, 0)) != referencia.get_at(
            (referencia.get_width() // 2, 0)
        ):
            return False   # el pixel de arriba no es el del equipo
    return True


def _agachado_conserva_su_alto():
    """El recorte del agachado tiene que dar exactamente los 56 px de alto.

    Ese alto es el que hace pasar al personaje por debajo de un obstaculo alto.
    """
    for equipo in ("CT", "T"):
        if _texturas(equipo)["agacharse"][0].get_height() != constantes.ALTO_PERSONAJE_AGACHADO:
            return False
    return True
    for equipo in ("CT", "T"):
        if _texturas(equipo)["agacharse"][0].get_height() != constantes.ALTO_PERSONAJE_AGACHADO:
            return False
    return True


def _todos_los_fotogramas_iguales():
    """Todos los fotogramas de correr tienen la misma altura.

    El ancho NO se comprueba: los seis anchos difieren entre si (de 84 a 93 px),
    asi que el personaje se veria respirar si se escalaran al mismo ancho. Lo
    que se hace es dejar que cada fotograma conserve su proporcion dentro de un
    rectangulo de ancho comun.

    El alto si tiene que ser igual: si un fotograma quedara mas alto, al pasar
    al siguiente el personaje saltaria de alto.
    """
    for equipo in ("CT", "T"):
        altos = {f.get_height() for f in _texturas(equipo)["correr"]}
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
            for y in (344, 346, 348, 350)
            for x in range(0, constantes.ANCHO, 2)
        ):
            return False
    return True


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


def _ancho_de_correr_del_equipo(equipo):
    """El ancho del primer fotograma de correr con el que arranca la partida."""
    stub = juego_stub()
    stub.equipo = equipo
    escena = juego.EscenaJuego(stub)
    escena.inicializar()
    return escena.personaje.texturas["correr"][0].get_width()


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

        ("agachar recorta el torso: el ancho es EXACTAMENTE el de correr (no deforma)",
         _agachado_no_se_deforma()),

        ("el recorte de agachar sale del equipo pedido, no del otro",
         _agachado_es_el_torso_del_equipo()),

        ("el sprite de agachar conserva los 56 px de alto al recortarse",
         _agachado_conserva_su_alto()),

        ("el sprite de agachar nunca se dibuja mas ancho que la hitbox",
         _agachado_entra_en_la_hitbox()),

        ("los seis fotogramas de correr tienen la misma altura (el ancho varia, a proposito)",
         _todos_los_fotogramas_iguales()),

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
         _ancho_de_correr_del_equipo("CT") != _ancho_de_correr_del_equipo("T")),

        ("la eleccion dibuja los dos retratos y los dos nombres",
         _dibuja_los_dos_equipos()),

        ("la eleccion dibuja aunque falten los retratos",
         _dibuja_sin_retratos()),
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
