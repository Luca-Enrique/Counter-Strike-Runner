"""Genera ranking.html a partir de ranking.txt.

No importa Pygame a proposito: se puede ejecutar y probar sin abrir la ventana
del juego. La separacion tambien deja claro que los datos (ranking.py) y la
presentacion (este archivo + estilos.css) son responsabilidades distintas.

Uso:

    python generar_ranking.py
    python generar_ranking.py --ranking otra/ruta.txt --html otra/ruta.html
"""
import argparse
import html
from pathlib import Path

import ranking


def _fila_html(posicion, partida, muertes):
    """Una fila de la tabla. Las tres primeras llevan su clase de podio."""
    clases = "fila"
    if posicion <= 3:
        clases += " fila--{}".format(("oro", "plata", "bronce")[posicion - 1])

    equipo = html.escape(partida.equipo)
    return (
        '<tr class="{clases}">'
        '<td class="pos">{posicion}</td>'
        '<td class="iniciales">{iniciales}</td>'
        '<td><span class="equipo equipo--{equipo_clase}">{equipo}</span></td>'
        '<td class="score">{puntaje}</td>'
        '<td class="k">{personas}</td>'
        '<td class="d">{muertes}</td>'
        '<td class="kd">{ratio}</td>'
        '<td class="fecha">{fecha}</td>'
        "</tr>"
    ).format(
        clases=clases,
        posicion=posicion,
        iniciales=html.escape(partida.iniciales),
        equipo=equipo,
        equipo_clase=equipo.lower(),
        puntaje=partida.puntaje,
        personas=partida.personas,
        muertes=muertes,
        ratio=html.escape(ranking.ratio(partida.personas, muertes)),
        fecha=html.escape(partida.fecha.strftime(ranking.FORMATO_FECHA)),
    )


def _tabla_html(partidas):
    """El cuerpo de la tabla, o una sola fila avisando que esta vacio."""
    if not partidas:
        return (
            '<tr><td class="vacio" colspan="8">'
            "TODAVIA NO HAY PARTIDAS. JUGA UNA PARA ESTRENAR EL RANKING."
            "</td></tr>"
        )

    cantidades = ranking.contar_por_iniciales(partidas)
    return "\n".join(
        _fila_html(posicion, partida, cantidades[partida.iniciales])
        for posicion, partida in enumerate(partidas, start=1)
    )


def generar_html(ruta_ranking=ranking.RUTA_RANKING, ruta_html=None,
                 ruta_css="estilos.css"):
    """Lee el archivo de datos y escribe ranking.html. Devuelve su ruta.

    Se muestran las 10 mejores partidas. D se calcula sobre todo el historial,
    no solo sobre las filas visibles, para que el ratio no cambie al recortar.
    """
    ruta_ranking = Path(ruta_ranking)
    ruta_html = Path(ruta_html) if ruta_html else ruta_ranking.with_name("ranking.html")

    partidas = ranking.leer_partidas(ruta_ranking)
    mejores = ranking.top(partidas)
    tabla = _tabla_html(mejores)

    documento = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CS: RUNNER | Ranking</title>
<link rel="stylesheet" href="{css}">
</head>
<body>
<main class="ranking">
  <header class="ranking__cabecera">
    <p class="ranking__marca">COUNTER-STRIKE: RUNNER</p>
    <h1>MEJORES PUNTAJES</h1>
    <p class="ranking__subtitulo">TOP 10 &middot; HISTORICO DE LA MAQUINA</p>
  </header>

  <div class="ranking__marco">
    <table class="ranking__tabla">
      <thead>
        <tr>
          <th>POS</th>
          <th>INICIALES</th>
          <th>EQUIPO</th>
          <th>SCORE</th>
          <th>K</th>
          <th>D</th>
          <th>K/D</th>
          <th>FECHA</th>
        </tr>
      </thead>
      <tbody>
{tabla}
      </tbody>
    </table>
  </div>

  <footer class="ranking__pie">
    <p>K: personas superadas &middot; D: partidas jugadas &middot; K/D: ratio</p>
    <p class="ranking__parpadeo">INSERT COIN TO CONTINUE</p>
  </footer>
</main>
</body>
</html>
""".format(css=html.escape(ruta_css, quote=True), tabla=tabla)

    ruta_html.write_text(documento, encoding="utf-8")
    return ruta_html


def main(argv=None):
    """Entrada de linea de comandos."""
    analizador = argparse.ArgumentParser(
        description="Genera ranking.html a partir de ranking.txt."
    )
    analizador.add_argument(
        "--ranking", type=Path, default=ranking.RUTA_RANKING,
        help="archivo de datos (por defecto: ranking.txt)",
    )
    analizador.add_argument(
        "--html", type=Path, default=None,
        help="archivo de salida (por defecto: ranking.html junto al de datos)",
    )
    opciones = analizador.parse_args(argv)

    ruta = generar_html(opciones.ranking, opciones.html)
    print("Ranking generado en {}".format(ruta))


if __name__ == "__main__":
    main()
