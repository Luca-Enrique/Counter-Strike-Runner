# Trabajo práctico: Juego Arcade en Python (Pygame + HTML/CSS)

Este trabajo integra los contenidos de la cursada: variables, condicionales, bucles, funciones, manejo de archivos, listas, ordenamiento de datos y generación de HTML/CSS desde Python, sumando el uso de la librería Pygame para programar un juego visual.

**Modalidad:** individual. Cada alumno entrega su propio proyecto.

**Fecha de entrega:** viernes 16 de octubre de 2026 (ajustable según el calendario de la cátedra).

## Descripción del proyecto

Deben programar un juego 2D simple tipo "corredor infinito", al estilo del dinosaurio de Chrome: un personaje que salta obstáculos que se mueven hacia él, con el objetivo de sobrevivir el mayor tiempo posible. El juego se construye 100% en Python con Pygame — no se usa HTML ni CSS para el juego en sí.

Al finalizar cada partida, el programa debe guardar el resultado y generar automáticamente una página con el ranking histórico de todos los que jugaron, mostrada con una estética retro tipo "recreativa arcade" (ranking.html + estilos.css).

## Requisitos funcionales mínimos

- Ventana de juego creada con Pygame, con un loop principal (game loop) que corre hasta el game over.
- Un personaje que puede saltar (tecla espacio) con una física simple de gravedad/velocidad.
- Al menos un obstáculo que se mueve hacia el jugador y debe esquivarse.
- Detección de colisión entre el jugador y el obstáculo que termina la partida.
- Puntaje que aumenta con el tiempo/distancia sobrevivida, mostrado en pantalla durante el juego.
- Dificultad creciente: la velocidad del juego debe aumentar a medida que pasa el tiempo.
- Al terminar la partida, pedir al jugador sus iniciales (3 letras, estilo arcade clásico) y guardar el resultado en un archivo ranking.txt que acumula todas las partidas jugadas (no se sobreescribe).
- Generar automáticamente ranking.html, mostrando el top 10 de puntajes ordenados de mayor a menor, con estilo aplicado desde estilos.css.
- El ranking.html debe abrirse solo en el navegador al finalizar cada partida.

## Estructura de archivos esperada

```text
proyecto_final/
├── juego.py             # el juego en Pygame
├── ranking.txt          # se genera y crece con cada partida jugada
├── generar_ranking.py   # lee ranking.txt y arma ranking.html
├── estilos.css
└── ranking.html         # se regenera después de cada partida
```

Pueden organizar el código en más funciones o módulos si lo consideran necesario, siempre que se respete esta separación de responsabilidades: el juego, el guardado de datos y la generación del ranking.

## Requisitos técnicos

- Python 3.10 o superior.
- Librería Pygame, instalada con `pip install pygame-ce`.
- IDE recomendado: Visual Studio Code, con la extensión de Python instalada.
- No está permitido usar frameworks web (Flask, Django, FastAPI, etc.) en la consigna base — el juego debe ser Python "puro" del lado del cliente. El uso de un framework web queda reservado para el desafío opcional avanzado (ver más abajo).

## Desafíos opcionales (puntos extra)

- En vez de pedir las iniciales por consola, armar una pantalla dentro del propio juego donde se elige cada letra con las flechas del teclado, tal como en las recreativas clásicas.
- obstáculos de distinta altura o que aparezcan en intervalos aleatorios, sonidos al saltar y al chocar, pantalla de inicio y de game over.
- reconstruir el juego (o una versión de él) con un backend en Flask que exponga la lógica como una API, y un frontend en HTML, CSS y JavaScript que la consuma con fetch. Esto permite, entre otras cosas, que el ranking se comparta entre distintas máquinas conectadas a un mismo servidor, en vez de quedar local a cada computadora.

## Documento explicativo (entrega obligatoria, en PDF)

Además del código, cada alumno debe entregar un documento en que explique el trabajo realizado. Debe incluir:

1. Portada con nombre, comisión y fecha de entrega.
2. Introducción: qué decidieron hacer y por qué.
3. Arquitectura del proyecto: qué hace cada archivo y cómo se relacionan entre sí.
4. Decisiones de diseño: cómo implementaron el salto y la física, la detección de colisión, el guardado del puntaje y la generación del ranking en HTML.
5. Capturas de pantalla: el juego en ejecución, el momento de ingresar las iniciales, y el ranking.html final mostrando el top 10.
6. Dificultades encontradas durante el desarrollo y cómo las resolvieron.
7. Instrucciones para instalar y ejecutar el proyecto desde cero.
8. (Opcional) Ideas de mejora a futuro para el juego.

## Entregables

- Código fuente completo (juego.py, generar_ranking.py y todo archivo auxiliar).
- ranking.txt con al menos algunas partidas de prueba ya jugadas.
- estilos.css.
- Documento explicativo en PDF, con las capturas de pantalla pedidas.

## Criterios de evaluación

| Criterio                                                          | Peso |
| ---------------------------------------------------------------- | ---- |
| Funcionamiento del juego (loop, salto, colisión)                  | 25%  |
| Sistema de puntaje y dificultad creciente                          | 15%  |
| Persistencia del ranking (guardado correcto en ranking.txt)       | 15%  |
| Generación de ranking.html con estilos de estilos.css             | 15%  |
| Calidad y prolijidad del código (funciones, nombres, comentarios) | 15%  |
| Documento explicativo (claridad, completitud, capturas)           | 15%  |
