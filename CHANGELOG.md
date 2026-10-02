# Changelog

Todos los cambios relevantes del proyecto se anotan acá.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el
proyecto usa [SemVer](https://semver.org/lang/es/).

## [No publicado]

### Agregado

- Base del motor del juego, sobre la rama `feat/base-motor`:
  - `constantes.py` con los valores de `docs/ESPECIFICACION.md` (lienzo
    virtual, fotogramas objetivo, tope de delta, gravedad, velocidad de salto,
    topes de dificultad, puntaje y umbrales de zona), más los colores, la
    posición del suelo y los tamaños de fuente, marcados como propuesta.
  - `juego.py` con la ventana redimensionable, el lienzo virtual de 960×540
    escalado con letterbox, el tope de delta y el despacho de escenas. Las
    pantallas de título y de partida ya cambian con `ESPACIO` y `ESC`.
  - `pruebas.py` con 10 verificaciones de la escala, el centrado del
    letterbox, el recorte de delta y la altura del salto.

### Corregido

- La imagen escalada se pasa por un pixel en ventanas de ancho "raro" (por
  ejemplo 500 px). El tamaño destino ahora se redondea a píxeles enteros antes
  de blitear, así que el error de redondeo de la división no puede empujar la
  imagen fuera de la ventana.

## [0.1.0] - 2026-09-29

### Agregado

- Documentación inicial: `docs/CONSIGNAS.md`, `docs/TEMATICA.md` y
  `docs/ESPECIFICACION.md`.
- `README.md` con descripción, instalación, ejecución y flujo de trabajo Git.
- `.gitignore` para Python, entorno virtual, editores y sistema operativo.
- `requirements.txt` con `pygame-ce==2.5.8`.

[No publicado]: https://github.com/Luca-Enrique/Counter-Strike-Runner/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Luca-Enrique/Counter-Strike-Runner/releases/tag/v0.1.0
