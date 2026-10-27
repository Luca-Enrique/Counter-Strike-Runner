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
import json
import os
import random
import webbrowser
from pathlib import Path

import pygame
import consola
import constantes
import fondo
import generar_ranking
import mando
import obstaculo
import personaje
import ranking
import sonido

# El config vive al lado del juego, igual que ranking.txt. Se guarda como
# atributo de modulo para que las pruebas puedan apuntarlo a una carpeta
# temporal sin tocar el archivo real.
RUTA_CONFIG = Path(__file__).resolve().with_name("config.json")

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
        "consola": pygame.font.SysFont(
            "consolas,couriernew,dejavusansmono,monospace",
            constantes.TAMANO_FUENTE_CONSOLA,
        ),
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

    Para el mando, cada escena declara que tecla equivale a cada accion. Asi
    las acciones del mando reutilizan los mismos manejadores que el teclado y
    no hay que duplicar la logica de cada pantalla.
    """

    MAPEO_MANDO = {
        "confirmar": pygame.K_RETURN,
        "secundario": pygame.K_ESCAPE,
        "inicio": pygame.K_RETURN,
        "atras": pygame.K_ESCAPE,
        "izquierda": pygame.K_LEFT,
        "derecha": pygame.K_RIGHT,
        "arriba": pygame.K_UP,
        "abajo": pygame.K_DOWN,
    }

    # En los menus conviene que mantener el D-pad o el stick repita el
    # movimiento. En la partida no: arriba/abajo son salto y agachado.
    REPETIR_DIRECCIONES_MANDO = True

    def __init__(self, juego):
        self.juego = juego

    def tecla_de_mando(self, accion):
        """La tecla que representa esa accion del mando en esta escena."""
        return self.MAPEO_MANDO.get(accion)

    def inicializar(self):
        """Se llama una vez, justo despues de crear la escena."""

    def manejar_eventos(self, evento):
        """Reacciona a un evento de pygame."""

    def liberar_controles(self):
        """Suelta las teclas que pudieran quedar apretadas.

        La consola la llama al abrirse: mientras esta abierta los eventos no
        llegan a la escena, asi que un KEYUP pendiente se perderia.
        """

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

    # Triangulo (Y en Xbox) abre el tutorial desde el titulo, igual que la T.
    MAPEO_MANDO = dict(Escena.MAPEO_MANDO, tutorial=pygame.K_t)

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

        if evento.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
            sonido.reproducir("select")
            siguiente = (
                "tutorial"
                if self.juego.corresponde_tutorial()
                else "equipo"
            )
            self.juego.cambiar_escena(siguiente)
        elif evento.key == pygame.K_t:
            sonido.reproducir("select")
            self.juego.cambiar_escena("tutorial")
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
                "APRETÁ ESPACIO O A PARA JUGAR",
                self.juego.fuentes["medio"],
                constantes.COLOR_ACENTO,
                centro_x,
                panel.y + 154,
            )

        dibujar_texto_centrado_en(
            superficie,
            "SPACE/ENTER/A: JUGAR   ·   T/TRIÁNGULO: TUTORIAL   ·   ESC/B: SALIR",
            self.juego.fuentes["etiqueta"],
            constantes.COLOR_LETRA_INACTIVA,
            centro_x,
            panel.bottom - 28,
        )


class EscenaTutorial(Escena):
    """Tutorial de seis paginas, antes de elegir equipo.

    Se muestra la primera vez (o cuando se pide con T desde el titulo). Cada
    SPACE/ENTER pasa de pagina y, al terminar, marca el tutorial como visto en
    el config para no volver a mostrarlo. ESC lo saltea y hace lo mismo.
    """

    def __init__(self, juego):
        super().__init__(juego)
        self.paginas = [
            ["TUTORIAL"],
            ["SALTAR: ESPACIO / ARRIBA / W / CLICK IZQ", "MANDO: A / CROSS"],
            ["AGACHAR: ABAJO / S / CLICK DER", "MANDO: B / CIRCLE O ABAJO"],
            ["ESQUIVA TODOS LOS OBSTACULOS", "SUPERA PERSONAS PARA SUMAR KILLS"],
            [
                "EN LOS MENUS: D-PAD O STICK PARA MOVERTE",
                "A: CONFIRMAR   ·   B: VOLVER",
                "TRIÁNGULO: ABRIR TUTORIAL (TITULO)",
            ],
            [
                "APRETA ESPACIO / ENTER / A PARA AVANZAR",
                "ESC / B PARA SALTEAR O VOLVER ATRAS",
            ],
        ]
        self.fondo = None
        self.suelo = None
        self.tiempo = 0.0
        self.pagina = 0

    def inicializar(self):
        self.fondo = fondo.Fondo()
        self.suelo = fondo.Suelo()
        self.tiempo = 0.0
        self.pagina = 0

    def manejar_eventos(self, evento):
        if evento.type != pygame.KEYDOWN:
            return
        if evento.key == pygame.K_ESCAPE:
            self._terminar()
            return
        if evento.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
            self.pagina += 1
            if self.pagina >= len(self.paginas):
                self._terminar()
            else:
                sonido.reproducir("tick")

    def _terminar(self):
        try:
            self.juego.tutorial_visto = True
            self.juego.guardar_config()
        except Exception:
            pass
        try:
            sonido.reproducir("select")
        except Exception:
            pass
        self.juego.cambiar_escena("equipo")

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

        panel = pygame.Rect(140, 150, 680, 260)
        dibujar_panel(superficie, panel)
        centro_x = panel.centerx

        pagina = (
            self.paginas[self.pagina]
            if self.pagina < len(self.paginas)
            else self.paginas[-1]
        )
        lineas = [pagina] if isinstance(pagina, str) else list(pagina)

        y = panel.y + 70
        for indice, linea in enumerate(lineas):
            color = (
                constantes.COLOR_ACENTO
                if self.pagina == 0 and indice == 0
                else constantes.COLOR_TEXTO
            )
            dibujar_texto_con_sombra(
                superficie,
                linea,
                self.juego.fuentes["medio"],
                color,
                centro_x,
                y,
            )
            y += 38

        if self.pagina == 0 and len(lineas) == 1:
            dibujar_texto_centrado_en(
                superficie,
                "UN TUTORIAL SIMPLE PARA EMPEZAR",
                self.juego.fuentes["etiqueta"],
                constantes.COLOR_LETRA_INACTIVA,
                centro_x,
                panel.y + 150,
            )

        dibujar_texto_centrado_en(
            superficie,
            f"PAGINA {self.pagina + 1}/{len(self.paginas)}   ·   "
            "SPACE/ENTER/A: SIGUIENTE   ·   ESC/B: SALTEAR",
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
        self._ultimo_resaltado = EQUIPOS[0]

    def inicializar(self):
        self.fondo = fondo.Fondo()
        self.suelo = fondo.Suelo()
        self.tiempo = 0.0
        self._ultimo_resaltado = self.resaltado
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
            return
        anterior = self.resaltado
        if key in IZQUIERDA:
            self.resaltado = EQUIPOS[0]
        elif key in DERECHA:
            self.resaltado = EQUIPOS[-1]
        elif key in CONFIRMAR:
            sonido.reproducir("select")
            self._elegir(self.resaltado)
            return
        if anterior != self.resaltado:
            sonido.reproducir("tick")

    def _click(self, evento):
        # Solo el boton izquierdo: el derecho es el de agacharse en la partida.
        if evento.button != constantes.BOTON_IZQUIERDO:
            return
        anterior = self.resaltado
        self._apuntar_en_ventana(evento.pos)
        if anterior != self.resaltado:
            sonido.reproducir("tick")
        sonido.reproducir("select")
        self._elegir(self.resaltado)

    def _apuntar_en_ventana(self, posicion):
        """Resalta el equipo de la mitad donde cae ese punto de la ventana."""
        x, _ = a_coordenadas_del_lienzo(
            posicion, self.juego.ventana.get_size()
        )
        anterior = self.resaltado
        self.resaltado = EQUIPOS[0] if x < constantes.ANCHO / 2 else EQUIPOS[-1]
        if anterior != self.resaltado:
            sonido.reproducir("tick")

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
            "A/D · FLECHAS · D-PAD: CAMBIAR",
            self.juego.fuentes["etiqueta"],
            constantes.COLOR_LETRA_INACTIVA,
            superficie.get_width() // 2,
            constantes.ALTO - 58,
        )
        dibujar_texto_centrado_en(
            superficie,
            "SPACE/ENTER/A: CONFIRMAR   ·   ESC/B: VOLVER",
            self.juego.fuentes["etiqueta"],
            constantes.COLOR_LETRA_INACTIVA,
            superficie.get_width() // 2,
            constantes.ALTO - 32,
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

    # En la partida el mando se usa como en CS: A/Cross salta, B/Circle
    # agacha y el D-pad o el stick abajo tambien agachan. Start no hace nada
    # para no pausar sin querer, y Back/Share vuelve al titulo.
    MAPEO_MANDO = {
        "confirmar": pygame.K_SPACE,
        "secundario": pygame.K_DOWN,
        "inicio": None,
        "atras": pygame.K_ESCAPE,
        "izquierda": None,
        "derecha": None,
        "arriba": pygame.K_UP,
        "abajo": pygame.K_DOWN,
    }
    REPETIR_DIRECCIONES_MANDO = False

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
        self.muriendo = False
        self.muerto_fade = 0.0
        self.canales_muerte = []
        self.tiempo_muerte = 0.0
        self.muerto_imagen = None
        self.muerto_rect = None
        self.pasos_timer = 0.0
        self.pasos_indice = 0
        self.en_suelo_anterior = True
        self._agachado_antes = False

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
        # El personaje consulta los cheats al saltar (jumper).
        self.personaje.juego = self.juego
        self._agachado_antes = self.personaje.agachado
        self.pasos_timer = 0.0
        self.pasos_indice = 0
        self.en_suelo_anterior = self.personaje.en_suelo

        self.puntaje = 0
        self.tiempo_vivido = 0.0
        self.obstaculos = []
        self.personas_superadas = 0
        self.terminada = False
        self.muriendo = False
        self.muerto_fade = 0.0
        self.canales_muerte = []
        self.tiempo_muerte = 0.0
        self.muerto_imagen = None
        self.muerto_rect = None
        self.fondo = fondo.Fondo(
            rotar=False, alfa=constantes.ALFA_OSCURECIDO_JUEGO
        )
        self.suelo = fondo.Suelo()
        self.tiempo_para_obstaculo = intervalo_obstaculo(0)
        try:
            sonido.reproducir("go")
        except Exception:
            pass

    def manejar_eventos(self, evento):
        if self.muriendo or self.terminada:
            return
        if evento.type == pygame.QUIT:
            self.juego.salir()
        elif evento.type == pygame.VIDEORESIZE:
            self.juego.redimensionar(evento.size)
        elif evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
            self.juego.cambiar_escena("titulo")
        elif evento.type == pygame.KEYDOWN and evento.key in SALTAR:
            estaba_en_suelo = self.personaje.en_suelo
            self.personaje.saltar()
            if estaba_en_suelo and self.personaje.en_suelo is False:
                sonido.reproducir("saltar")
                self.pasos_timer = 0.0
        elif evento.type == pygame.KEYDOWN and evento.key in AGACHAR:
            self.tecla_agacha = True
            if not self.personaje.agachado:
                sonido.reproducir("agachar")
            self.personaje.agachar(True)
            self.pasos_timer = 0.0
        elif evento.type == pygame.KEYUP and evento.key in AGACHAR:
            self.tecla_agacha = False
            self.personaje.agachar(self.raton_agacha)
        elif evento.type == pygame.MOUSEBUTTONDOWN:
            self._boton(evento.button, True)
        elif evento.type == pygame.MOUSEBUTTONUP:
            self._boton(evento.button, False)

    def liberar_controles(self):
        """Levanta al personaje y olvida el agachado apretado.

        La consola lo llama al abrirse: si el jugador venia agachado, el KEYUP
        no va a llegar a la escena y se quedaria agachado para siempre.
        """
        self.tecla_agacha = False
        self.raton_agacha = False
        if self.personaje is not None:
            self.personaje.agachar(False)
        self.pasos_timer = 0.0

    def _boton(self, boton, presionado):
        """Un boton del raton: el izquierdo salta y el derecho agacha."""
        if self.muriendo or self.terminada:
            return
        if boton == constantes.BOTON_IZQUIERDO:
            if presionado:
                estaba_en_suelo = self.personaje.en_suelo
                self.personaje.saltar()
                if estaba_en_suelo and self.personaje.en_suelo is False:
                    sonido.reproducir("saltar")
                    self.pasos_timer = 0.0
        elif boton == constantes.BOTON_DERECHO:
            self._fijar_agachado(presionado)

    def _fijar_agachado(self, del_raton):
        """Agacha o levanta segun el raton y la tecla, sinon los dos."""
        if del_raton:
            if not self.raton_agacha and not self.personaje.agachado:
                sonido.reproducir("agachar")
            self.raton_agacha = True
        else:
            self.raton_agacha = False
        estaba_agachado = self.personaje.agachado
        self.personaje.agachar(self.raton_agacha or self.tecla_agacha)
        if not estaba_agachado and self.personaje.agachado:
            sonido.reproducir("agachar")
            self.pasos_timer = 0.0

    def actualizar(self, delta):
        if self.terminada:
            return
        if self.muriendo:
            self.tiempo_muerte += delta
            if self.muerto_fade < 255:
                self.muerto_fade = min(255, self.muerto_fade + delta * 160)
            c0 = self.canales_muerte[0] if hasattr(self, "canales_muerte") and len(self.canales_muerte) > 0 else None
            c1 = self.canales_muerte[1] if hasattr(self, "canales_muerte") and len(self.canales_muerte) > 1 else None
            muerto_term = True
            try:
                if sonido.reproduciendose(c0) or sonido.reproduciendose(c1):
                    muerto_term = False
            except Exception:
                muerto_term = True
            try:
                dummy = os.environ.get("SDL_VIDEODRIVER", "").lower() == "dummy"
            except Exception:
                dummy = False
            if dummy:
                self._terminar()
                return
            if muerto_term or self.tiempo_muerte > 1.8 or self.muerto_fade >= 245:
                self._terminar()
            return

        self.tiempo_vivido += delta
        self.puntaje = calcular_puntaje(self.tiempo_vivido)
        self.personaje.actualizar(delta)

        self._actualizar_pasos(delta)

        self._actualizar_fondo(delta)
        self._actualizar_obstaculos(delta)

        if self._choca():
            try:
                if self.muriendo or self.terminada:
                    return
                try:
                    dummy = os.environ.get("SDL_VIDEODRIVER", "").lower() == "dummy"
                except Exception:
                    dummy = False
                if dummy:
                    self._terminar()
                    return
                muerto_antes = self.muriendo
                self._iniciar_muerte()
                if self.muriendo:
                    return
                if not muerto_antes:
                    self._terminar()
                return
            except Exception:
                if not self.terminada:
                    self._terminar()
                return

    def _actualizar_pasos(self, delta):
        if self.personaje is None or self.muriendo:
            return
        if getattr(self.personaje, "agachado", False):
            self.pasos_timer = 0.0
            return
        if not getattr(self.personaje, "en_suelo", True):
            self.pasos_timer = 0.0
            return
        self.pasos_timer += delta
        intervalo = 0.34
        if self.pasos_timer >= intervalo:
            self.pasos_timer = 0.0
            self.pasos_indice = (self.pasos_indice % 4) + 1
            try:
                sonido.reproducir(f"caminar_{self.pasos_indice}")
            except Exception:
                pass

    def _actualizar_fondo(self, delta):
        """Elige el escenario de la zona y mueve el fondo y el suelo."""
        velocidad = self._velocidad_actual()

        if self.fondo is not None:
            self.fondo.cambiar_escenario(zona_de_puntaje(self.puntaje))
            self.fondo.velocidad = velocidad * constantes.FACTOR_PARALLAX_FONDO
            self.fondo.actualizar(delta)

        if self.suelo is not None:
            self.suelo.velocidad = velocidad * constantes.FACTOR_PARALLAX_SUELO
            self.suelo.actualizar(delta)

    def _velocidad_actual(self):
        """La velocidad de los obstaculos, con el cheat speedyg aplicado."""
        velocidad = velocidad_obstaculo(self.puntaje)
        try:
            if getattr(self.juego, "cheats", {}).get("speedyg"):
                velocidad *= 2.0
        except Exception:
            pass
        return velocidad

    def _actualizar_obstaculos(self, delta):
        velocidad = self._velocidad_actual()

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
                try:
                    sonido.reproducir("pass_persona")
                except Exception:
                    try:
                        sonido.reproducir("pasar_persona")
                    except Exception:
                        pass
                try:
                    cada_uno.marcar_muerto(self.juego.equipo)
                except Exception:
                    try:
                        cada_uno.marcar_muerto()
                    except Exception:
                        pass

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
        if self.muriendo or self.terminada or self.personaje is None:
            return False
        try:
            if getattr(self.juego, "cheats", {}).get("god"):
                return False
        except Exception:
            pass
        for cada_uno in self.obstaculos:
            try:
                if cada_uno.tipo == "persona" and (getattr(cada_uno, "muerto", False) or getattr(cada_uno, "superado", False)):
                    continue
            except Exception:
                pass
            try:
                if cada_uno.colisiona(self.personaje.rect):
                    return True
            except Exception:
                continue
        return False

    def _iniciar_muerte(self):
        if self.muriendo or self.terminada:
            return
        try:
            self.muriendo = True
            self.muerto_fade = 0.0
            self.tiempo_muerte = 0.0
            self.pasos_timer = 0.0
            try:
                muerto = personaje.cargar_muerto(self.juego.equipo)
                if muerto is not None and self.personaje is not None:
                    self.muerto_imagen = muerto
                    self.muerto_rect = muerto.get_rect(center=self.personaje.rect.center)
                    self.muerto_rect.centerx = self.personaje.rect.centerx - 14
                    self.muerto_rect.bottom = constantes.SUELO_Y
                else:
                    self.muerto_imagen = None
                    self.muerto_rect = None
            except Exception:
                self.muerto_imagen = None
                self.muerto_rect = None
            self.canales_muerte = []
            try:
                c = sonido.reproducir("die")
                self.canales_muerte.append(c)
            except Exception:
                pass
            try:
                c = sonido.reproducir("headshot")
                self.canales_muerte.append(c)
            except Exception:
                pass
        except Exception:
            self._terminar()

    def _terminar(self):
        """Termina la partida y guarda el resultado para la pantalla siguiente.

        Son los campos 2 y 5 de ranking.txt: el puntaje y las personas
        superadas. La escena de iniciales los escribe recien al confirmar.
        """
        if self.terminada:
            return
        self.terminada = True
        self.muriendo = False
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

        try:
            if getattr(self.juego, "cheats", {}).get("wallhack"):
                for cada_uno in self.obstaculos:
                    if getattr(cada_uno, "tipo", None) != "persona":
                        continue
                    rect = getattr(cada_uno, "rect", None)
                    if rect is not None:
                        pygame.draw.rect(
                            superficie, constantes.COLOR_ACENTO, rect, 2
                        )
        except Exception:
            pass

        if self.personaje is not None:
            if self.muriendo and self.muerto_imagen is not None and self.muerto_rect is not None:
                superficie.blit(self.muerto_imagen, self.muerto_rect)
            elif not self.muriendo:
                self.personaje.dibujar(superficie)

        dibujar_texto(
            superficie,
            f"SCORE: {self.puntaje}",
            self.juego.fuentes["puntaje"],
            constantes.COLOR_TEXTO,
            (20, 20),
        )

        mando_activo = getattr(
            getattr(self.juego, "mando", None), "activo", False
        )
        if mando_activo:
            dibujar_texto(
                superficie,
                "MANDO: A SALTAR   ·   B AGACHAR   ·   BACK SALIR",
                self.juego.fuentes["etiqueta"],
                constantes.COLOR_LETRA_INACTIVA,
                (20, constantes.ALTO - 30),
            )

        if self.muriendo and self.muerto_fade > 0:
            try:
                fade = pygame.Surface(superficie.get_size())
                fade.fill((0, 0, 0))
                fade.set_alpha(int(self.muerto_fade))
                superficie.blit(fade, (0, 0))
            except Exception:
                pass


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
        try:
            if getattr(self.juego, "equipo", "CT") == "CT":
                sonido.reproducir("terwin")
            else:
                sonido.reproducir("ctwin")
        except Exception:
            pass

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
                "PRESIONA ESPACIO O A PARA INGRESAR TUS INICIALES",
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

    # B/Circle borra una letra, como BACKSPACE en el teclado. A/Cross confirma.
    MAPEO_MANDO = dict(Escena.MAPEO_MANDO, secundario=pygame.K_BACKSPACE)

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
        anterior = self._letra_actual()
        indice = (ranking.ALFABETO.index(anterior) + paso)
        self.letras[self.slot] = ranking.ALFABETO[indice % len(ranking.ALFABETO)]
        self.error = None
        if anterior != self._letra_actual():
            sonido.reproducir("tick")

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
            return
        if self.guardado and evento.key in CONFIRMAR:
            self.juego.cambiar_escena("titulo")
            return
        if evento.key in CONFIRMAR:
            self._guardar()
            return
        anterior_slot = self.slot
        letra_anterior = self._letra_actual() if hasattr(self, "_letra_actual") else None
        if evento.key in (pygame.K_UP, pygame.K_w):
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
            if self._escribir(evento.key):
                sonido.reproducir("tick")
                return
            return
        if anterior_slot != self.slot or (letra_anterior != self._letra_actual()):
            sonido.reproducir("tick")

    def _cambiar_slot(self, paso):
        """Mueve el cursor sin pasarse de los bordes."""
        anterior = self.slot
        self.slot = min(len(self.letras) - 1, max(0, self.slot + paso))
        if anterior != self.slot:
            sonido.reproducir("tick")

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
            try:
                sonido.reproducir("save_error")
            except Exception:
                pass
            return

        self.guardado = True
        try:
            sonido.reproducir("save_ok")
        except Exception:
            pass
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
            return "RANKING GUARDADO Y ABIERTO. ENTER O A PARA SEGUIR", (
                constantes.COLOR_ACENTO
            )
        return "FLECHAS/D-PAD: ELEGIR   ·   ENTER/A: CONFIRMAR   ·   ESC/B: SALIR", (
            constantes.COLOR_TEXTO
        )


ESCENAS = {
    "titulo": EscenaTitulo,
    "tutorial": EscenaTutorial,
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

        # Config: se lee antes de armar la primera escena para que el titulo
        # sepa si le toca mostrar el tutorial.
        self.config = self.cargar_config()
        self.tutorial_habilitado = bool(
            self.config.get("tutorial_activo", constantes.TUTORIAL_ACTIVO_DEF)
        )
        self.sonido_habilitado = bool(
            self.config.get("sonido_activo", constantes.SONIDO_ACTIVO_DEF)
        )
        self.tutorial_visto = bool(self.config.get("tutorial_visto", False))
        try:
            sonido.set_activo(self.sonido_habilitado)
        except Exception:
            pass

        # Cheats: los prende y apaga la consola (F12).
        self.cheats = {
            "wallhack": False,
            "god": False,
            "jumper": False,
            "speedyg": False,
        }

        # Mando y teclas que tiene apretadas ahora mismo. Se guardan por tecla
        # para que dos controles del mando que hacen lo mismo (por ejemplo
        # Circle y D-pad abajo para agacharse) no se suelten entre si.
        self.mando = mando.Mando()
        self._claves_de_mando = {}

        self.consola = consola.Consola(self)
        self.cambiar_escena("titulo")

    def corresponde_tutorial(self):
        """True si el tutorial tiene que aparecer antes de elegir equipo."""
        return bool(self.tutorial_habilitado and not self.tutorial_visto)

    def cargar_config(self):
        """Lee config.json. Si falta o esta roto, devuelve los valores por defecto."""
        try:
            with open(RUTA_CONFIG, "r", encoding="utf-8") as archivo:
                datos = json.load(archivo)
            if isinstance(datos, dict):
                return datos
        except (OSError, ValueError):
            pass
        return {
            "tutorial_activo": constantes.TUTORIAL_ACTIVO_DEF,
            "sonido_activo": constantes.SONIDO_ACTIVO_DEF,
            "tutorial_visto": False,
        }

    def guardar_config(self):
        """Guarda la config de forma atomica: primero el temporal, despues el real."""
        datos = {
            "tutorial_activo": bool(self.tutorial_habilitado),
            "sonido_activo": bool(self.sonido_habilitado),
            "tutorial_visto": bool(self.tutorial_visto),
        }
        self.config = datos
        ruta_tmp = RUTA_CONFIG.with_name(RUTA_CONFIG.name + ".tmp")
        try:
            with open(ruta_tmp, "w", encoding="utf-8", newline="\n") as archivo:
                json.dump(datos, archivo, ensure_ascii=False, indent=2)
            os.replace(ruta_tmp, RUTA_CONFIG)
        except OSError:
            try:
                if ruta_tmp.exists():
                    ruta_tmp.unlink()
            except OSError:
                pass

    def abrir_ranking(self):
        """Muestra ranking.html en el navegador. Un error no corta el juego."""
        try:
            self.abrir_navegador(self.ruta_ranking_html.resolve().as_uri())
        except OSError:
            pass

    def cambiar_escena(self, nombre):
        """Reemplaza la escena activa por la que pide el nombre dado."""
        # Lo que el mando tenia apretado era para la escena anterior. Asi una
        # direccion mantenida no mueve sola la pantalla siguiente y un boton
        # que acaba de confirmar no confirma otra vez.
        self._claves_de_mando.clear()
        self.mando.reiniciar_direccion()
        self.escena = ESCENAS[nombre](self)
        self.escena.inicializar()

    def salir(self):
        """Pide que termine el bucle."""
        self.corriendo = False

    def manejar_eventos(self):
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                self.salir()
                continue
            if evento.type == pygame.VIDEORESIZE:
                self.redimensionar(evento.size)
                continue

            # Los eventos del mando no llegan a las escenas: el estado se lee
            # una vez por fotograma en actualizar(). Solo interesan los de
            # conexion y desconexion, para abrir o cerrar el dispositivo.
            if self.mando.manejar_evento(evento):
                if self.mando.consumir_desconexion():
                    self._soltar_controles_de_mando()
                continue

            # La consola se abre y se cierra desde cualquier escena, y mientras
            # esta abierta se queda con todos los eventos: la partida sigue
            # corriendo, pero el personaje no recibe las teclas.
            if (evento.type == pygame.KEYDOWN
                    and evento.key in (pygame.K_F12, pygame.K_BACKQUOTE)):
                self._soltar_controles_de_mando()
                self.consola.alternar()
                continue
            if self.consola.abierta:
                self.consola.manejar_eventos(evento)
                continue

            self.escena.manejar_eventos(evento)

    def _soltar_controles_de_mando(self):
        """Suelta lo que el mando tenia apretado, sin tocar el teclado."""
        for clave, acciones in list(self._claves_de_mando.items()):
            if acciones:
                self._enviar_a_escena(pygame.KEYUP, clave)
        self._claves_de_mando.clear()
        self.mando.reiniciar_direccion()

    def _enviar_a_escena(self, tipo, clave):
        """Manda a la escena un evento como si viniera del teclado."""
        self.escena.manejar_eventos(pygame.event.Event(tipo, key=clave))

    def _aplicar_accion_de_mando(self, accion, presionado, repetido=False):
        """Traduce una accion del mando a la tecla de la escena actual.

        Se lleva la cuenta de que acciones tienen apretada cada tecla. Si dos
        controles del mando hacen lo mismo, soltar uno no suelta la tecla
        mientras el otro siga apretado.
        """
        clave = self.escena.tecla_de_mando(accion)
        if clave is None:
            return

        acciones = self._claves_de_mando.setdefault(clave, set())

        if repetido:
            if acciones:
                self._enviar_a_escena(pygame.KEYDOWN, clave)
            return

        if presionado:
            if accion in acciones:
                return
            acciones.add(accion)
            if len(acciones) == 1:
                self._enviar_a_escena(pygame.KEYDOWN, clave)
            return

        if accion not in acciones:
            return
        acciones.discard(accion)
        if not acciones:
            self._enviar_a_escena(pygame.KEYUP, clave)

    def redimensionar(self, tamano):
        """Ajusta la ventana al tamano pedido por el sistema.

        Al minimizar en Windows llega (0, 0) y set_mode no acepta ese valor,
        asi que se fuerza al menos 1 pixel.
        """
        ancho = max(tamano[0], 1)
        alto = max(tamano[1], 1)
        self.ventana = pygame.display.set_mode((ancho, alto), pygame.RESIZABLE)

    def actualizar(self, delta):
        self.consola.actualizar(delta)

        # El mando se lee siempre, aunque la consola este abierta, para que su
        # estado no quede atrasado. Con la consola abierta las acciones se
        # descartan: la consola se maneja con el teclado.
        repetir = getattr(
            self.escena, "REPETIR_DIRECCIONES_MANDO", True
        )
        acciones = self.mando.actualizar(delta, repetir)
        if self.mando.consumir_desconexion():
            self._soltar_controles_de_mando()

        if not self.consola.abierta:
            for accion, presionado, repetido in acciones:
                escena_antes = self.escena
                self._aplicar_accion_de_mando(accion, presionado, repetido)
                if self.escena is not escena_antes:
                    break

        self.escena.actualizar(delta)

    def dibujar(self):
        self.lienzo.limpiar()
        self.escena.dibujar(self.lienzo.superficie)
        self.consola.dibujar(self.lienzo.superficie)
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
    try:
        pygame.mixer.pre_init(44100, -16, 2, 512)
    except Exception:
        pass
    pygame.init()
    try:
        sonido.inicializar()
        sonido.cargar()
    except Exception:
        pass
    Juego().bucle()

if __name__ == "__main__":
    main()
