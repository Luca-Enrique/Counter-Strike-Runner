# Especificación técnica

Este documento fija las decisiones técnicas del proyecto que no están definidas
ni en la [consigna](CONSIGNAS.md) ni en la [temática](TEMATICA.md). Es la
fuente de verdad para cualquier valor numérico que aparezca en el código.

Todas las constantes viven en `constantes.py`. Lo que se lee acá es la
justificación de cada una.

## 1. Presentación

| Parámetro | Valor | Motivo |
| --- | --- | --- |
| Lienzo virtual | 960 × 540 | Proporción 16:9, múltiplo de 2 para que el escalado no deforme píxeles. |
| Ventana | Redimensionable | El jugador puede agrandarla sin que el juego cambie. |
| Escalado | `smoothscale` con letterbox | Ver abajo. |
| Fotogramas objetivo | 60 | estándar para juegos 2D. |
| Tope de delta | 0.05 s | Ver abajo. |

### Por qué resolución virtual

El juego se dibuja **siempre** sobre un lienzo de 960×540. Recién al terminar
el fotograma esa imagen se escala para entrar en la ventana real, y lo que sobra
queda como barra negra.

Si en cambio se dibujara directamente sobre la ventana, el tamaño de la pantalla
formaría parte de la física: en un monitor grande entrarían más obstáculos en
pantalla y la dificultad dependería del hardware. Con el lienzo virtual el
juego es idéntico en cualquier resolución, y solo cambia el tamaño de la imagen.

Se usa el **menor** de los dos factores de escala (el `min`) para que la imagen
entre completa. Con `max` se saldría de la ventana.

### Por qué el tamaño destino se redondea

El ancho y el alto de la imagen escalada se redondean a **píxeles enteros** antes
de dibujarse, y nunca se estiran: si un lado quedara en 0 se lo fuerza a 1.

El redondeo no es cosmético. El factor de escala es el resultado de una división,
as que casi nunca da un número exacto. En una ventana de 500 px de ancho,
`960 × 0.5208333333333334` da `500.00000000000006`: un pelo por encima del ancho
real. Sin redondear, la imagen se saldría de la ventana por una fracción de
píxel, y la verificación de "entra completa" fallaría por una razón que no se ve
en la pantalla.

Todo eso vive en `calcular_destino()`, en `juego.py`. Devuelve la posición y el
tamaño ya redondeados, así que el dibujo solo tiene que pegarla.

### Por qué el guardia de ventana de tamaño cero

En Windows, al minimizar la ventana el sistema manda un `VIDEORESIZE` con tamaño
`(0, 0)`. `set_mode` no acepta ese valor y levanta una excepción, así que un
minimizado abortaría el juego.

El tamaño se fuerza a un mínimo de 1×1 y, si la ventana no tiene área útil, no se
dibuja nada hasta que vuelva a tener tamaño. El juego sigue corriendo por debajo,
que es lo que se espera de una ventana minimizada.

### Por qué tope de delta

El tiempo entre fotogramas se mide y se convierte a segundos para que toda la
física se exprese en píxeles por segundo. Sin ese tope, una congelación de la
máquina (abrir el menú de Windows, leer un archivo) produciría un delta enorme y
el jugador atravesaría la pantalla de golpe, sin chocar con nada.

Con el tope, esos milisegundos se pierden: el juego se ralentiza un instante pero
la física no se rompe. Un tope de 0.05 s equivale a dejar pasar unos 3
fotogramas de rezago antes de recortar.

## 2. Física y dificultad

| Constante | Valor | Motivo |
| --- | --- | --- |
| Gravedad | 2400 px/s² | — |
| Velocidad de salto | −900 px/s | Produce una altura de unos 169 px, cerca de un tercio de la pantalla. |
| Velocidad de obstáculos | 300 → 700 px/s | El máximo es un tope duro, pedido explícitamente por la temática. |
| Intervalo de aparición | 2.0 s → 0.7 s | Ídem: la frecuencia también tiene tope. |
| Parallax del fondo | 0.5 | El fondo avanza a la mitad de la velocidad de los obstáculos. |

Estos valores son un **punto de partida**, no un dogma. Se ajustan jugando, y
el ajuste es parte del trabajo. Lo que no se negocia es que la velocidad y la
frecuencia sean crecientes y acotadas: la temática pide que la dificultad "deba
tener un límite para que no sea imposible".

