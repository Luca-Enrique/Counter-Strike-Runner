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
propias y no depende de ninguna escena.
"""
import pygame
import constantes
import fondo
import personaje

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

def calcular_puntaje(segundos):
    """El puntaje son los segundos que llevas vivo, por diez.

    Los segundos se cortan a entero a proposito: si no, el numero cambiaria en
    cada fotograma y no se podria leer de un vistazo.
    """
    return int(segundos) * constantes.PUNTOS_POR_SEGUNDO

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

    def inicializar(self):
        self.fondo = fondo.Fondo()

    def manejar_eventos(self, evento):
        if evento.type != pygame.KEYDOWN:
            return

        if evento.key in (pygame.K_SPACE, pygame.K_RETURN):
            self.juego.cambiar_escena("equipo")
        elif evento.key == pygame.K_ESCAPE:
            self.juego.salir()

    def actualizar(self, delta):
        if self.fondo is not None:
            self.fondo.actualizar(delta)

    def dibujar(self, superficie):
        if self.fondo is not None:
            self.fondo.dibujar(superficie)

        dibujar_texto_centrado(
            superficie, constantes.TITULO_VENTANA,
            self.juego.fuentes["titulo"], constantes.COLOR_TEXTO, 240,
        )
        dibujar_texto_centrado(
            superficie, "Apretá espacio para insertar una moneda",
            self.juego.fuentes["medio"], constantes.COLOR_ACENTO, 330,
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
        self.resaltado = EQUIPOS[0]

    def inicializar(self):
        self.fondo = fondo.Fondo()
        if not self.juego.retratos_equipo:
            self.juego.retratos_equipo = cargar_retratos()

    def manejar_eventos(self, evento):
        if evento.type == pygame.KEYDOWN:
            self._tecla(evento.key)
        elif evento.type == pygame.MOUSEMOTION:
            self._apuntar(evento.pos[0])
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
        self._apuntar(evento.pos[0])
        self._elegir(self.resaltado)

    def _apuntar(self, x):
        """Resalta el equipo de la mitad donde esta `x`."""
        self.resaltado = EQUIPOS[0] if x < constantes.ANCHO / 2 else EQUIPOS[-1]

    def _elegir(self, equipo):
        self.juego.equipo = equipo
        self.juego.cambiar_escena("juego")

    def actualizar(self, delta):
        if self.fondo is not None:
            self.fondo.actualizar(delta)

    def dibujar(self, superficie):
        if self.fondo is not None:
            self.fondo.dibujar(superficie)

        dibujar_texto_centrado(
            superficie, "ELEGI TU PERSONAJE",
            self.juego.fuentes["medio"], constantes.COLOR_ACENTO, 90,
        )

        for indice, equipo in enumerate(EQUIPOS):
            self._dibujar_equipo(superficie, equipo, indice)

    def _dibujar_equipo(self, superficie, equipo, indice):
        """Un equipo: su retrato y su nombre, centrados en su propia mitad.

        El panel resaltado lleva un anillo dorado, para que se vea cual se va a
        elegir tanto si se apunta con el raton como si se mueve con el teclado.
        """
        centro_x = constantes.ANCHO // 4 + indice * (constantes.ANCHO // 2)
        resaltado = equipo == self.resaltado

        caja = pygame.Rect(
            centro_x - constantes.ANCHO // 4 + 20, 130,
            constantes.ANCHO // 2 - 40, 260,
        )
        relleno = (constantes.COLOR_EQUIPO_RESALTADO if resaltado
                   else constantes.COLOR_EQUIPO_ELEGIDO)
        pygame.draw.rect(superficie, relleno, caja)
        pygame.draw.rect(
            superficie,
            constantes.COLOR_ACENTO if resaltado else constantes.COLOR_EQUIPO_BORDE,
            caja, 4 if resaltado else 2,
        )

        self._dibujar_retrato(superficie, equipo, caja)

        dibujar_texto_centrado_en(
            superficie, NOMBRES_DE_EQUIPO[equipo],
            self.juego.fuentes["medio"], COLOR_DE_EQUIPO[equipo], centro_x, 410,
        )

    def _dibujar_retrato(self, superficie, equipo, caja):
        """El retrato del equipo, o un rectangulo de color si falta el archivo."""
        imagen = self._retrato_escalado(equipo, caja.h)

        if imagen is None:
            pygame.draw.rect(
                superficie, COLOR_DE_EQUIPO[equipo],
                pygame.Rect(caja.x + 40, caja.y + 20, caja.w - 80, caja.h - 40),
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
    """Escena de partida: el personaje, el puntaje y el suelo.

    Todavia no hay obstaculos ni dificultad. Esos llegan en sus propias ramas.
    """

    def __init__(self, juego):
        super().__init__(juego)
        self.puntaje = 0
        self.tiempo_vivido = 0.0
        self.personaje = None

        # El agachado se puede pedir con ABAJO o con el click derecho, y son
        # dos controles independientes. Se guardan por separado para que
        # soltar uno no levante al personaje si el otro sigue apretado.
        self.tecla_agacha = False
        self.raton_agacha = False

    def inicializar(self):
        """Carga los sprites y arma el personaje.

        Si faltan archivos, cargar_texturas devuelve None y el personaje se
        dibuja como un rectangulo de color. El juego arranca igual.
        """
        texturas = personaje.cargar_texturas(self.juego.equipo)
        self.personaje = personaje.Personaje(
            texturas=personaje.recortar_agachado(texturas)
        )

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
        self.tiempo_vivido += delta
        self.puntaje = calcular_puntaje(self.tiempo_vivido)
        self.personaje.actualizar(delta)

    def dibujar(self, superficie):
        self.personaje.dibujar(superficie)

        pygame.draw.line(
            superficie,
            constantes.COLOR_SUELO,
            (0, constantes.SUELO_Y),
            (constantes.ANCHO, constantes.SUELO_Y),
            3,
        )

        dibujar_texto(
            superficie,
            f"SCORE: {self.puntaje}",
            self.juego.fuentes["puntaje"],
            constantes.COLOR_TEXTO,
            (20, 20),
        )

ESCENAS = {
    "titulo": EscenaTitulo,
    "equipo": EscenaEquipo,
    "juego": EscenaJuego,
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

        self.cambiar_escena("titulo")

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
