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
"""
import pygame
import constantes

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
    imagen = fuente.render(cadena, True, color)
    superficie.blit(imagen, imagen.get_rect(center=(superficie.get_width() // 2, y)))

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
    """Pantalla de inicio. Es la que se ve al abrir el juego."""

    def manejar_eventos(self, evento):
        if evento.type != pygame.KEYDOWN:
            return

        if evento.key in (pygame.K_SPACE, pygame.K_RETURN):
            self.juego.cambiar_escena("juego")
        elif evento.key == pygame.K_ESCAPE:
            self.juego.salir()

    def dibujar(self, superficie):
        fuentes = self.juego.fuentes
        dibujar_texto_centrado(
            superficie, "COUNTER-STRIKE: RUNNER",
            fuentes["titulo"], constantes.COLOR_TEXTO, 150,
        )
        dibujar_texto_centrado(
            superficie, "APRETA ESPACIO PARA EMPEZAR",
            fuentes["medio"], constantes.COLOR_ACENTO, 280,
        )
        dibujar_texto_centrado(
            superficie, "ESPACIO: SALTAR    ABAJO: AGACHARSE    ESC: SALIR",
            fuentes["medio"], constantes.COLOR_TEXTO, 340,
        )

class EscenaJuego(Escena):
    """Escena de partida, todavia sin fisica.

    Por ahora solo dibuja el suelo y el puntaje, para poder probar que el
    cambio de escena funciona. El salto, los obstaculos y la dificultad
    llegan en sus propias ramas.
    """

    def __init__(self, juego):
        super().__init__(juego)
        self.puntaje = 0

    def manejar_eventos(self, evento):
        if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
            self.juego.cambiar_escena("titulo")

    def dibujar(self, superficie):
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
    "juego": EscenaJuego,
}

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
        self.reloj = pygame.time.Clock()
        self.corriendo = True
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