La altura del salto sale de la fórmula `altura = v² / (2 · g)`. Con los valores
de arriba, `900² / (2 · 2400) = 168.75` píxeles.

### Por qué el salto usa la solución exacta y no suma velocidad

La altura se calcula con la solución cerrada de la caída libre:

```text
y(t) = y₀ + v₀ · t + (g / 2) · t²
```

y no sumando la velocidad fotograma a fotograma. La diferencia parece un detalle
pero importa por dos razones:

- **La altura es la misma siempre.** La fórmula da exactamente 168.75 px. Sumando
  a mano, el punto más alto cae 7.75 px más bajo a 60 por segundo, y 16 px más
  bajo a 30: la altura del salto dependería de la máquina.
- **Es el mismo código a cualquier tasa de fotogramas.** `personaje.py` calcula
  la posición a partir del tiempo transcurrido, no de cuántos fotogramas
  pasaron.

El tiempo en el aire se mide de forma continua (0.75 s), y el rectángulo se
coloca recién redondeado a píxel entero. Guardar la cuenta en coma flotante y
redondear solo al dibujar evita que el redondeo se acumule.

## 2.1 El personaje

`personaje.py` tiene la física y el dibujo. No sabe qué escena lo usa ni le
interesan los obstáculos: la escena le dice cuándo saltar o agachar y él solo
avanza.

| Estado | Qué hace |
| --- | --- |
| Correr | Siempre que está apoyado. Un único sprite estático, sin animación. |
| Saltar | Un toque de `ESPACIO` / `ARRIBA` / click izquierdo. En el aire no hace nada: no hay doble salto. |
| Agachado | `ABAJO` / click derecho baja el rectángulo de 96 a 56 px. **Solo en el suelo.** |

Salir de un agachado con `ESPACIO` levanta al personaje antes de saltar, así que
saltar y agacharse no se contradicen.

El agachado no aplica en el aire porque no hay sprite de caída: se usaría el de
salto y no se vería la diferencia. En su lugar, **mantener `ABAJO` apretado en el
aire acelera la caída** (ver abajo).

### La caída rápida

`ABAJO` o el click derecho mantenidos mientras el personaje está en el aire cambian
la gravedad a 2× (`GRAVEDAD_CAIDA_RAPIDA`). Sirve para bajar antes y meterse bajo
un obstáculo cuando el salto normal no alcanza.

La física no se reescribe: la parábola **se reinicia desde donde está el
personaje**, con la posición y la velocidad que ya tenía. Por eso no hay un salto
de posición al apretar, que sería un teletransporte. El efecto es que el ascenso
restante se acorta y la bajada se acelera, de golpe y continuo.

El salto normal no cambia: sin `ABAJO` el apex sigue siendo 168.75 px.

### El agachado es un recorte, no una deformación

El sprite de `agacharse.png` tiene una proporción ancha (0.94) para ser una
persona, así que si se escala directo a los 56 px de la hitbox queda chico y con
la cabeza desproporcionada. Estirarlo en horizontal para compensar lo deforma y
queda peor todavía.

La solución es **recortar**. Primero se carga `agacharse.png` al mismo alto que
el de correr (96 px), así la cabeza sale del mismo tamaño; recién entonces se
muestran los **56 pixeles de arriba** y se ocultan las piernas. El corte no
reescala nada: la cabeza conserva sus píxeles originales.

Después del corte se recorta el margen transparente que queda. Sin ese paso, el
lienzo del sprite escalado (unos 90 px de ancho) se centraría sobre la hitbox de
76 px y el dibujo se vería corrido de lugar. Con el recorte del margen, el torso
visible queda centrado y nunca más ancho que la hitbox. La prueba
`_agachado_entra_en_la_hitbox` lo comprueba.

El corte se hace sobre el sprite de `agacharse.png`, no sobre el de correr: lo
que se ve agachado es la pose de agacharse, con las piernas ocultas.

### El rectángulo manda

El rectángulo de colisión **nunca** se deduce del ancho del fotograma que se
está dibujando. Hay dos razones, y las dos son bugs reales que se evitaron:

- **El ancho no se recalcula con el estado.** Cada estado se dibuja con un
  único sprite, pero el ancho de la hitbox no sale del sprite dibujado: sale del
  sprite de correr. Si saliera del que se está dibujando, la hitbox cambiaría al
  pasar de un estado a otro.
