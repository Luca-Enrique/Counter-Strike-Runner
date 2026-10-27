# Changelog

Los cambios del proyecto, de la versión más reciente a la más antigua.

## 1.8.0 - 2026-10-26

### Agregado

- **Soporte de mando** (`mando.py`): navegación de todos los menús y control de
  la partida con un mando de PlayStation o Xbox, por USB o Bluetooth. Los
  controles de PlayStation se normalizan con SDL, así que `Cross`/`Circle`/
  `Options`/`Share` funcionan igual que `A`/`B`/`Start`/`Back`. Si el mando no
  tiene mapping, se usa el respaldo crudo de `pygame.joystick`.
- **Detección en caliente**: el mando se abre al arrancar y se puede conectar o
  desconectar durante la partida. Al desconectarse se sueltan los controles para
  que el personaje no quede agachado ni una dirección trabada.
- **Zona muerta y repetición**: el stick izquierdo ignora el temblor y las
  direcciones se repiten al mantenerlas en los menús. En la partida no se
  repiten: arriba salta y abajo agacha mientras se mantiene.
- **Mapeo por escena**: `A`/`Cross` confirma y salta, `B`/`Circle` vuelve y
  agacha, `Options`/`Start` confirma, `Share`/`Back` vuelve, y el D-pad o el
  stick navegan. En las iniciales, `B`/`Circle` borra una letra.
- **Sexta página del tutorial** y avisos de mando en el título, la elección de
  equipo, el game over, las iniciales y la partida.
- 19 pruebas nuevas para el mando (176 en total).

### Cambiado

- `Juego` consulta el mando una vez por fotograma y traduce sus acciones a los
  mismos eventos de teclado que ya usan las escenas. El teclado y el ratón
  siguen funcionando al mismo tiempo.
- Cada escena declara su `MAPEO_MANDO`; `EscenaJuego` usa salto y agachado, y
  `EscenaIniciales` usa `BACKSPACE` para el botón secundario.
- Al abrir la consola o cambiar de escena se sueltan las teclas del mando y se
  espera a que el stick vuelva al centro antes de mover la pantalla siguiente.
- `README.md` documenta los controles de teclado, ratón y mando, y agrega
  `mando.py` a la estructura del proyecto.

### Corregido

- Se corrigieron los textos del tutorial `ESCPACIO` y `SALTEAR IR PARA ATRAS`.

## 1.7.0 - 2026-10-26

### Agregado

- **Tutorial de bienvenida** (`EscenaTutorial`): cinco páginas con los controles
  y el objetivo. Aparece la primera vez que se juega, se puede volver a abrir con
  `T` desde el título y se marca como visto al terminarlo o saltearlo con `ESC`.
