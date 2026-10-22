"""Valores ajustables del juego.

Todos los numeros que haya que cambiar estan aca. La idea es que el resto del
codigo no tenga numeros magicos: si algo se tunea, se tunea en este archivo.

La justificación de cada valor está en docs/ESPECIFICACION.md. Los valores
marcados como PROPUESTA no salen de ahí, se eligieron para que algo se pueda
ver; se ajustan jugando.
"""


# --- Presentación --------------------------------------------------------
# docs/ESPECIFICACION.md, sección 1

# Lienzo virtual. El juego se dibuja siempre sobre una imagen de este tamaño,
# sin importar cuanto mida la ventana: eso es lo que hace que el juego se vea
# igual en cualquier monitor. Proporcion 16:9 y divisible por 2 para que al
# escalar no se deformen los pixeles.
ANCHO = 960
ALTO = 540

# Fotogramas objetivo por segundo.
FPS = 60

# Tope del tiempo entre fotogramas, en segundos. Sin este tope, si la maquina
# se congela un instante (abrir un menu, leer un archivo) el delta seria
# enorme y la fisica se romperia de golpe. Con el tope, esos milisegundos se
# pierden: el juego se frena un momento pero nada atraviesa la pantalla.
TOPE_DELTA = 0.05

# Titulo de la ventana.
TITULO_VENTANA = "Counter-Strike: Runner"


# --- Física y dificultad -------------------------------------------------
# docs/ESPECIFICACION.md, sección 2

GRAVEDAD = 2400.0
VELOCIDAD_SALTO = -900.0

# La velocidad de los obstaculos y la frecuencia con que aparecen crecen con
# el puntaje, pero hasta estos topes. La dificultad tiene que ser creciente y acotada, nunca imposible.
VELOCIDAD_OBSTACULO_MIN = 300.0
VELOCIDAD_OBSTACULO_MAX = 700.0
INTERVALO_MIN = 2.0
INTERVALO_MAX = 0.7


# --- Puntaje y zonas -----------------------------------------------------
# docs/TEMATICA.md, secciones 7 y 9

# El puntaje se mide sobre el tiempo, no sobre la distancia recorrida, y se
# multiplica por 10 para que los umbrales se alcancen en minutos (ver
# PUNTOS_POR_SEGUNDO, mas abajo).

# Umbrales de la progresion visual. El escenario cambia al cruzarlos, y son
# los mismos numeros que disparan los mensajes de puntaje.
UMBRAL_ZONA_COMBATE = 500
UMBRAL_ZONA_BOMBAS = 1000
UMBRAL_ZONA_AVANZADA = 1500


# --- Distribucion en el lienzo -------------------------------------------
# PROPUESTA. No salen de la especificacion: se eligen para que se vea algo y
# se ajustan jugando.

# Altura de la linea de suelo. Debajo quedan 80 pixeles de piso dibujado.
SUELO_Y = 460

TAMANO_FUENTE_TITULO = 64
TAMANO_FUENTE_MEDIO = 32
TAMANO_FUENTE_PUNTAJE = 28

# Tipografia chica para las etiquetas ("SCORE", ayudas) y para la letra grande
# de cada casillero de iniciales.
TAMANO_FUENTE_ETIQUETA = 22
TAMANO_FUENTE_SLOT = 88

# Posicion horizontal del jugador. Es fija: el personaje no se mueve de lado,
# lo que se desplaza es el escenario.
JUGADOR_X = 120


# --- Personaje y animacion ------------------------------------------------
# PROPUESTA. Alturas con las que se dibujan los sprites en el lienzo virtual.

# Los sprites miden lo que miden, pero el juego los escala a estos altos. La
# escala preserva la proporcion, asi que el ancho sale del alto.
#
# La diferencia entre los dos (96 a 56) es la que hace que el personaje pase por
# debajo de un obstaculo alto sin golpearlo. Esa diferencia es de juego, no
# estetica: si se perdiera, habria obstaculos imposibles de pasar.
ALTO_PERSONAJE = 96
ALTO_PERSONAJE_AGACHADO = 56