- **El agachado no achica el ancho.** Solo el alto. Si la hitbox se angostara al
  agacharse, pasarían obstáculos que en realidad golpean.

El sprite se dibuja centrado sobre el rectángulo, nunca al revés. Así lo que se
ve y lo que colisiona son siempre lo mismo.

### Los sprites

| Estado | Alto en pantalla |
| --- | --- |
| Correr | 96 px |
| Saltar | 96 px |
| Agachado | 56 px |

Los PNG miden lo que miden: la escala **preserva la proporción** y se hace por
alto, salvo el proyectil, que es la excepción y se escala por largo (su
proporción es de 3.85:1). Por eso el tamaño de los archivos es irrelevante y no
hizo falta redimensionar nada a mano.

Al cargar, cada imagen se recorta con `get_bounding_rect()` para sacarle el
margen transparente que traen los sprites de personaje y obstáculo. Sin ese
recorte, el rectángulo de colisión sería más grande que el dibujo y golpearía
cosas que no se ven.

### Si falta un archivo

`cargar_textura()` devuelve `None` si el archivo no existe, y el estado se dibuja
como un rectángulo de color del mismo tamaño. El juego arranca siempre, aunque
falte un asset. El recorte con `smoothscale` y no con `scale` es por lo mismo:
los sprites de origen son muy grandes y hay que reducirlos mucho, y el
filtrado evita que queden bordes irregulares.

## 2.2 Los obstáculos

`obstaculo.py` tiene los sprites y el rectángulo de cada obstáculo. La escena
decide cuándo aparece y a qué velocidad avanza; el obstáculo solo se mueve.

| Tipo | Alto en pantalla | Cómo se pasa |
| --- | --- | --- |
| Caja | 56 px | Saltando. |
| Barril | 64 px | Saltando. |
| Barricada | 44 px | Saltando. |
| C4 | 36 px | Saltando. |
| Persona | 96 px | Saltando. Es siempre del equipo rival. |
| Proyectil | 15 px de alto, 56 px de largo | Agachándose. Va por el aire. |

El proyectil se apoya justo arriba de la cabeza agachada
(`SUELO_Y - ALTO_PERSONAJE_AGACHADO - 1`). De pie golpea; agachado pasa. El
píxel de margen evita que el redondeo haga tocarse los rectángulos.

Los sprites de los obstáculos se recortan con `_caja_visible()`, que ignora las
componentes de menos de 8 píxeles. Sin eso, un píxel perdido lejos del dibujo
estira la caja y la hitbox queda desfasada: la caja traía dos píxeles sueltos
en el extremo izquierdo que movían su rectángulo unos 480 px hacia adelante.

La persona que aparece como obstáculo es del **equipo contrario** al elegido:
si el jugador es CT, aparece un T. Sus iniciales y su equipo son los campos 1 y
3 de `ranking.txt`.

Los obstáculos aparecen en el borde derecho (`x = ANCHO`) y avanzan hacia la
izquierda. Se descartan cuando su borde derecho sale de la pantalla. El primero
aparece a los `INTERVALO_MIN` segundos, así el jugador tiene tiempo de
acomodarse.

### La dificultad

La velocidad y el intervalo se interpolan linealmente con el puntaje:

```text
progreso = min(1, puntaje / UMBRAL_ZONA_AVANZADA)
velocidad = VELOCIDAD_OBSTACULO_MIN + (MAX - MIN) · progreso
intervalo = INTERVALO_MIN + (MAX - MIN) · progreso
```

El progreso se topa en 1 al llegar a los 1500 puntos, que es el mismo umbral de
la zona avanzada. Así la dificultad crece y tiene un límite, como pide la
temática, y el límite coincide con el último cambio de escenario.

### El fondo y el suelo de la partida

El escenario se elige por el puntaje (`zona_de_puntaje`) con los mismos
umbrales de la progresión visual, y no rota solo: cambia cuando el puntaje
cruza un umbral.

El fondo se mueve a la mitad de la velocidad de los obstáculos
(`FACTOR_PARALLAX_FONDO`). Esa diferencia es el parallax: da sensación de
profundidad y evita que el fondo parezca pegado a los obstáculos.

