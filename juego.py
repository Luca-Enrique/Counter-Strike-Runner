"""Counter-Strike: Runner.

Punto de entrada del juego. Acá se crea la ventana, corre el bucle principal y
se reparte el trabajo entre las escenas.

La logica esta dividida en cuatro partes:

1. funciones puras (calcular_escala, calcular_destino, recortar_delta), sin
   estado, se pueden verificar por separado sin abrir nada;
2. el Lienzo, que sabe mostrar la imagen virtual en la ventana real;
3. las escenas, una por pantalla, con la misma forma (eventos, actualizacion,
   dibujo) para que el bucle no sepa cual esta activa;
4. el Juego, que es el bucle: eventos, actualizacion y dibujo, en ese orden.

El personaje vive aparte, en personaje.py, porque tiene fisica y animacion
propias y no depende de ninguna escena. Los obstaculos viven aparte, en
obstaculo.py, por la misma razon.
"""
import random
import webbrowser

import pygame
import constantes
import fondo
import generar_ranking
import obstaculo
import personaje
import ranking

# --- Funciones puras -----------------------------------------------------
# No tocan pygame ni guardan estado: son las que se prueban en pruebas.py.

def calcular_escala(ancho_ventana, alto_ventana):
    """Devuelve el factor con el que la imagen virtual entra en la ventana.

    Se usa el menor de los dos factores. Con el mayor, la imagen se saldria
    de la ventana; con el menor entra completa y sobra un margen.
    """
    return min(ancho_ventana / constantes.ANCHO, alto_ventana / constantes.ALTO)

def recortar_delta(segundos):
    """Limita el tiempo entre fotogramas para que la fisica no se rompa."""
    return min(segundos, constantes.TOPE_DELTA)

def calcular_destino(ancho_ventana, alto_ventana):
    """Devuelve (x, y, ancho, alto): donde va la imagen virtual, ya escalada.

    La imagen entra completa y queda centrada, asi que lo que sobra de la
    ventana son las barras del letterbox.

    El tamano se redondea a pixeles enteros porque en pantalla no hay medios
    pixeles. Ademas asi un error de redondeo de la division no puede hacer que
    la imagen se pase por un pixel: con una ventana de 500 de ancho, 960 * 0.52
    da 500.00000000000006, y sin redondear la prueba "entra completa" fallaria
    por una fraccion de pixel.
    """
    escala = calcular_escala(ancho_ventana, alto_ventana)
    ancho = max(1, round(constantes.ANCHO * escala))
    alto = max(1, round(constantes.ALTO * escala))
    return (
        (ancho_ventana - ancho) // 2,
        (alto_ventana - alto) // 2,
        ancho,
        alto,
    )

def a_coordenadas_del_lienzo(posicion, tamano_ventana):
    """Convierte un punto de la ventana a la imagen virtual.

    El raton llega en pixeles de la ventana y las escenas dibujan sobre el
    lienzo virtual. Con el letterbox la ventana es mas grande y las coordenadas
    no coinciden, asi que se deshace el escalado y se corre el margen. Sin
    esto, en pantalla completa la mitad de la pantalla no cae donde parece y el
    click elige el equipo equivocado.
    """
    escala = calcular_escala(*tamano_ventana)
    x, y, _, _ = calcular_destino(*tamano_ventana)

    # Al minimizar, la ventana puede llegar a (0, 0). No hay mapeo posible.
    if escala <= 0:
        return posicion

    return (posicion[0] - x) / escala, (posicion[1] - y) / escala

def calcular_puntaje(segundos):
    """El puntaje son los segundos que llevas vivo, por diez.

    Los segundos se cortan a entero a proposito: si no, el numero cambiaria en
    cada fotograma y no se podria leer de un vistazo.
    """
    return int(segundos) * constantes.PUNTOS_POR_SEGUNDO

def zona_de_puntaje(puntaje):
    """El escenario que corresponde al puntaje.

    Son los mismos umbrales que usa la tematica para la progresion visual.
    """
    if puntaje >= constantes.UMBRAL_ZONA_AVANZADA:
        return "avanzada"
    if puntaje >= constantes.UMBRAL_ZONA_BOMBAS:
        return "bombas"
    if puntaje >= constantes.UMBRAL_ZONA_COMBATE:
        return "combate"
    return "inicial"

def _progreso_dificultad(puntaje):
    """Cuanto avanza la dificultad, de 0 a 1, al llegar a la zona avanzada."""
    return min(1.0, max(0.0, puntaje / constantes.UMBRAL_ZONA_AVANZADA))

def _interpolar(inicio, fin, progreso):
    """Un valor entre inicio y fin, segun el progreso de 0 a 1."""
    return inicio + (fin - inicio) * progreso

def velocidad_obstaculo(puntaje):
    """La velocidad de los obstaculos para ese puntaje, ya acotada."""
    return _interpolar(
        constantes.VELOCIDAD_OBSTACULO_MIN,
        constantes.VELOCIDAD_OBSTACULO_MAX,
        _progreso_dificultad(puntaje),
    )

def intervalo_obstaculo(puntaje):
    """Los segundos entre obstaculos para ese puntaje, ya acotados."""
    return _interpolar(
        constantes.INTERVALO_MIN,
        constantes.INTERVALO_MAX,
        _progreso_dificultad(puntaje),
    )

