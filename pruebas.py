"""Verificaciones automaticas de la base del motor.

Solo comprueban funciones puras de juego.py, asi que no abren ninguna ventana
y se pueden correr en cualquier lado.

Se ejecuta con:

    python pruebas.py

Devuelve 0 si todo pasa y 1 si algo falla.
"""
import os

# Tiene que estar antes de importar juego, para que las pruebas corran tambien
# en una maquina sin pantalla (un servidor de integracion continua, por
# ejemplo). setdefault no pisa la variable si ya estaba puesta.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import constantes
import juego


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


def casos():
    """Arma la lista de (descripcion, condicion) a verificar."""
    # La altura del salto sale de la formula de docs/ESPECIFICACION.md:
    # altura = velocidad^2 / (2 * gravedad).
    altura_salto = constantes.VELOCIDAD_SALTO ** 2 / (2 * constantes.GRAVEDAD)

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
    ]


def main():
    total = 0
    falladas = 0

    for descripcion, condicion in casos():
        total += 1
        if condicion:
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