La franja inferior (`SUELO_Y..ALTO`, 80 px) la ocupa
`assets/escenario/suelo.png`. El asset completo se escala a esos 80 px y se
repite en copias consecutivas. El suelo avanza a la misma velocidad que los
obstáculos (`FACTOR_PARALLAX_SUELO`), porque es la superficie sobre la que se
apoyan. Si falta el archivo, la franja se pinta con `COLOR_SUELO`.

Durante la partida el oscurecido del fondo es más suave que en el menú
(`ALFA_OSCURECIDO_JUEGO`), porque acá lo importante es que se vean los
obstáculos, no solo el texto.

### La colisión

La colisión se decide con `personaje.rect` y `obstaculo.rect`, los mismos
rectángulos que se dibujan. Un solo contacto termina la partida. Agacharse baja
el rectángulo del jugador lo suficiente para pasar bajo el proyectil, y saltar
lo sube lo suficiente para pasar sobre los obstáculos de suelo (el salto llega
a 168.75 px y el más alto mide 96 px).

Cada persona superada se cuenta una sola vez, aunque tarde varios fotogramas en
terminar de pasar al jugador. Ese contador es el campo 5 de `ranking.txt`: la
partida lo copia a `juego.ultimas_personas` al chocar y de ahí sale el **K** del
ranking. El marcador en pantalla sigue mostrando el SCORE, no las personas.

## 2.3 El game over y las iniciales

Cuando el personaje choca, la escena guarda el puntaje en
`juego.ultimo_puntaje` y las personas superadas en `juego.ultimas_personas`, y
cambia a `gameover`. La pantalla usa el fondo animado fijado en el escenario
`bombas`, un panel central semitransparente, una frase tematica elegida al azar
desde `constantes.FRASES_GAMEOVER` y el aviso parpadeante para pasar a las
iniciales. `SPACE`, `ENTER` o el click izquierdo pasan a la pantalla de
iniciales; `ESC` vuelve al título sin guardar nada.

## 2.4 El ingreso de iniciales

La pantalla de iniciales (`iniciales`) pide exactamente 3 letras, al estilo de las
recreativas:

| Tecla | Qué hace |
| --- | --- |
| `ARRIBA` / `W` | Pasa a la letra siguiente, dando la vuelta de Z a A. |
| `ABAJO` / `S` | Pasa a la letra anterior, dando la vuelta de A a Z. |
| `IZQUIERDA` / `DERECHA` | Mueve el cursor entre las tres letras. |
| `A`..`Z` | Escribe esa letra directo y avanza el cursor. |
| `BACKSPACE` | Retrocede un lugar para corregir. |
| `ENTER` | Confirma. |
| `ESC` | Cancela y vuelve al título sin guardar. |

La pantalla usa el fondo animado rotativo y un panel central. El casillero
apuntado se resalta con el color de acento, muestra flechas parpadeantes
arriba y abajo, y su letra aparece más grande. Al confirmar se **escribe la
partida** en `ranking.txt`, se **regenera** `ranking.html` y se **abre en el
navegador**. Recién ahí la partida queda registrada. Si el archivo no se puede
escribir, el juego no se cae: muestra el error en pantalla y `ENTER` vuelve al
título.

El guardado y la apertura viven en `juego.py` como `juego.ruta_ranking`,
`juego.ruta_ranking_html` y `juego.abrir_ranking()`, para que se puedan
reemplazar en las pruebas y no ensuciar el `ranking.txt` real.

## 3. Distribución, color y tipografía

Estos valores **no salen de la consigna ni de la temática**: se eligieron para que
haya algo visible en pantalla y se ajustan jugando. En `constantes.py` están
marcados como `PROPUESTA` para distinguirlos de los que sí están fijados.

