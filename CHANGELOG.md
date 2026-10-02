# Changelog

Los cambios del proyecto, de la versión más reciente a la más antigua.

## 1.1.0 - 2026-10-02

### Agregado

- Base del motor del juego:
  - `constantes.py` con los valores de `docs/ESPECIFICACION.md` (lienzo
    virtual de 960×540, 60 fotogramas por segundo, tope de delta de 0.05 s,
    gravedad 2400, velocidad de salto -900, topes de dificultad de 300 a
    700 px/s y de 2.0 a 0.7 s, puntaje y umbrales de zona), más los colores,
    la posición del suelo y los tamaños de fuente.
  - `juego.py` con la ventana redimensionable, el lienzo virtual escalado
    con letterbox, el tope de delta y el despacho de escenas. La pantalla de
    título y la de partida ya cambian con `ESPACIO` y `ESC`.
  - `pruebas.py` con 10 verificaciones automáticas de la escala, el centrado
    del letterbox, el recorte de delta y la altura del salto.
- Los 28 sprites del juego, en `assets/`:
  - Los personajes CT y T, con sus animaciones de correr, saltar y
    agacharse.
  - Los obstáculos caja, barril, barricada, C4, persona CT, persona T y
    proyectil volador.
  - El suelo y los cuatro fondos de zona: inicial, combate, bombas y
    avanzada.

### Corregido

- La imagen escalada se pasaba por un píxel en ventanas de ancho raro
  (por ejemplo 500 px). Ahora el tamaño destino se redondea a píxeles
  enteros antes de dibujarse, así que el error de redondeo no puede
  empujarla fuera de la ventana.

## 1.0.0 - 2026-09-29

### Agregado

- Documentación inicial: `docs/CONSIGNAS.md`, `docs/TEMATICA.md` y
  `docs/ESPECIFICACION.md`.
- `README.md` con descripción, instalación, ejecución y flujo de trabajo
  Git.
- `.gitignore` para Python, entorno virtual, editores y sistema operativo.
- `.gitattributes` para normalizar los finales de línea.
- `requirements.txt` con `pygame-ce==2.5.8`.