- **Consola de comandos (F12)** (`consola.py`): overlay al estilo CS2 que se abre
  desde cualquier escena. La partida sigue corriendo detrás, pero los eventos van
  solo a la consola. Incluye historial con `↑`/`↓`, autocompletado con `TAB`,
  scroll con `PageUp`/`PageDown` y rueda, y `F12`/`` ` ``/`ESC` para cerrar.
- **Comandos**: `help`, `cheats`, `god`, `wallhack`, `jumper`, `speedyg`,
  `tutorial`, `sonido on|off`, `tutorial_auto on|off`, `restart`, `menu`,
  `spawn`, `rank`, `clear` y `quit`, con alias en español.
- **Cheats** en `Juego.cheats`: `god` evita los choques, `wallhack` marca el borde
  de las personas, `jumper` duplica la velocidad del salto (cuádruple de altura)
  y `speedyg` duplica la velocidad de la partida. Se prenden y apagan solo desde
  la consola.
- **Configuración** (`config.json`): guarda si el tutorial ya se vio, si el
  tutorial automático está activo y si el sonido está activo. Se escribe de forma
  atómica y, si falta o está roto, se usan los valores por defecto.
- **Control de audio** (`sonido.set_activo()` y `SONIDO_ACTIVO`): permite
  silenciar todos los SFX desde la consola.
- 38 pruebas nuevas para tutorial, config, cheats, consola, comandos y el sprite
  de muerte (157 en total).

### Cambiado

- El título ahora muestra `SPACE/ENTER: JUGAR · T: TUTORIAL · ESC: SALIR` y
  decide entre tutorial y elección de equipo según la configuración.
- `EscenaJuego.liberar_controles()` suelta el agachado de teclado y ratón cuando
  se abre la consola, para que ningún control quede trabado.
- El escalado de obstáculos y fondo usa `_velocidad_actual()`, que aplica
  `speedyg` sin duplicar la fórmula de dificultad.
- `generar_ranking` y `guardar_config` escriben con `newline="\n"` para respetar
  el `eol=lf` de `.gitattributes` y no ensuciar el área de trabajo.

### Corregido

- `personaje.cargar_muerto()` escala el sprite muerto a `ALTO_PERSONAJE`; antes
  llamaba a `_escalar` con argumentos incompatibles y el dibujo quedaba mal.
- Se eliminó el bloque inalcanzable que quedaba al final de `personaje._escalar()`.
- Se quitó el buffer oculto de letras que procesaba los cheats: ahora el único
  canal es la consola, así que escribir una letra suelta ya no activa nada.

## 1.6.0 - 2026-10-23

### Agregado

- **Sistema de sonido** (`sonido.py`): inicializa el mixer, carga los SFX de
  `assets/sonidos/` y los reproduce una vez, con volumen por categoría definido
  en `constantes` (`VOLUMEN_SFX`, `VOLUMEN_UI`, `VOLUMEN_PASOS`,
  `VOLUMEN_MUERTE`, `VOLUMEN_FINAL` y `VOLUMEN_OBSTACULO`). Si el mixer no está
  disponible o falta un archivo, falla en silencio para que el juego nunca se
  rompa por audio.
- **16 efectos de sonido** en `assets/sonidos/`: salto, agacharse, cuatro pasos,
  inicio de partida, muerte, headshot, victoria de CT, victoria de T, persona
  superada, selección, tick, guardado correcto y error de guardado.
- Sonidos en la partida: `go` al comenzar, salto, agacharse, pasos alternados
  mientras corre en el suelo y aviso al superar una persona.
- **Animación de muerte del jugador.** Al chocar se muestra `muerto.png` del
  equipo elegido, se oscurece la pantalla y se espera a que termine el audio de
  muerte antes de pasar al game over. Mientras muere, los controles se ignoran.
- Sonidos en las pantallas: selección y tick en título, elección de equipo e
  iniciales; victoria del equipo rival en el game over; confirmación y error al
  guardar el ranking.
- Sprites de muerte para los dos equipos (`assets/personajes/{ct,t}/muerto.png`)
  y para la persona obstáculo (`assets/obstaculos/persona_{ct,t}_muerto.png`).
- `personaje.cargar_muerto()`, `obstaculo.cargar_persona_muerta()` y
  `Obstaculo.marcar_muerto()`.

### Cambiado

- `main()` preinicia el mixer (44100 Hz, 16 bits, estéreo, búfer 512) y llama a
  `sonido.inicializar()` y `sonido.cargar()`.
- La persona obstáculo superada pasa al sprite de cuerpo muerto, se marca como
  `superado`/`muerto` y deja de colisionar con el jugador.
- `EscenaJuego._terminar()` es idempotente y la escena ignora los eventos
  mientras el personaje muere o la partida ya terminó.
- En SDL dummy (pruebas automáticas) la muerte se resuelve sin animación para no
  bloquear el bucle.

## 1.5.2 - 2026-10-22

### Cambiado

- **Rediseño del menú de inicio y selección de personaje.** Ambos se unifican al
  estilo arcade del resto de las pantallas: panel central semitransparente con
  marco dorado, sombras en el título/etiquetas, línea decorativa dorada y avisos
  parpadeantes. Se agrega el suelo animado y un pie con los controles. En la
  selección de equipo aparece un `VS` central, flecha parpadeante sobre el
  seleccionado y los paneles resaltan con el color de acento.

## 1.5.1 - 2026-10-22

### Cambiado

- **Rediseño de `game over` e `iniciales`.** Ahora usan el fondo animado del
  juego, un panel central semitransparente con marco dorado y mayor jerarquía
  visual. El game over muestra una frase temática elegida al azar desde
  `constantes.FRASES_GAMEOVER`. La pantalla de iniciales resalta el casillero
  activo con el color de acento, flechas parpadeantes y la letra más grande.

### Agregado

- Helpers para dibujo: `dibujar_texto_con_sombra()`, `dibujar_panel()`,
  `dibujar_triangulo()` y `_parpadea()`.
- Constantes para las dos pantallas (`ALFA_PANEL`, `COLOR_PANEL`,
  `GAMEOVER_PANEL`, `INICIALES_PANEL`, `FRASES_GAMEOVER`, `ESCENARIO_GAMEOVER`,
  fuentes de etiqueta y slot).

## 1.5.0 - 2026-10-22

### Agregado

- **Ranking histórico completo.** Al chocar, el juego pasa por la pantalla de
  iniciales y al confirmar escribe la partida en `ranking.txt`, regenera
  `ranking.html` y abre la página en el navegador.
- **Pantalla de iniciales** (`EscenaIniciales`): 3 letras al estilo arcade. Las
  flechas cambian la letra y mueven el cursor, `A`..`Z` escribe directo,
  `BACKSPACE` corrige y `ENTER` confirma. `ESC` cancela sin guardar.
- **`ranking.py`**: lee, valida y agrega partidas en `ranking.txt` sin Pygame.
  Saltea las líneas mal formadas con un aviso, crea el archivo si no existe y
  nunca sobreescribe el historial. Ordena por puntaje descendente y desempata por
  la partida más antigua; calcula el top 10, la columna D y el K/D.
- **`generar_ranking.py`**: arma `ranking.html` desde los datos, con la tabla del
  top 10. Se puede ejecutar solo (`python generar_ranking.py`) porque no importa
  Pygame. El contenido se escapa con `html.escape`.
- **`estilos.css`**: estética arcade de Counter-Strike, con scanlines, podio para
  el top 3 y las columnas del scoreboard (POS, INICIALES, EQUIPO, SCORE, K, D,
  K/D, FECHA).
- `ranking.txt` con tres partidas de ejemplo y `ranking.html` generado.
- `juego.ruta_ranking`, `juego.ruta_ranking_html` y `juego.abrir_ranking()`: el
  guardado y la apertura del navegador viven en el juego, no en la escena, para
  poder reemplazarlos en las pruebas.
- 21 verificaciones nuevas de datos, HTML e ingreso de iniciales. `pruebas.py`
  pasa de 98 a 119.

### Cambiado

- `EscenaJuego._terminar()` ahora guarda también `juego.ultimas_personas`, el
  campo 5 de `ranking.txt` (personas superadas en la partida).
- `EscenaGameOver` ya no vuelve al título: `SPACE`/`ENTER`/click pasan a las
  iniciales y `ESC` vuelve al título sin guardar.
- `constantes.COLOR_ERROR`, para el aviso de que no se pudo guardar el ranking.

### Corregido

- Si `ranking.txt` no se puede escribir, el juego ya no se cae: muestra el error
  en pantalla y `ENTER` vuelve al título.

## 1.4.0 - 2026-10-22

### Agregado

- **Fondos por puntaje en la partida.** El escenario se elige con los umbrales
  de zona (`zona_de_puntaje`) y cambia al cruzar los 500, 1000 y 1500 puntos. El
  fondo avanza a la mitad de la velocidad de los obstáculos
  (`FACTOR_PARALLAX_FONDO`) y usa un oscurecido más suave que el del menú.
- **Obstáculos** (`obstaculo.py`): caja, barril, barricada, C4, persona y
  proyectil. Aparecen por el borde derecho, avanzan a la velocidad que marca el
  puntaje y se descartan al salir de pantalla. Los sprites quedan cacheados por
  tipo y equipo para no releerlos en cada aparición.
- La **persona** que aparece como obstáculo es siempre del equipo rival, y cada
  una superada se cuenta una sola vez (campo 5 de `ranking.txt`, todavía sin
  mostrar).
- **El proyectil va por el aire**, a la altura de la cabeza agachada: de pie
  golpea y agachado pasa. El resto de los obstáculos está en el suelo y se pasa
  saltando.
- **Game over mínimo**: al chocar se guarda el puntaje en
  `juego.ultimo_puntaje` y se muestra una pantalla con GAME OVER y el SCORE.
  `SPACE`, `ENTER`, `ESC` o el click vuelven al título.
- **Suelo de la partida**: `assets/escenario/suelo.png` se escala a la franja de
  80 px debajo de `SUELO_Y` y se repite mientras avanza a la velocidad de los
  obstáculos (`FACTOR_PARALLAX_SUELO`).
- Tests de zonas, dificultad, obstáculos, colisión, suelo, game over y parallax.
  `pruebas.py` pasa de 73 a 98 verificaciones.

### Cambiado

- `Fondo` acepta `rotar`, `velocidad` y `alfa`, y puede cambiar de escenario con
  `cambiar_escenario()`. La partida lo usa sin rotación automática.
- `fondo.py` suma `Suelo`, con su propio cache; `EscenaJuego` lo actualiza y lo
  dibuja entre el fondo y los obstáculos. `COLOR_SUELO` queda solo como respaldo
  si falta el asset.
- Los obstáculos se recortan con `recorte_robusto` y `_caja_visible()`, que
  descartan las componentes de menos de 8 píxeles.
- Se cachean los escenarios escalados y sus espejos.
- Se eliminó la constante duplicada `PUNTAJE_POR_SEGUNDO` (el juego ya usaba
  `PUNTOS_POR_SEGUNDO`).

### Corregido

- **La hitbox de la caja coincide con el dibujo.** El PNG trae dos píxeles
  sueltos en el extremo izquierdo que `get_bounding_rect()` tomaba como parte
  del sprite: el rectángulo quedaba unos 480 px más adelante que la caja
  visible. Ahora el recorte de los obstáculos ignora esos píxeles.
- **La partida muestra el asset del suelo** en la franja inferior y ya no
  dibuja la línea gris de `COLOR_SUELO`.

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
- **La selección con el ratón en pantalla completa ya no se desfasa.** Se
  comparaba la coordenada de la ventana con la mitad del lienzo virtual, así que
  al agrandar la ventana el click elegía el equipo equivocado. Ahora el punto del
  ratón se traduce del tamaño de la ventana al lienzo antes de decidir.

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