# --- Imagen virtual ------------------------------------------------------
class Lienzo:
    """La imagen virtual del juego y el modo de mostrarla en la ventana.

    El juego dibuja siempre sobre self.superficie, que tiene el tamano fijo
    de constantes.ANCHO x constantes.ALTO. Recien al terminar el fotograma esa
    imagen se escala para entrar en la ventana real.
    """
    def __init__(self):
        self.superficie = pygame.Surface((constantes.ANCHO, constantes.ALTO))

    def limpiar(self):
        """Pinta el fondo de un fotograma."""
        self.superficie.fill(constantes.COLOR_FONDO)

    def presentar(self, ventana):
        """Escala la imagen virtual y la pega centrada en la ventana."""
        ancho_ventana, alto_ventana = ventana.get_size()

        # Al minimizar en Windows llega un tamano de (0, 0) y no se puede
        # escalar a eso. No hay nada que dibujar hasta que vuelva a tener
        # tamano util.
        if ancho_ventana < 1 or alto_ventana < 1:
            return

        x, y, ancho, alto = calcular_destino(ancho_ventana, alto_ventana)
        imagen = pygame.transform.smoothscale(self.superficie, (ancho, alto))

        # Lo que sobra de la ventana queda negro: son las barras del
        # letterbox.
        ventana.fill(constantes.COLOR_BARRA)
        ventana.blit(imagen, (x, y))
        pygame.display.flip()

# --- Los dos equipos ------------------------------------------------------
# docs/TEMATICA.md pide que el jugador elija entre CT y T al empezar, y el
# equipo elegido es el campo 3 de ranking.txt.

EQUIPOS = ("CT", "T")

NOMBRES_DE_EQUIPO = {
    "CT": "COUNTER-TERRORIST",
    "T": "TERRORIST",
}

# Los mismos sprites que despues van a ser obstaculos, para que la eleccion
# muestre exactamente la misma cara que se va a ver jugando.
COLOR_DE_EQUIPO = {
    "CT": (86, 122, 164),
    "T": (196, 152, 84),
}

RUTA_PERSONA_OBSTACULO = "assets/obstaculos/persona_{}.png"


def cargar_retratos():
    """El retrato de cada equipo, sin escalar todavia.

    Si falta el archivo devuelve None para ese equipo, y la pantalla lo dibuja
    como un rectangulo de color. La seleccion tiene que poder verse siempre.
    """
    retratos = {}
    for equipo in EQUIPOS:
        retratos[equipo] = personaje.cargar_textura_original(
            RUTA_PERSONA_OBSTACULO.format(equipo.lower())
        )
    return retratos


# --- Textos --------------------------------------------------------------
def cargar_fuentes():
    """Crea las fuentes del juego.

    Por ahora usa la fuente que trae pygame, asi que no hace falta ningun
    archivo. Cuando se agreguen fuentes de internet, este es el unico lugar
    que hay que tocar.
    """
    pygame.font.init()
    return {
        "titulo": pygame.font.Font(None, constantes.TAMANO_FUENTE_TITULO),
        "medio": pygame.font.Font(None, constantes.TAMANO_FUENTE_MEDIO),
        "puntaje": pygame.font.Font(None, constantes.TAMANO_FUENTE_PUNTAJE),
        "etiqueta": pygame.font.Font(None, constantes.TAMANO_FUENTE_ETIQUETA),
        "slot": pygame.font.Font(None, constantes.TAMANO_FUENTE_SLOT),
    }

def dibujar_texto(superficie, cadena, fuente, color, posicion):
    """Escribe un texto con la esquina superior izquierda en `posicion`."""
    superficie.blit(fuente.render(cadena, True, color), posicion)

def dibujar_texto_centrado(superficie, cadena, fuente, color, y):
    """Escribe un texto centrado horizontalmente, a la altura `y`."""
    dibujar_texto_centrado_en(
        superficie, cadena, fuente, color, superficie.get_width() // 2, y
    )

def dibujar_texto_centrado_en(superficie, cadena, fuente, color, centro_x, y):
    """Escribe un texto centrado en `centro_x`, a la altura `y`.

    Sirve para centrar cada texto en su propio sitio y no todos en el medio de
    la pantalla, que es lo que hacia que los nombres de los equipos se pisaran.
    """
    imagen = fuente.render(cadena, True, color)
    superficie.blit(imagen, imagen.get_rect(center=(centro_x, y)))

def dibujar_texto_con_sombra(superficie, cadena, fuente, color, centro_x, y,
                            desplazamiento=2):
    """Un texto centrado con una sombra oscura debajo, para darle peso.

    Se dibuja dos veces: primero la copia negra corrida unos pixeles y despues
    el texto de color encima. Es lo que hace que el titulo grande no se vea
    plano sobre el fondo.
    """
    sombra = fuente.render(cadena, True, (0, 0, 0))
    principal = fuente.render(cadena, True, color)
    centro = (centro_x, y)
    superficie.blit(sombra, sombra.get_rect(center=(centro_x + desplazamiento,
                                                    y + desplazamiento)))
    superficie.blit(principal, principal.get_rect(center=centro))