| Constante | Valor | Motivo |
| --- | --- | --- |
| Altura del suelo | 460 px | Deja 80 px para la franja de `suelo.png`. |
| Posición horizontal del jugador | 120 px | Fija: lo que se desplaza es el escenario, no el jugador. |
| Proporción del personaje sin sprite | 0.9 | Ancho de reserva cuando no hay imagen. |
| Tamaño de fuente de título | 64 px | El título tiene que leerse de lejos. |
| Tamaño de fuente de texto | 32 px | Controles y mensajes. |
| Tamaño de fuente de puntaje | 28 px | Va en una esquina, no compite con el juego. |
| Color de fondo | RGB(24, 26, 32) | Casi negro azulado, para que los sprites resalten. |
| Color del suelo | RGB(58, 62, 72) | Respaldo si falta `suelo.png`. |
| Velocidad del suelo | 1.0× obstáculos | Se mueve con los obstáculos, no con el fondo. |
| Color del texto | RGB(232, 236, 240) | Blanco apagado, no cansa la vista. |
| Color de acento | RGB(240, 196, 25) | Amarillo de recreativa, solo para lo que llama la atención. |
| Color del personaje sin sprite | RGB(86, 122, 164) | Azul apagado. Solo aparece si falta un archivo. |
| Color del obstáculo sin sprite | RGB(150, 96, 70) | Terracota apagado. Solo aparece si falta un archivo. |
| Oscurecido del menú | Alfa 150 | El texto tiene que leerse sobre el escenario. |
| Oscurecido de la partida | Alfa 60 | Más suave: los obstáculos tienen que verse bien. |
| Color de las barras | RGB(0, 0, 0) | No es un color del juego: es la ventana donde no entra la imagen. |

La tipografía usa por ahora la fuente que viene con Pygame, así que el juego no
depende de ningún archivo de texto. Si más adelante se agrega una fuente
descargada, `cargar_fuentes()` es el único lugar que hay que tocar.

## 4. Formato de `ranking.txt`

Un registro por línea, con los campos separados por punto y coma:

```text
LUC;1250;CT;2026-10-16 14:32:05;37
LUC;980;CT;2026-10-16 14:35:12;29
ANA;1500;T;2026-10-16 15:02:44;45
LUC;640;T;2026-10-16 15:10:01;19
```

| Campo | Contenido |
| --- | --- |
| 1 | Iniciales, 3 letras |
| 2 | Puntaje de la partida |
| 3 | Equipo elegido: `CT` o `T` |
| 4 | Fecha y hora, `AAAA-MM-DD HH:MM:SS` |
| 5 | Obstáculos de tipo **Persona** superados en esa partida |

El punto y coma funciona como separador porque las iniciales tienen siempre 3
letras y la fecha no lo contiene. Ningún campo puede contener `;`, así que el
archivo se puede leer partiendo la línea sin ambigüedad.

### Qué NO se guarda

El total de game over (**D**) del jugador **no está en el archivo**. Se calcula
contando cuántas líneas tienen sus mismas iniciales. En el ejemplo de arriba,
`LUC` tiene 3 partidas, así que sus tres filas muestran `D = 3`.

Guardarlo sería redundante: si el jugador guardara dos partidas seguidas, habría
que reescribir la fila vieja. Calcularlo siempre da un número consistente con el
historial real, y es más barato de explicar.

### Reglas de escritura

- Si el archivo no existe, se crea vacío. La primera partida nunca debe fallar.
- Las líneas mal formadas se **salten con un aviso**, no cortan la ejecución. Un
  `ranking.txt` editado a mano no puede romper el juego.
- Se **agrega** al final con modo `append`. Nunca se sobreescribe: el ranking
  es histórico.

## 5. `ranking.html`

### Ordenamiento

Primero por puntaje, de mayor a menor. En caso de empate gana **la partida más
antigua**, que es la regla clásica de las recreativas: el primero que sacó ese
puntaje lo merece más.

Se muestran las 10 mejores partidas. Cada fila es una partida, no un jugador,
porque la consigna pide "el top 10 de puntajes".

### Columnas

| Columna | Origen |
| --- | --- |
| POS | Posición en el orden. |
| INICIALES | Campo 1 del archivo. |
| EQUIPO | Campo 3 del archivo. |
| SCORE | Campo 2 del archivo. |
| K | Campo 5 del archivo. |
| D | Calculado: cantidad de filas con esas iniciales. |
| K/D | División de K por D. |
| FECHA | Campo 4 del archivo. |

Con los cuatro registros de ejemplo, la tabla queda:

| POS | INICIALES | EQUIPO | SCORE | K | D | K/D |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | ANA | T | 1500 | 45 | 1 | 45.0 |
| 2 | LUC | CT | 1250 | 37 | 3 | 12.3 |
| 3 | LUC | CT | 980 | 29 | 3 | 9.7 |
| 4 | LUC | T | 640 | 19 | 3 | 6.3 |

`ranking.html` se regenera al terminar cada partida y se abre solo en el
navegador. Los estilos viven en `estilos.css`, un archivo aparte, para que la
página tenga forma aunque el HTML se genere desde Python.