# Ancho con el que se arma el rectangulo del personaje cuando no hay sprite
# (por ejemplo en las pruebas). Si hay sprite manda el ancho real de la
# imagen, para que el dibujo y la colISION coincidan.
PROPORCION_PERSONAJE = 0.9

# Fotogramas del estado de correr. Es uno solo: cada estado (correr, saltar,
# agacharse) se dibuja con un unico sprite estatico, sin animacion.
FOTOGRAMAS_CORRER = 1


# --- Controles -----------------------------------------------------------
# docs/TEMATICA.md: SPACE/ARRIBA/W/CLICK IZQ saltan y ABAJO/S/CLICK DER
# agachan. En la eleccion, A/D y las flechas mueven el resaltado, y
# SPACE/ENTER/CLICK IZQ confirman. El boton izquierdo es el 1 de Pygame y el
# derecho el 3.

BOTON_IZQUIERDO = 1
BOTON_DERECHO = 3

# PROPUESTA. Gravedad de la caida rapida: el doble de la normal.
#
# Agachar en el aire multiplica la gravedad por este factor, en vez de ser solo
# el agachado del suelo. Es lo que hace que el personaje baje mas rapido, y es
# la mecanica que le da sentido a soltar el control antes de tiempo.
#
# Con el doble, el punto mas alto del salto queda en 84 px en vez de 168.75 si
# se mantiene apretado desde el arranque. Ese recorte es lo que hace que el
# agachado en el aire sea una decision y no un atajo.
GRAVEDAD_CAIDA_RAPIDA = 2.0


# --- Obstaculos ----------------------------------------------------------
# PROPUESTA. Alturas con las que se dibujan, para que todos los obstaculos
# tengan un tamano coherente entre si.
#
# Los obstaculos todavia no existen en el juego: estas constantes quedan
# fijadas ahora para que la rama que los implemente no tenga que tocar este
# archivo.

ALTO_OBSTACULO_CAJA = 56
ALTO_OBSTACULO_BARRIL = 64
ALTO_OBSTACULO_BARRICADA = 44
ALTO_OBSTACULO_C4 = 36
ALTO_OBSTACULO_PERSONA = 96

# El proyectil es la excepcion: su proporcion es de 3.85:1, muy alargado, asi
# que se escala por largo y no por alto.
LARGO_PROYECTIL = 56
ALTO_PROYECTIL = 15

# Color del rectangulo que reemplaza a un obstaculo cuando falta su sprite y
# no se puede sacar el tamaño de la imagen.
COLOR_OBSTACULO_SIN_SPRITE = (150, 96, 70)


# --- Puntaje -------------------------------------------------------------
# PROPUESTA. El puntaje son los segundos que llevas vivo, por diez. La cuenta
# se corta a segundos enteros para que el numero no cambie cada fotograma.
PUNTOS_POR_SEGUNDO = 10


# --- Colores -------------------------------------------------------------
# PROPUESTA. Placeholders para las zonas. Reemplazar cuando se elija la
# paleta definitiva.

COLOR_FONDO = (24, 26, 32)
COLOR_SUELO = (58, 62, 72)
COLOR_TEXTO = (232, 236, 240)
COLOR_ACENTO = (240, 196, 25)
COLOR_LETRA_INACTIVA = (170, 180, 196)

# Rojo del aviso cuando no se pudo guardar el ranking. Tiene que leerse como un
# error y no como parte de la decoracion.
COLOR_ERROR = (232, 92, 92)

# Color del rectangulo que reemplaza al personaje cuando no hay sprite. El
# juego tiene que funcionar aunque falte un archivo.
COLOR_PERSONAJE_SIN_SPRITE = (86, 122, 164)

# Marco de las dos cajas de la pantalla de eleccion, y el fondo del recuadro
# donde va el equipo elegido. El resaltado es el panel apuntado ahora mismo,
# sea con el raton o con el teclado.
COLOR_EQUIPO_BORDE = (70, 74, 86)
COLOR_EQUIPO_ELEGIDO = (46, 50, 60)
COLOR_EQUIPO_RESALTADO = (58, 64, 78)

# Alto de los retratos de la pantalla de eleccion. Son mas grandes que el
# personaje en juego para que se vean bien: solo es dibujo, la hitbox no cambia.
ALTO_RETRATO_EQUIPO = 200

