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
# multiplica por 10 para que los umbrales se alcancen en minutos.
PUNTAJE_POR_SEGUNDO = 10

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


# --- Colores -------------------------------------------------------------
# PROPUESTA. Placeholders para las zonas. Reemplazar cuando se elija la
# paleta definitiva.

COLOR_FONDO = (24, 26, 32)
COLOR_SUELO = (58, 62, 72)
COLOR_TEXTO = (232, 236, 240)
COLOR_ACENTO = (240, 196, 25)

# Negro puro de las barras del letterbox. No es un color del juego: es el
# fondo de la ventana donde no entra la imagen.
COLOR_BARRA = (0, 0, 0)