La generación está en `generar_ranking.py`: `generar_html()` lee los datos con
`ranking.py`, recorta el top 10 y escribe la tabla. La tabla se escapa con
`html.escape` aunque los datos ya vengan validados: el generador no confía en su
entrada. El archivo se puede ejecutar solo, sin Pygame:

```bash
python generar_ranking.py
```

## 6. Estructura de archivos

La consigna propone una estructura mínima y permite separar en más módulos,
siempre que se respeten las tres responsabilidades: el juego, el guardado de
datos y la generación del ranking.

```text
Counter-Strike-Runner/
├── juego.py             # punto de entrada: ventana, bucle y escenas
├── personaje.py         # la física y el dibujo del jugador
├── obstaculo.py         # los sprites y el rectángulo de los obstáculos
├── fondo.py             # los escenarios y el suelo que se desplazan
├── constantes.py        # todos los valores ajustables
├── pruebas.py           # verificaciones automáticas
├── ranking.py           # datos: lee, valida y agrega en ranking.txt (sin pygame)
├── generar_ranking.py   # lee ranking.txt y arma ranking.html (no importa pygame)
├── ranking.txt          # datos, crece con cada partida
├── estilos.css          # estilos de la página
├── ranking.html         # se regenera en cada partida
├── assets/              # imágenes y sonidos
└── docs/                # consigna, temática y esta especificación
```

`ranking.py` y `generar_ranking.py` no importan Pygame a propósito: así se
pueden ejecutar y probar por separado, sin levantar la ventana del juego. La
separación respeta las tres responsabilidades que pide la consigna: el juego
(`juego.py`), el guardado de datos (`ranking.py`) y la generación del ranking
(`generar_ranking.py` + `estilos.css`).

`personaje.py` está aparte de `juego.py` por la misma razón: la física y el
dibujo del jugador se pueden probar sin abrir una ventana ni construir
escenas. `obstaculo.py` y `fondo.py` viven aparte por lo mismo: saben moverse y
dibujarse, pero no saben de escenas ni de puntaje. `juego.py` se queda con lo
que le corresponde: ventana, bucle, escenas y el reparto del trabajo entre
ellas.

## 7. Las escenas

`juego.py` tiene cinco escenas y el flujo va de izquierda a derecha:

```text
                    ESPACIO            CLICK            CHOQUE
 titulo -------------------> equipo -----------> juego ---------> gameover
   ^                          |                   |                  |
   |                    ESC   |             ESC   |        ENTER/SPACE/click
   |                          +-------------------+                  v
   |                                                                 |
   |   ESC (cancela, no guarda)                                      v
   +------------------- iniciales --ENTER (guarda + abre ranking)-- (navegador)
```

| Escena | Qué hace |
| --- | --- |
| `titulo` | El nombre del juego y el aviso de insertar una moneda. `ESPACIO` pasa a la elección, `ESC` sale. |
| `equipo` | Los dos personajes a la vista. Un click elige y arranca. `ESC` vuelve. |
| `juego` | La partida: fondo por zona, obstáculos, personaje y puntaje. `ESC` vuelve al título. |
| `gameover` | El puntaje final. `SPACE`/`ENTER`/click pasan a las iniciales; `ESC` vuelve al título. |
| `iniciales` | Las 3 letras. `ENTER` guarda, regenera y abre `ranking.html`; `ESC` cancela. |

La pantalla de título **no anuncia los controles**: se anuncian en la de
elección, que es donde se elige el personaje y arranca la partida.

### El equipo se elige por la mitad de la pantalla

El click se decide por la **mitad de la pantalla**: izquierda es CT, derecha es T.
No se mira dónde cayó el retrato.

Eso es deliberado. Si la decisión dependiera de la imagen, un asset faltante
rompería la selección sin avisar. Con la mitad, el juego elige equipo siempre,
y el retrato es solo decoración: si falta el archivo, se dibuja un rectángulo
del color del equipo y el click sigue funcionando igual.

Los retratos salen de `assets/obstaculos/persona_ct.png` y `persona_t.png`: son
los mismos sprites que después van a ser obstáculos, así que la elección muestra
exactamente la misma cara que se va a ver jugando.

El equipo elegido queda en `juego.equipo` y no se vuelve a preguntar. Es el
**campo 3 de `ranking.txt`**, así que la escena de partida lo lee de ahí para
cargar los sprites, sin que la escena tenga que saber de dónde salió.