# Negro puro de las barras del letterbox. No es un color del juego: es el
# fondo de la ventana donde no entra la imagen.
COLOR_BARRA = (0, 0, 0)


# --- Fondo que se desplaza -----------------------------------------------
# PROPUESTA. El fondo muestra los escenarios del juego avanzando de derecha a
# izquierda, como una muestra. Por ahora lo usa la pantalla de titulo.

# Los escenarios que rotan, en orden. El nombre arma la ruta
# assets/escenario/fondo_<nombre>.png.
FONDOS = ("inicial", "combate", "bombas", "avanzada")

# Velocidad a la que avanza el fondo, en pixeles por segundo. La partida la
# reemplaza por la de los obstaculos multiplicada por FACTOR_PARALLAX_FONDO.
VELOCIDAD_FONDO = 60.0

# Cuanto mas lento que los obstaculos se mueve el fondo de la partida. Al ser
# mas lento, da sensacion de profundidad (parallax) en vez de parecer pegado a
# los obstaculos.
FACTOR_PARALLAX_FONDO = 0.5

# El piso va con los obstaculos: es la superficie sobre la que se apoyan, no
# una capa lejana. Se deja como factor para poder ajustarlo sin tocar juego.py.
FACTOR_PARALLAX_SUELO = 1.0

# Cada cuantos segundos el fondo pasa al escenario siguiente. Solo se usa en
# las pantallas que rotan escenarios; la partida los elige por puntaje.
SEGUNDOS_POR_FONDO = 6.0

# Oscurecido que se pinta sobre el fondo, para que el texto de encima se lea.
# Es el COLOR_FONDO con transparencia.
ALFA_OSCURECIDO_FONDO = 150

# En la partida el oscurecido es mas suave: los obstaculos tienen que verse
# bien, no solo el texto.
ALFA_OSCURECIDO_JUEGO = 60


# --- Pantallas de fin de partida -----------------------------------------
# PROPUESTA. El game over y las iniciales usan el mismo fondo animado que el
# titulo y un panel central semitransparente, para que no queden flotando sobre
# el negro y desentonen con el resto del juego.
#
# Todo lo ajustable de esas dos pantallas vive aca: para cambiar una frase, el
# tamano del panel, la transparencia o los casilleros de letra no hace falta
# tocar juego.py.

# Relleno y borde del panel central. El alfa se aplica solo al relleno; el
# borde va opaco para que el marco se vea nitido.
ALFA_PANEL = 200
COLOR_PANEL = (18, 20, 26)
COLOR_PANEL_BORDE = COLOR_ACENTO
GROSOR_BORDE_PANEL = 3

# Panel del game over y de las iniciales: (x, y, ancho, alto) en el lienzo.
GAMEOVER_PANEL = (220, 150, 520, 240)
INICIALES_PANEL = (250, 110, 460, 330)

# Frase tematica del game over. Se elige una al azar por partida; agregar o
# quitar frases de esta tupla es todo lo que hay que hacer para cambiarlas.
FRASES_GAMEOVER = (
    "HORRIBLE",
    "HORRENDO",
    "NT",
    "GG",
    "ACTUACIÓN DIGNA DE DONK",
    "TOTALMENTE SACADO",
    "LA COCISTE",
    "LA ROMPISTE",
    "SI TE PAGARAN POR JUGAR ESTO SERIAS POBRE",
    "BIG LEAGUES ARE CALLING",
    "ESTAS PARA UN MAJOR",
    "ESTAS PARA UN 'MINOR' xd",
    "DEFINITIVAMENTE HAY QUE BORRARLO",
)

# Escenario que se ve detras del game over. Es fijo: la pantalla es un cierre,
# no una muestra que rota.
ESCENARIO_GAMEOVER = "bombas"

# Lado de cada casillero de iniciales y cuanto se agranda la letra del slot
# apuntado respecto de las otras.
ANCHO_SLOT_INICIALES = 90

# Parpadeo de los avisos y de las flechas, en ciclos por segundo y en segundos
# de periodo respectivamente.
SEGUNDOS_PARPADEO = 0.7
ALTO_FLECHA_INICIALES = 16
