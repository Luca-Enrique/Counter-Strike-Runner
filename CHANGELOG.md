# Changelog

Los cambios del proyecto, de la versión más reciente a la más antigua.

## 1.3.0 - 2026-10-19

### Cambiado

- Cada estado del personaje (correr, saltar y agacharse) usa un único sprite
  estático. Se eliminó la animación de correr de 6 fotogramas y las constantes
  que la sostenían (`FOTOGRAMAS_ANIMACION_POR_SEGUNDO`, `FRACCION_AGACHADO`).
- La pantalla de título dice **"Apretá espacio para insertar una moneda"**.
- La elección de personaje se navega con `A`/`D` o las flechas (y con el ratón,
  que resalta lo que se apunta) y se confirma con `SPACE`, `ENTER` o el click
  izquierdo. El panel elegido se marca con un anillo dorado.
- `W` salta y `S` se agacha, además de `ESPACIO`/`ARRIBA`/click izquierdo y
  `ABAJO`/click derecho.

### Corregido

- **El agachado usa el sprite de agacharse.** Antes se veía la pose de correr
  recortada. Ahora `agacharse.png` se carga al mismo alto que correr (96 px),
  se recorta a los 56 px de la hitbox y se le quita el margen transparente, así
  la cabeza queda del mismo tamaño y el torso entra justo en la hitbox.
- **Los nombres de la elección ya no se pisan.** Se centraban todos en el medio
  de la pantalla, así que el nombre y la abreviatura de cada equipo se
  superponían con los del otro. Ahora cada uno se centra en su propia mitad y se
  dibuja debajo del retrato, no encima. Se quitaron las etiquetas "CT"/"T" (queda
  solo el nombre completo) y la línea de ayuda de la parte de abajo.

### Agregado

- Sprites de personaje de CT y de T (`correr_0.png`, `saltar.png` y
  `agacharse.png` de cada equipo).
- Retratos de la elección tomados de los mismos sprites que después son
  obstáculos (`assets/obstaculos/persona_ct.png` y `persona_t.png`).
- **Fondo animado** con los escenarios del juego avanzando de derecha a
  izquierda como una muestra, que rota entre sí (`fondo.py`). Va oscurecido para
  que el texto de encima se lea. Se usa en el título y en la elección de
  personaje, y queda listo para que la partida lo use cuando tenga escenarios
  por zona.

## 1.2.0 - 2026-10-02

### Agregado

- `personaje.py`: el personaje jugable, con su rectángulo de colisión, la
  animación de correr de 6 fotogramas, el salto de altura fija de 168.75 px y
  el agachado. El salto usa la solución exacta de caída libre, así que da la
  misma altura a 30 que a 60 fotogramas por segundo.
- El personaje y el puntaje en la escena de partida: el puntaje son los
  segundos jugados por diez.
- **Los controles que pedía `docs/TEMATICA.md`**, que faltaban:
  `ESPACIO`, `ARRIBA` y click izquierdo saltan; `ABAJO` y click derecho
  agachan. Teclado y ratón se guardan por separado, así que soltar uno no
  levanta al personaje si el otro sigue apretado.
- **La caída rápida**: mantener `ABAJO` en el aire pasa la gravedad al doble.
  La parábola se reinicia desde la posición y la velocidad actuales, así que no
  hay teletransporte: el ascenso restante se acorta y la bajada se acelera de
  golpe. El salto normal no cambia.
- **La pantalla de elección de personaje**, con los dos a la vista y un click
  para elegir entre `Terrorist` y `Counter-Terrorist`. El equipo queda en
  `juego.equipo`, que es el campo 3 de `ranking.txt`.
- Los retratos de la selección salen de los mismos sprites que después son
  obstáculos (`persona_ct.png` y `persona_t.png`).
- `pruebas.py` pasa de 10 a 59 verificaciones.

### Corregido

- **El agachado ya no deforma al personaje.** El sprite es un personaje parado
  encogido: escalado a 56 px quedaba angosto, y estirarlo 1.72 veces lo
  deformaba más todavía. Ahora se **recorta**: se muestran los 56 píxeles de
  arriba del fotograma de correr y las piernas quedan ocultas, sin reescalar
  nada. La cabeza conserva exactamente el mismo tamaño que corriendo.
- La pantalla de título ya no anuncia los controles: dice solo el nombre del
  juego. Los controles aparecen en la pantalla de elección.

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