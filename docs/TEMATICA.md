# Counter-Strike: Runner

## 1. Concepto general

El juego debe tener en cuenta los siguientes aspectos:

- Estética de Counter-Strike.
- Obstáculos y elementos reconocibles de la saga.
- Interfaz inspirada en videojuegos arcade.
- Ranking con apariencia de tabla de puntuaciones clásica.
- Referencias visuales y humorísticas relacionadas con Counter-Strike.

## 2. Nombre: Counter-Strike: Runner

Nombre corto que puede utilizarse dentro del juego:
**CS: Runner**

## 3. Gameplay

El jugador corre automáticamente mientras que la posición horizontal del personaje será prácticamente fija haciendo que el escenario y los obstáculos se desplazen hacia la izquierda.

Las acciones del jugador serán:

```text
SPACE/ARRIBA/CLICK IZQ → SALTAR
ABAJO/CLICK DER → AGACHARSE
```

La consigna exige como mínimo que el personaje salte con la tecla espacio. Las
teclas adicionales y los clicks de mouse son un agregado de la temática, no un
requisito: si no llegaran a implementarse, el juego seguiría cumpliendo.

El objetivo es evitar los obstáculos y si el personaje toca un obstáculo **GAME OVER**.

El jugador debe intentar conseguir la mayor puntuación posible antes de morir.

## 4. Personaje

El personaje tendrá apariencia inspirada en personajes de Counter-Strike.

El jugador puede elegir entre CT o T al comienzo del juego.

Los sprites del personaje deben ser reconocibles y deben tener animaciones de correr, saltar y agacharse funcionales.

## 5. Obstáculos

Los obstáculos deben tener temática relacionada con Counter-Strike.

Algunas ideas:

- Caja
- C4
- Barril
- Barricada
- Persona CT/T dependiendo del personaje elegido
- Proyectil volador (granada, bala, etc.)

## 6. Escenario

El escenario debe transmitir que el jugador está dentro de un entorno relacionado con Counter-Strike.

Se pueden utilizar elementos simples como:

- Suelo
- Fondo del respectivo mapa
- Grafitis famosos de Counter-Strike
- Elementos varios (cajas, barriles, etc.)

## 7. Progresión visual

El escenario debe cambiar progresivamente a medida que aumenta el puntaje.

Ejemplo:

```text
0 - 500       → zona inicial
500 - 1000    → zona de combate
1000 - 1500   → zona de bombas
1500+         → zona avanzada
```

La zona avanzada es la última: se mantiene hasta el final de la partida. Eso no
contradice el límite que pide la sección de dificultad, porque ese tope se
aplica a la velocidad y a la frecuencia de aparición de obstáculos, no al
escenario. El jugador puede seguir viendo la zona avanzada sin que el juego se
vuelva imposible.

## 8. Dificultad

La dificultad debe aumentar principalmente mediante la velocidad.

Al comenzar:

- Obstáculos relativamente lentos.
- Mayor tiempo de reacción.

A medida que aumenta el score:

- Obstáculos más rápidos.
- Menor tiempo de reacción.
- Partidas progresivamente más difíciles.
- Aumentar la frecuencia de aparición de obstáculos.

La dificultad debe crecer de forma gradual, no volverse imposible rápidamente y debe tener un límite para que no sea imposible.

## 9. Score

El score representa cuánto tiempo logró sobrevivir el jugador.

Se calcula sobre el tiempo, no sobre la distancia recorrida, y se lleva a un
número más grande para que los umbrales de la progresión visual se alcancen en
minutos y no en media hora:

```text
puntaje = segundos vividos × 10
```

Con esta fórmula, un puntaje de 1250 corresponde a unos 2 minutos de partida.

Debe mostrarse permanentemente durante la partida.

Ejemplo:

```text
SCORE: 1250
```

## 10. Game Over

Cuando el jugador colisiona con un obstáculo debe aparecer una pantalla de Game Over.

Conceptualmente:

```text
╔════════════════════════════╗
║                            ║
║        GAME OVER           ║
║                            ║
║       SCORE: 1250          ║
║                            ║
║   INGRESA TUS INICIALES    ║
║                            ║
╚════════════════════════════╝
```

Después se debe pasar al ingreso de las iniciales.

## 11. Iniciales

El jugador debe ingresar exactamente 3 letras.

La experiencia ideal es que se sienta como una máquina arcade.

Las letras pueden seleccionarse mediante las flechas del teclado.

La implementación puede hacerse de forma progresiva.

En este proyecto se implementa la pantalla dentro del propio juego, con las
flechas del teclado. Esa versión cumple a la vez el requisito mínimo de la
consigna (pedir 3 letras de estilo arcade) y el desafío opcional de reemplazar
la entrada por consola, así que no queda nada pendiente de ese lado.

## 12. Ranking

El ranking debe tener una estética de arcade.

Los datos se almacenarán localmente, en el archivo `ranking.txt` que acompaña al
proyecto. El ranking es histórico de esa máquina: conserva todas las partidas que
se jugaron en ella, sin importar quién las haya jugado. Como el trabajo es
individual, "todos los que jugaron" son los que usaron esa computadora.

El ranking será histórico y conservará las partidas anteriores.

El formato del archivo y el criterio de ordenamiento están definidos en
[ESPECIFICACION.md](ESPECIFICACION.md).

## 13. Estética del ranking HTML

`ranking.html` debe sentirse como una pantalla de puntuaciones de una máquina arcade y como una tabla de puntuaciones de Counter-Strike.

Las columnas que replican el scoreboard de CS son:

- **K**: cantidad de obstáculos de tipo Persona superados en esa partida.
- **D**: cantidad de game over acumulados de ese jugador, es decir, el total de
  partidas que tiene registradas con esas iniciales.
- **K/D**: la división de K por D.

No se usa la columna A (asistencias). Cada partida es una muerte, así que K y D
miden cosas distintas y el ratio es puramente decorativo, con la misma función
visual que tiene en un arcade.

El valor de D no se guarda en el archivo: se calcula contando cuántas filas
tienen esas mismas iniciales. Así nunca queda desincronizado del historial real.

## 14. Detalles

- Mensajes de Game Over.
- Mensajes al superar determinados scores.
- Referencias a situaciones conocidas por jugadores de CS.
- Elementos absurdos como obstáculos.

Los mensajes de Game Over dependen del equipo elegido:

```text
YOU GOT FLASHED
TERRORISTS WIN
COUNTER-TERRORISTS WIN
```

Los mensajes por puntaje se disparan al cruzar los mismos umbrales de la
progresión visual, para que ambas secciones hablen el mismo idioma:

```text
500   → primera zona superada
1000  → a mitad de camino
1500  → zona avanzada alcanzada
```

Deben aparecer según el personaje elegido y la situación en que se pierde la
partida.

## 15. Sonido

Agregar sonidos como:

- Salto.
- Colisión.
- Game Over.
- Inicio de partida.
- Confirmación de iniciales.

Los sonidos deben utilizarse con moderación.

El juego debe funcionar aunque los sonidos no estén disponibles.

## 16. Filosofía del proyecto

El proyecto debe seguir dos principios:

- Simple: La mecánica debe poder entenderse inmediatamente.
- Divertido: Debe sentirse como un pequeño juego arcade.