def dibujar_panel(superficie, rect, relleno=constantes.COLOR_PANEL,
                  borde=constantes.COLOR_PANEL_BORDE,
                  alfa=constantes.ALFA_PANEL,
                  grosor=constantes.GROSOR_BORDE_PANEL):
    """Un panel semitransparente con marco, para agrupar el contenido.

    El relleno lleva alfa para dejar ver el fondo de atras; el borde va opaco
    para que el marco quede nitido. Sin esto las pantallas de fin de partida
    quedaban flotando sobre el negro.
    """
    capa = pygame.Surface(rect.size, pygame.SRCALPHA)
    capa.fill((*relleno, alfa))
    superficie.blit(capa, rect.topleft)
    pygame.draw.rect(superficie, borde, rect, grosor)

def dibujar_triangulo(superficie, centro, hacia_arriba, alto, color):
    """Una flecha triangular. Se dibuja, no se depende de un glifo de fuente."""
    ancho = alto
    if hacia_arriba:
        puntos = [
            (centro[0], centro[1] - alto),
            (centro[0] - ancho, centro[1] + alto // 2),
            (centro[0] + ancho, centro[1] + alto // 2),
        ]
    else:
        puntos = [
            (centro[0], centro[1] + alto),
            (centro[0] - ancho, centro[1] - alto // 2),
            (centro[0] + ancho, centro[1] - alto // 2),
        ]
    pygame.draw.polygon(superficie, color, puntos)

def _parpadea(tiempo, periodo=constantes.SEGUNDOS_PARPADEO):
    """True la mitad de cada periodo. Sirve para avisos y flechas que pulsan."""
    return (tiempo % (periodo * 2)) < periodo

# --- Escenas -------------------------------------------------------------
class Escena:
    """Base de todas las escenas.

    Cada escena responde a lo mismo, asi que el bucle no necesita saber que
    hay en pantalla. Los metodos vacios se pisan solo con lo que la escena
    necesite.
    """

    def __init__(self, juego):
        self.juego = juego

    def inicializar(self):
        """Se llama una vez, justo despues de crear la escena."""

    def manejar_eventos(self, evento):
        """Reacciona a un evento de pygame."""

    def actualizar(self, delta):
        """Avanza la escena. `delta` son segundos, ya recortados."""

    def dibujar(self, superficie):
        """Pinta la escena en la imagen virtual."""

class EscenaTitulo(Escena):
    """Pantalla de inicio. Es la que se ve al abrir el juego.

    Muestra el titulo sobre los escenarios del juego, que van avanzando de
    derecha a izquierda como una muestra. Los controles y la eleccion de
    personaje van en la pantalla siguiente.
    """

    def __init__(self, juego):
        super().__init__(juego)
        self.fondo = None
        self.suelo = None
        self.tiempo = 0.0

    def inicializar(self):
        self.fondo = fondo.Fondo()
        self.suelo = fondo.Suelo()
        self.tiempo = 0.0

    def manejar_eventos(self, evento):
        if evento.type != pygame.KEYDOWN:
            return

        if evento.key in (pygame.K_SPACE, pygame.K_RETURN):
            self.juego.cambiar_escena("equipo")
        elif evento.key == pygame.K_ESCAPE:
            self.juego.salir()

    def actualizar(self, delta):
        self.tiempo += delta
        if self.fondo is not None:
            self.fondo.actualizar(delta)
        if self.suelo is not None:
            self.suelo.actualizar(delta)

    def dibujar(self, superficie):
        if self.fondo is not None:
            self.fondo.dibujar(superficie)
        if self.suelo is not None:
            self.suelo.dibujar(superficie)

        panel = pygame.Rect(180, 150, 600, 230)
        dibujar_panel(superficie, panel)

        centro_x = panel.centerx
        dibujar_texto_con_sombra(
            superficie,
            constantes.TITULO_VENTANA,
            self.juego.fuentes["titulo"],
            constantes.COLOR_TEXTO,
            centro_x,
            panel.y + 72,
        )
        pygame.draw.line(
            superficie,
            constantes.COLOR_ACENTO,
            (panel.x + 80, panel.y + 112),
            (panel.right - 80, panel.y + 112),
            2,
        )

        if _parpadea(self.tiempo):
            dibujar_texto_centrado_en(
                superficie,
                "APRETÁ ESPACIO PARA INSERTAR UNA MONEDA",
                self.juego.fuentes["medio"],
                constantes.COLOR_ACENTO,
                centro_x,
                panel.y + 154,
            )

        dibujar_texto_centrado_en(
            superficie,
            "SPACE/ENTER: JUGAR   ·   ESC: SALIR",
            self.juego.fuentes["etiqueta"],
            constantes.COLOR_LETRA_INACTIVA,
            centro_x,
            panel.bottom - 28,
        )

class EscenaEquipo(Escena):
    """Pantalla de eleccion de personaje: CT o T.

    Los dos quedan a la vista sobre el mismo fondo del titulo. El equipo
    resaltado es el que se va a elegir: se mueve con A/D, con las flechas o con
    el raton (lo que se apunta), y se confirma con SPACE, ENTER o el click
    izquierdo. El equipo elegido queda en juego.equipo, que despues lo lee la
    escena de partida para cargar los sprites y lo usara el ranking.
    """

    def __init__(self, juego):
        super().__init__(juego)
        self.retratos = {}
        self.fondo = None
        self.suelo = None
        self.resaltado = EQUIPOS[0]
        self.tiempo = 0.0

    def inicializar(self):
        self.fondo = fondo.Fondo()
        self.suelo = fondo.Suelo()
        self.tiempo = 0.0
        if not self.juego.retratos_equipo:
            self.juego.retratos_equipo = cargar_retratos()

    def manejar_eventos(self, evento):
        if evento.type == pygame.KEYDOWN:
            self._tecla(evento.key)
        elif evento.type == pygame.MOUSEMOTION:
            self._apuntar_en_ventana(evento.pos)
        elif evento.type == pygame.MOUSEBUTTONDOWN:
            self._click(evento)

    def _tecla(self, key):
        if key == pygame.K_ESCAPE:
            self.juego.cambiar_escena("titulo")
        elif key in IZQUIERDA:
            self.resaltado = EQUIPOS[0]
        elif key in DERECHA:
            self.resaltado = EQUIPOS[-1]
        elif key in CONFIRMAR:
            self._elegir(self.resaltado)

    def _click(self, evento):
        # Solo el boton izquierdo: el derecho es el de agacharse en la partida.
        if evento.button != constantes.BOTON_IZQUIERDO:
            return
        self._apuntar_en_ventana(evento.pos)
        self._elegir(self.resaltado)

    def _apuntar_en_ventana(self, posicion):
        """Resalta el equipo de la mitad donde cae ese punto de la ventana."""
        x, _ = a_coordenadas_del_lienzo(
            posicion, self.juego.ventana.get_size()
        )
        self.resaltado = EQUIPOS[0] if x < constantes.ANCHO / 2 else EQUIPOS[-1]

    def _elegir(self, equipo):
        self.juego.equipo = equipo
        self.juego.cambiar_escena("juego")

    def actualizar(self, delta):
        self.tiempo += delta
        if self.fondo is not None:
            self.fondo.actualizar(delta)
        if self.suelo is not None:
            self.suelo.actualizar(delta)

    def dibujar(self, superficie):
        if self.fondo is not None:
            self.fondo.dibujar(superficie)
        if self.suelo is not None:
            self.suelo.dibujar(superficie)

        dibujar_texto_con_sombra(
            superficie,
            "SELECCIONÁ TU EQUIPO",
            self.juego.fuentes["medio"],
            constantes.COLOR_ACENTO,
            superficie.get_width() // 2,
            86,
        )
        pygame.draw.line(
            superficie,
            constantes.COLOR_ACENTO,
            (280, 112),
            (680, 112),
            2,
        )

        for indice, equipo in enumerate(EQUIPOS):
            self._dibujar_equipo(superficie, equipo, indice)

        dibujar_texto_con_sombra(
            superficie,
            "VS",
            self.juego.fuentes["titulo"],
            constantes.COLOR_ACENTO,
            superficie.get_width() // 2,
            270,
        )

        dibujar_texto_centrado_en(
            superficie,
            "A/D O FLECHAS: CAMBIAR   ·   SPACE/ENTER: CONFIRMAR   ·   ESC: VOLVER",
            self.juego.fuentes["etiqueta"],
            constantes.COLOR_LETRA_INACTIVA,
            superficie.get_width() // 2,
            constantes.ALTO - 36,
        )

    def _dibujar_equipo(self, superficie, equipo, indice):
        """Un equipo: su retrato y su nombre, centrados en su propia mitad.

        El panel resaltado lleva un anillo dorado, para que se vea cual se va a
        elegir tanto si se apunta con el raton como si se mueve con el teclado.
        """
        centro_x = constantes.ANCHO // 4 + indice * (constantes.ANCHO // 2)
        resaltado = equipo == self.resaltado

        caja = pygame.Rect(
            centro_x - constantes.ANCHO // 4 + 32,
            134,
            constantes.ANCHO // 2 - 64,
            276,
        )
        dibujar_panel(superficie, caja)
        if resaltado:
            pygame.draw.rect(superficie, constantes.COLOR_ACENTO, caja, 4)
            if _parpadea(self.tiempo):
                dibujar_triangulo(
                    superficie,
                    (caja.centerx, caja.top - 18),
                    True,
                    18,
                    constantes.COLOR_ACENTO,
                )
        else:
            pygame.draw.rect(superficie, constantes.COLOR_EQUIPO_BORDE, caja, 2)

        self._dibujar_retrato(superficie, equipo, caja)

        dibujar_texto_con_sombra(
            superficie,
            NOMBRES_DE_EQUIPO[equipo],
            self.juego.fuentes["medio"],
            COLOR_DE_EQUIPO[equipo],
            centro_x,
            442,
        )

    def _dibujar_retrato(self, superficie, equipo, caja):
        """El retrato del equipo, o un rectangulo de color si falta el archivo."""
        imagen = self._retrato_escalado(equipo, caja.h - 40)

        if imagen is None:
            pygame.draw.rect(
                superficie,
                COLOR_DE_EQUIPO[equipo],
                pygame.Rect(caja.x + 48, caja.y + 32, caja.w - 96, caja.h - 64),
            )
            return

        posicion = imagen.get_rect(center=caja.center)
        superficie.blit(imagen, posicion)

    def _retrato_escalado(self, equipo, alto):
        """El retrato del equipo a ese alto, usando el cache si ya estaba.

        El lienzo virtual es siempre de ANCHO x ALTO, asi que el alto pedido
        casi nunca cambia. Por eso se guarda el resultado y no se reescala en
        cada fotograma.
        """
        cacheado = self.retratos.get(equipo)
        if cacheado is not None and cacheado.get_height() == alto:
            return cacheado

        imagen = self.juego.retratos_equipo.get(equipo)
        if imagen is None:
            return None

        escalada = pygame.transform.smoothscale(
            imagen, (round(imagen.get_width() * alto / imagen.get_height()), alto)
        )
        self.retratos[equipo] = escalada
        return escalada

class EscenaJuego(Escena):
    """Escena de partida: fondo por zona, obstaculos, personaje y puntaje."""

    def __init__(self, juego):
        super().__init__(juego)
        self.puntaje = 0
        self.tiempo_vivido = 0.0
        self.personaje = None
        self.fondo = None
        self.suelo = None
        self.obstaculos = []
        self.tiempo_para_obstaculo = 0.0
        self.personas_superadas = 0
        self.terminada = False

        # Se puede reemplazar en las pruebas para que la aparicion sea
        # determinista.
        self.azar = random.Random()

        # El agachado se puede pedir con ABAJO o con el click derecho, y son
        # dos controles independientes. Se guardan por separado para que
        # soltar uno no levante al personaje si el otro sigue apretado.
        self.tecla_agacha = False
        self.raton_agacha = False

    def inicializar(self):
        """Carga los sprites y arma el personaje, el fondo y los obstaculos.

        Si faltan archivos, las imagenes quedan en None y todo se dibuja como
        rectangulos de color. El juego arranca igual.
        """
        texturas = personaje.cargar_texturas(self.juego.equipo)
        self.personaje = personaje.Personaje(
            texturas=personaje.recortar_agachado(texturas)
        )

        self.puntaje = 0
        self.tiempo_vivido = 0.0
        self.obstaculos = []
        self.personas_superadas = 0
        self.terminada = False
        self.fondo = fondo.Fondo(
            rotar=False, alfa=constantes.ALFA_OSCURECIDO_JUEGO
        )
        self.suelo = fondo.Suelo()
        self.tiempo_para_obstaculo = intervalo_obstaculo(0)

    def manejar_eventos(self, evento):
        if evento.type == pygame.QUIT:
            self.juego.salir()
        elif evento.type == pygame.VIDEORESIZE:
            self.juego.redimensionar(evento.size)
        elif evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
            self.juego.cambiar_escena("titulo")
        elif evento.type == pygame.KEYDOWN and evento.key in SALTAR:
            self.personaje.saltar()
        elif evento.type == pygame.KEYDOWN and evento.key in AGACHAR:
            self.tecla_agacha = True
            self.personaje.agachar(True)
        elif evento.type == pygame.KEYUP and evento.key in AGACHAR:
            self.tecla_agacha = False
            self.personaje.agachar(self.raton_agacha)
        elif evento.type == pygame.MOUSEBUTTONDOWN:
            self._boton(evento.button, True)
        elif evento.type == pygame.MOUSEBUTTONUP:
            self._boton(evento.button, False)

    def _boton(self, boton, presionado):
        """Un boton del raton: el izquierdo salta y el derecho agacha."""
        if boton == constantes.BOTON_IZQUIERDO:
            if presionado:
                self.personaje.saltar()
        elif boton == constantes.BOTON_DERECHO:
            self._fijar_agachado(presionado)

    def _fijar_agachado(self, del_raton):
        """Agacha o levanta segun el raton y la tecla, sinon los dos."""
        if del_raton:
            self.raton_agacha = True
        else:
            self.raton_agacha = False
        self.personaje.agachar(self.raton_agacha or self.tecla_agacha)

    def actualizar(self, delta):
        if self.terminada:
            return

        self.tiempo_vivido += delta
        self.puntaje = calcular_puntaje(self.tiempo_vivido)
        self.personaje.actualizar(delta)

        self._actualizar_fondo(delta)
        self._actualizar_obstaculos(delta)

        if self._choca():
            self._terminar()

    def _actualizar_fondo(self, delta):
        """Elige el escenario de la zona y mueve el fondo y el suelo."""
        velocidad = velocidad_obstaculo(self.puntaje)

        if self.fondo is not None:
            self.fondo.cambiar_escenario(zona_de_puntaje(self.puntaje))
            self.fondo.velocidad = velocidad * constantes.FACTOR_PARALLAX_FONDO
            self.fondo.actualizar(delta)

        if self.suelo is not None:
            self.suelo.velocidad = velocidad * constantes.FACTOR_PARALLAX_SUELO
            self.suelo.actualizar(delta)

    def _actualizar_obstaculos(self, delta):
        velocidad = velocidad_obstaculo(self.puntaje)

        self.tiempo_para_obstaculo -= delta
        while self.tiempo_para_obstaculo <= 0:
            self._generar_obstaculo()
            self.tiempo_para_obstaculo += intervalo_obstaculo(self.puntaje)

        for cada_uno in self.obstaculos:
            cada_uno.actualizar(delta, velocidad)

            if (
                cada_uno.tipo == "persona"
                and not cada_uno.contada
                and cada_uno.paso_al_jugador(self.personaje.rect.left)
            ):
                cada_uno.contada = True
                self.personas_superadas += 1

        self.obstaculos = [
            cada_uno
            for cada_uno in self.obstaculos
            if not cada_uno.fuera_de_pantalla()
        ]

    def _generar_obstaculo(self, tipo=None):
        """Crea un obstaculo en el borde derecho y lo suma a la lista."""
        tipo = tipo or self._elegir_tipo()
        self.obstaculos.append(
            obstaculo.Obstaculo(tipo, self.juego.equipo, constantes.ANCHO)
        )

    def _elegir_tipo(self):
        """Un tipo al azar. Las pruebas lo reemplazan por uno fijo."""
        return self.azar.choice(obstaculo.TIPOS)

    def _choca(self):
        """True si algun obstaculo se superpone con el personaje."""
        return any(
            cada_uno.colisiona(self.personaje.rect)
            for cada_uno in self.obstaculos
        )

    def _terminar(self):
        """Termina la partida y guarda el resultado para la pantalla siguiente.

        Son los campos 2 y 5 de ranking.txt: el puntaje y las personas
        superadas. La escena de iniciales los escribe recien al confirmar.
        """
        self.terminada = True
        self.juego.ultimo_puntaje = self.puntaje
        self.juego.ultimas_personas = self.personas_superadas
        self.juego.cambiar_escena("gameover")

    def dibujar(self, superficie):
        if self.fondo is not None:
            self.fondo.dibujar(superficie)

        if self.suelo is not None:
            self.suelo.dibujar(superficie)

        for cada_uno in self.obstaculos:
            cada_uno.dibujar(superficie)

        self.personaje.dibujar(superficie)

        dibujar_texto(
            superficie,
            f"SCORE: {self.puntaje}",
            self.juego.fuentes["puntaje"],
            constantes.COLOR_TEXTO,
            (20, 20),
        )


class EscenaGameOver(Escena):
    def __init__(self, juego):
        super().__init__(juego)
        self.fondo = None
        self.frase = None
        self.tiempo = 0.0

    def inicializar(self):
        self.fondo = fondo.Fondo(rotar=False)
        self.fondo.cambiar_escenario(constantes.ESCENARIO_GAMEOVER)
        if constantes.FRASES_GAMEOVER:
            self.frase = random.choice(constantes.FRASES_GAMEOVER)
        else:
            self.frase = None
        self.tiempo = 0.0

    def actualizar(self, delta):
        self.tiempo += delta
        if self.fondo is not None:
            self.fondo.actualizar(delta)

    def manejar_eventos(self, evento):
        if evento.type == pygame.QUIT:
            self.juego.salir()
        elif evento.type == pygame.VIDEORESIZE:
            self.juego.redimensionar(evento.size)
        elif evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
            self.juego.cambiar_escena("titulo")
        elif evento.type == pygame.KEYDOWN and evento.key in CONFIRMAR:
            self.juego.cambiar_escena("iniciales")
        elif (
            evento.type == pygame.MOUSEBUTTONDOWN
            and evento.button == constantes.BOTON_IZQUIERDO
        ):
            self.juego.cambiar_escena("iniciales")

    def dibujar(self, superficie):
        if self.fondo is not None:
            self.fondo.dibujar(superficie)

        panel = pygame.Rect(constantes.GAMEOVER_PANEL)
        dibujar_panel(superficie, panel)

        centro_x = panel.centerx
        dibujar_texto_con_sombra(
            superficie,
            "GAME OVER",
            self.juego.fuentes["titulo"],
            constantes.COLOR_ACENTO,
            centro_x,
            panel.y + 58,
        )

        if self.frase:
            dibujar_texto_centrado_en(
                superficie,
                self.frase,
                self.juego.fuentes["puntaje"],
                constantes.COLOR_TEXTO,
                centro_x,
                panel.y + 108,
            )

        dibujar_texto_centrado_en(
            superficie,
            "SCORE",
            self.juego.fuentes["etiqueta"],
            constantes.COLOR_TEXTO,
            centro_x,
            panel.y + 144,
        )
        dibujar_texto_con_sombra(
            superficie,
            f"{self.juego.ultimo_puntaje}",
            self.juego.fuentes["titulo"],
            constantes.COLOR_ACENTO,
            centro_x,
            panel.y + 190,
            desplazamiento=3,
        )

        if _parpadea(self.tiempo):
            dibujar_texto_centrado_en(
                superficie,
                "PRESIONA ESPACIO PARA INGRESAR TUS INICIALES",
                self.juego.fuentes["etiqueta"],
                constantes.COLOR_TEXTO,
                centro_x,
                panel.bottom + 26,
            )


class EscenaIniciales(Escena):
    """Ingreso de las iniciales, al estilo de las recreativas.

    Usa el fondo animado, un panel central, casilleros con flechas y
    parpadeo. Al confirmar se escribe la partida en ranking.txt, se regenera
    ranking.html y se abre en el navegador una sola vez por partida.
    """

    def __init__(self, juego):
        super().__init__(juego)
        self.letras = ["A", "A", "A"]
        self.slot = 0
        self.error = None
        self.guardado = False
        self.fondo = None
        self.tiempo = 0.0

    def inicializar(self):
        self.fondo = fondo.Fondo()
        self.tiempo = 0.0
        self.error = None
        self.guardado = False
        self.letras = ["A", "A", "A"]
        self.slot = 0

    def actualizar(self, delta):
        self.tiempo += delta
        if self.fondo is not None:
            self.fondo.actualizar(delta)

    def _letra_actual(self):
        return self.letras[self.slot]

    def _cambiar_letra(self, paso):
        """Pasa a la letra anterior o siguiente, dando la vuelta."""
        indice = (ranking.ALFABETO.index(self._letra_actual()) + paso)
        self.letras[self.slot] = ranking.ALFABETO[indice % len(ranking.ALFABETO)]
        self.error = None

    def _escribir(self, key):
        """Escribe una letra directo si la tecla es de la A a la Z."""
        letra = chr(key).upper()
        if letra in ranking.ALFABETO:
            self.letras[self.slot] = letra
            if self.slot < len(self.letras) - 1:
                self.slot += 1
            self.error = None
            return True
        return False

    def manejar_eventos(self, evento):
        if evento.type == pygame.QUIT:
            self.juego.salir()
            return
        if evento.type == pygame.VIDEORESIZE:
            self.juego.redimensionar(evento.size)
            return
        if evento.type != pygame.KEYDOWN:
            return

        if evento.key == pygame.K_ESCAPE:
            self.juego.cambiar_escena("titulo")
        elif self.guardado and evento.key in CONFIRMAR:
            self.juego.cambiar_escena("titulo")
        elif evento.key in CONFIRMAR:
            self._guardar()
        elif evento.key in (pygame.K_UP, pygame.K_w):
            self._cambiar_letra(1)
        elif evento.key in (pygame.K_DOWN, pygame.K_s):
            self._cambiar_letra(-1)
        elif evento.key in IZQUIERDA:
            self._cambiar_slot(-1)
        elif evento.key in DERECHA:
            self._cambiar_slot(1)
        elif evento.key == pygame.K_BACKSPACE:
            self._cambiar_slot(-1)
        elif pygame.K_a <= evento.key <= pygame.K_z:
            self._escribir(evento.key)

    def _cambiar_slot(self, paso):
        """Mueve el cursor sin pasarse de los bordes."""
        self.slot = min(len(self.letras) - 1, max(0, self.slot + paso))

    def _guardar(self):
        """Escribe la partida, regenera el HTML y abre el navegador.

        Si algo falla, el juego no se cae: queda el aviso en pantalla y se
        puede volver al titulo con ENTER.
        """
        iniciales = "".join(self.letras)
        try:
            ranking.agregar_partida(
                self.juego.ruta_ranking,
                iniciales,
                self.juego.ultimo_puntaje,
                self.juego.equipo,
                self.juego.ultimas_personas,
            )
            generar_ranking.generar_html(
                self.juego.ruta_ranking, self.juego.ruta_ranking_html
            )
        except OSError as error:
            self.error = str(error)
            return

        self.guardado = True
        self.juego.abrir_ranking()

    def dibujar(self, superficie):
        if self.fondo is not None:
            self.fondo.dibujar(superficie)

        panel = pygame.Rect(constantes.INICIALES_PANEL)
        dibujar_panel(superficie, panel)

        centro_x = panel.centerx
        dibujar_texto_con_sombra(
            superficie,
            "INGRESA TUS INICIALES",
            self.juego.fuentes["medio"],
            constantes.COLOR_ACENTO,
            centro_x,
            panel.y + 36,
        )
        dibujar_texto_centrado_en(
            superficie,
            f"SCORE: {self.juego.ultimo_puntaje}",
            self.juego.fuentes["etiqueta"],
            constantes.COLOR_TEXTO,
            centro_x,
            panel.y + 70,
        )

        self._dibujar_slots(superficie, panel)

        aviso, color = self._texto_de_ayuda()
        if _parpadea(self.tiempo) or self.error is not None or self.guardado:
            dibujar_texto_centrado_en(
                superficie,
                aviso,
                self.juego.fuentes["etiqueta"],
                color,
                panel.centerx,
                panel.bottom - 26,
            )

    def _dibujar_slots(self, superficie, panel):
        """Los tres casilleros, con flechas sobre el slot apuntado."""
        ancho = constantes.ANCHO_SLOT_INICIALES
        centro_x = panel.centerx
        inicio = centro_x - (ancho * len(self.letras)) // 2
        centro_y = panel.centery + 10

        for indice, letra in enumerate(self.letras):
            apuntado = indice == self.slot
            caja = pygame.Rect(inicio + indice * ancho + 8, centro_y - 52, ancho - 16, 104)
            relleno = constantes.COLOR_ACENTO if apuntado else constantes.COLOR_EQUIPO_ELEGIDO
            alfa = 160 if apuntado else 90
            capa = pygame.Surface(caja.size, pygame.SRCALPHA)
            capa.fill((*relleno, alfa))
            superficie.blit(capa, caja.topleft)
            pygame.draw.rect(
                superficie,
                constantes.COLOR_ACENTO if apuntado else constantes.COLOR_EQUIPO_BORDE,
                caja,
                4 if apuntado else 2,
            )

            if apuntado:
                if _parpadea(self.tiempo):
                    dibujar_triangulo(
                        superficie,
                        (caja.centerx, caja.top - 16),
                        True,
                        constantes.ALTO_FLECHA_INICIALES,
                        constantes.COLOR_ACENTO,
                    )
                    dibujar_triangulo(
                        superficie,
                        (caja.centerx, caja.bottom + 16),
                        False,
                        constantes.ALTO_FLECHA_INICIALES,
                        constantes.COLOR_ACENTO,
                    )
                fuente = self.juego.fuentes["slot"]
                color = constantes.COLOR_TEXTO
            else:
                fuente = self.juego.fuentes["slot"]
                color = constantes.COLOR_LETRA_INACTIVA

            dibujar_texto_centrado_en(
                superficie, letra, fuente, color, caja.centerx, caja.centery
            )

    def _texto_de_ayuda(self):
        """El aviso de abajo y su color, segun lo que acaba de pasar."""
        if self.error is not None:
            error = str(self.error)
            if len(error) > 80:
                error = error[:77] + "..."
            return f"ERROR AL GUARDAR: {error}", constantes.COLOR_ERROR
        if self.guardado:
            return "RANKING GUARDADO Y ABIERTO. ENTER PARA SEGUIR", (
                constantes.COLOR_ACENTO
            )
        return "FLECHAS: ELEGIR   ENTER: CONFIRMAR   ESC: SALIR", (
            constantes.COLOR_TEXTO
        )


ESCENAS = {
    "titulo": EscenaTitulo,
    "equipo": EscenaEquipo,
    "juego": EscenaJuego,
    "gameover": EscenaGameOver,
    "iniciales": EscenaIniciales,
}

# Los controles de docs/TEMATICA.md:
#   SPACE / ARRIBA / W / CLICK IZQ -> SALTAR
#   ABAJO / S / CLICK DER          -> AGACHARSE
SALTAR = (pygame.K_SPACE, pygame.K_UP, pygame.K_w)
AGACHAR = (pygame.K_DOWN, pygame.K_s)

# En la eleccion de personaje: A/D y las flechas mueven el resaltado, y
# SPACE/ENTER o el click izquierdo confirman.
IZQUIERDA = (pygame.K_a, pygame.K_LEFT)
DERECHA = (pygame.K_d, pygame.K_RIGHT)
CONFIRMAR = (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER)

# --- Bucle principal -----------------------------------------------------
def crear_ventana():
    """Abre la ventana, del tamano del lienzo virtual y redimensionable."""
    ventana = pygame.display.set_mode(
        (constantes.ANCHO, constantes.ALTO), pygame.RESIZABLE
    )
    pygame.display.set_caption(constantes.TITULO_VENTANA)
    return ventana

class Juego:
    """El juego: ventana, bucle y escena activa."""

    def __init__(self):
        self.ventana = crear_ventana()
        self.lienzo = Lienzo()
        self.fuentes = cargar_fuentes()
        # Las imagenes de los retratos. Se dejan en un Surface vacio para que
        # cambien de tamano al redimensionar sin volver a leer los archivos.
        self.retratos = pygame.Surface((1, 1))
        self.retratos_equipo = {}
        self.reloj = pygame.time.Clock()
        self.corriendo = True

        # El equipo que elige el jugador. Es el campo 3 de ranking.txt, asi que
        # se guarda aqui y no se vuelve a preguntar.
        self.equipo = "CT"

        # El puntaje de la ultima partida, para que la pantalla de game over lo
        # muestre sin tener que guardar la escena anterior.
        self.ultimo_puntaje = 0

        # Las personas superadas en la ultima partida. Es el campo 5 de
        # ranking.txt y lo escribe la escena de iniciales al confirmar.
        self.ultimas_personas = 0

        # Rutas del ranking y como abrirlo. Se guardan como atributos para que
        # las pruebas puedan apuntarlas a una carpeta temporal y para no tener
        # el lanzamiento del navegador escondido dentro de la escena.
        self.ruta_ranking = ranking.RUTA_RANKING
        self.ruta_ranking_html = ranking.RUTA_RANKING.with_name("ranking.html")
        self.abrir_navegador = webbrowser.open

        self.cambiar_escena("titulo")

    def abrir_ranking(self):
        """Muestra ranking.html en el navegador. Un error no corta el juego."""
        try:
            self.abrir_navegador(self.ruta_ranking_html.resolve().as_uri())
        except OSError:
            pass

    def cambiar_escena(self, nombre):
        """Reemplaza la escena activa por la que pide el nombre dado."""
        self.escena = ESCENAS[nombre](self)
        self.escena.inicializar()

    def salir(self):
        """Pide que termine el bucle."""
        self.corriendo = False

    def manejar_eventos(self):
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                self.salir()
            elif evento.type == pygame.VIDEORESIZE:
                self.redimensionar(evento.size)
            else:
                self.escena.manejar_eventos(evento)

    def redimensionar(self, tamano):
        """Ajusta la ventana al tamano pedido por el sistema.

        Al minimizar en Windows llega (0, 0) y set_mode no acepta ese valor,
        asi que se fuerza al menos 1 pixel.
        """
        ancho = max(tamano[0], 1)
        alto = max(tamano[1], 1)
        self.ventana = pygame.display.set_mode((ancho, alto), pygame.RESIZABLE)

    def actualizar(self, delta):
        self.escena.actualizar(delta)

    def dibujar(self):
        self.lienzo.limpiar()
        self.escena.dibujar(self.lienzo.superficie)
        self.lienzo.presentar(self.ventana)

    def bucle(self):
        while self.corriendo:
            # clock.tick devuelve milisegundos. Se pasan a segundos para que
            # toda la fisica se exprese en pixeles por segundo.
            delta = recortar_delta(self.reloj.tick(constantes.FPS) / 1000.0)
            self.manejar_eventos()
            self.actualizar(delta)
            self.dibujar()

        pygame.quit()

def main():
    pygame.init()
    Juego().bucle()

if __name__ == "__main__":
    main()
