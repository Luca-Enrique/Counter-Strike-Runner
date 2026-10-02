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


def personaje_en_suelo():
    """Un personaje recien creado, apoyado y sin sprites."""
    return personaje.Personaje()


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


# --- Los sprites

def _texturas(equipo):
    return personaje.cargar_texturas(equipo)


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

        # --- Los sprites
        ("los sprites de los dos equipos se cargan y traen los tres estados",
         _texturas_completas("CT") and _texturas_completas("T")),

        ("los sprites del equipo salen con el alto pedido (96 parado, 56 agachado)",
         _altos_de_sprite() == (constantes.ALTO_PERSONAJE, constantes.ALTO_PERSONAJE_AGACHADO)),

        ("los seis fotogramas de correr tienen la misma altura (el ancho varia, a proposito)",
         _todos_los_fotogramas_iguales()),

        ("cargar_textura devuelve None si el archivo no existe, sin fallar",
         personaje.cargar_textura("assets/no_existe_este_archivo.png", 96) is None),

        ("sin sprites el juego dibuja un rectangulo igual de grande",
         _dibuja_sin_sprites()),
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
