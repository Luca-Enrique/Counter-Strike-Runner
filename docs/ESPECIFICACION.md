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

## 3. Distribución, color y tipografía

Estos valores **no salen de la consigna ni de la temática**: se eligieron para que
haya algo visible en pantalla y se ajustan jugando. En `constantes.py` están
marcados como `PROPUESTA` para distinguirlos de los que sí están fijados.

| Constante | Valor | Motivo |
| --- | --- | --- |
| Altura del suelo | 460 px | Deja 80 px de piso dibujado debajo de la línea. |
| Posición horizontal del jugador | 120 px | Fija: lo que se desplaza es el escenario, no el jugador. |
| Proporción del personaje sin sprite | 0.9 | Ancho de reserva cuando no hay imagen. |
| Tamaño de fuente de título | 64 px | El título tiene que leerse de lejos. |
| Tamaño de fuente de texto | 32 px | Controles y mensajes. |
| Tamaño de fuente de puntaje | 28 px | Va en una esquina, no compite con el juego. |
| Color de fondo | RGB(24, 26, 32) | Casi negro azulado, para que los sprites resalten. |
| Color del suelo | RGB(58, 62, 72) | Un tono más claro que el fondo, da profundidad. |
| Color del texto | RGB(232, 236, 240) | Blanco apagado, no cansa la vista. |
| Color de acento | RGB(240, 196, 25) | Amarillo de recreativa, solo para lo que llama la atención. |
| Color del personaje sin sprite | RGB(86, 122, 164) | Azul apagado. Solo aparece si falta un archivo. |
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

## 6. Estructura de archivos

La consigna propone una estructura mínima y permite separar en más módulos,
siempre que se respeten las tres responsabilidades: el juego, el guardado de
datos y la generación del ranking.

```text
Counter-Strike-Runner/
├── juego.py             # punto de entrada: ventana, bucle y escenas
├── personaje.py         # la física y el dibujo del jugador
├── constantes.py        # todos los valores ajustables
├── pruebas.py           # verificaciones automáticas
├── generar_ranking.py   # lee ranking.txt y arma ranking.html (no importa pygame)
├── ranking.txt          # datos, crece con cada partida
├── estilos.css          # estilos de la página
├── ranking.html         # se regenera en cada partida
├── assets/              # imágenes y sonidos
└── docs/                # consigna, temática y esta especificación
```

`generar_ranking.py` no importa Pygame a propósito: así se puede ejecutar y
probar por separado, sin levantar la ventana del juego.

`personaje.py` está aparte de `juego.py` por la misma razón: la física y el
dibujo del jugador se pueden probar sin abrir una ventana ni construir
escenas. `juego.py` se queda con lo que le corresponde: ventana, bucle, escenas
y el reparto del trabajo entre ellas.

## 7. Las escenas

`juego.py` tiene tres escenas y el flujo va de izquierda a derecha:

```text
titulo  --ESPACIO-->  equipo  --CLICK-->  juego
```

| Escena | Qué hace |
| --- | --- |
| `titulo` | Solo el nombre del juego. `ESPACIO` pasa a la elección, `ESC` sale. |
| `equipo` | Los dos personajes a la vista. Un click elige y arranca. `ESC` vuelve. |
| `juego` | La partida. |

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
