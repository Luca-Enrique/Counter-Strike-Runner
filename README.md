# Counter-Strike: Runner

Juego arcade 2D tipo *corredor infinito* hecho con **Python + Pygame**. El
jugador corre automáticamente, salta y se agacha para esquivar obstáculos con
temática de Counter-Strike, y el puntaje se guarda en un ranking histórico que se
muestra en una página con estética de recreativa.

Trabajo práctico individual. Entrega: **viernes 16 de octubre de 2026**.

## Documentación

Toda la documentación del proyecto vive en [`docs/`](docs/). Antes de tocar
código, leer los tres archivos:

| Documento | Qué define |
| --- | --- |
| [`docs/CONSIGNAS.md`](docs/CONSIGNAS.md) | Lo que pide la cátedra: requisitos, entregables y criterios de evaluación. |
| [`docs/TEMATICA.md`](docs/TEMATICA.md) | Lo que define el proyecto: temática, mecánicas, progresión, ranking y estética. |
| [`docs/ESPECIFICACION.md`](docs/ESPECIFICACION.md) | Las decisiones técnicas y **todos los valores numéricos**. Es la fuente de verdad de las constantes. |

## Requisitos

- Python 3.10 o superior.
- Nada más: las dependencias se instalan desde `requirements.txt`.

## Instalación

Desde la raíz del proyecto:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Ejecución

```bash
python juego.py
```

## Estado actual

- Escenas: título, tutorial, elección de equipo, partida, game over e ingreso de
  iniciales.
- Tutorial: la primera vez que se juega aparece un recorrido de seis páginas
  antes de elegir equipo. Se puede volver a abrir con `T` o `Triángulo`/`Y`
  desde el título, o con el comando `tutorial` de la consola.
- Partida: salto, agachado, obstáculos, colisión, puntaje, fondos por zona y
  suelo con parallax.
- Mando: se puede jugar y navegar todos los menús con un mando de PlayStation o
  Xbox conectado por USB o Bluetooth. El teclado y el ratón siguen funcionando
  al mismo tiempo, y el mando se puede conectar o desconectar en caliente.
- Consola de comandos: `F12` abre una consola al estilo CS2 desde cualquier
  pantalla. Ahí viven los cheats y los comandos de configuración, reinicio y
  salida (ver más abajo).
- Ranking: las iniciales se guardan en `ranking.txt` al terminar cada partida, se
  regenera `ranking.html` y se abre solo en el navegador.
- Configuración: `config.json` guarda si el tutorial ya se vio y si el sonido
  está activo. Si falta o está roto, el juego arranca con los valores por
  defecto sin fallar.
- Completo: la consigna pide juego, guardado histórico y ranking HTML, y las tres
  partes están implementadas y cubiertas por pruebas.

## Controles

| Acción | Teclado y ratón | Mando |
| --- | --- | --- |
| Saltar | `SPACE`, `↑`, `W` o click izquierdo | `Cross` (A) o D-pad arriba |
| Agacharse | `↓`, `S` o click derecho | `Circle` (B), D-pad abajo o stick abajo |
| Confirmar | `SPACE`, `ENTER` o click izquierdo | `Cross` (A) u `Options` (Start) |
| Volver | `ESC` | `Circle` (B) o `Share` (Back) |
| Navegar menús | `A`/`D`, flechas o el ratón | D-pad o stick izquierdo |
| Abrir tutorial (título) | `T` | `Triángulo` (Y) |
| Borrar en iniciales | `BACKSPACE` | `Circle` (B) |

En la partida, `Cross` salta y `Circle` agacha mientras se mantiene apretado.
En los menús, el D-pad y el stick repiten el movimiento si se mantienen. El
mando se detecta solo al arrancar y también si se conecta después; si se
desconecta, el juego suelta el agachado para que el personaje no quede trabado.
Los mandos de PlayStation se normalizan con SDL, así que `Cross`/`Circle`/
`Options`/`Share` funcionan igual que `A`/`B`/`Start`/`Back` de Xbox. El D-pad
se lee por botones normalizados, por `hat` y por botones crudos 11-14, así que
también funciona en mandos que Windows expone sin mapping. Los ejes del stick se
normalizan a `-1..1` antes de aplicar la zona muerta, así que la deriva del mando
en reposo no mueve el menú ni bloquea el D-pad.

## Consola de comandos (F12)

`F12` (o `` ` `` en las notebooks que necesitan `Fn`) abre y cierra la consola.
La partida **sigue corriendo** detrás del panel, pero los eventos van solo a la
consola: mientras está abierta el personaje no salta, no se agacha y no recibe
clicks. Al abrirla se sueltan las teclas que pudieran haber quedado apretadas.

| Comando | Alias | Efecto |
| --- | --- | --- |
| `help [comando]` | `ayuda`, `?` | Lista los comandos o detalla uno. |
| `cheats` | `trampas` | Muestra el estado de los cuatro cheats. |
| `god` | `inmortal`, `dios` | Alterna la invulnerabilidad. |
| `wallhack` | `wh` | Marca el borde de las personas. |
| `jumper` | `salto` | Duplica la velocidad del salto (cuádruple de altura). |
| `speedyg` | `speed` | Alterna la partida al doble de velocidad. |
| `tutorial` | — | Vuelve a abrir el tutorial. |
| `sonido on\|off` | — | Activa o desactiva el audio y lo guarda. |
| `tutorial_auto on\|off` | — | Activa o desactiva el tutorial automático. |
| `restart` | `reiniciar` | Reinicia la partida con el equipo actual. |
| `menu` | `titulo` | Vuelve a la pantalla de título. |
| `spawn caja\|barril\|barricada\|c4\|persona\|proyectil` | — | Genera un obstáculo (solo en partida). |
| `rank` | `ranking` | Abre `ranking.html` en el navegador. |
| `clear` | `cls`, `limpiar` | Limpia el historial de la consola. |
| `quit` | `salir` | Cierra el juego. |

Teclas de la consola: `ENTER` ejecuta, `↑`/`↓` recorren el historial, `TAB`
completa el nombre del comando, `PageUp`/`PageDown` y la rueda mueven el
historial de salida, y `ESC`/`F12` cierran.

Los cheats son de la sesión: se apagan al cerrar el juego. El sonido y el
tutorial automático sí se guardan en `config.json`.

## Pruebas

```bash
python pruebas.py
```

Devuelve `0` si todo pasa y `1` si algo falla, así que sirve para automatizar el
control. No abre ventana: el controlador de video se pone en modo `dummy`, así
que corre incluso en una máquina sin pantalla.

Las pruebas cubren la resolución virtual y el letterbox, el recorte de delta, la
física del salto y del agachado, los controles de teclado, ratón y mando, el
tutorial, la configuración, la elección de equipo, los cheats, la consola de
comandos, los fondos por zona, los obstáculos, la colisión, el suelo, el game
over, el ingreso de iniciales, el formato de `ranking.txt` y la generación de
`ranking.html`.

## Ranking

Al chocar, el juego pasa por el ingreso de iniciales (3 letras, con las flechas y
con el teclado) y al confirmar:

1. agrega la partida al final de `ranking.txt` (nunca lo sobreescribe);
2. regenera `ranking.html` con el top 10;
3. abre la página en el navegador.

Los datos se leen, validan y ordenan en `ranking.py` y la página se arma en
`generar_ranking.py`, que se puede correr solo:

```bash
python generar_ranking.py
```

## Estructura de archivos

```text
Counter-Strike-Runner/
├── juego.py             # punto de entrada: ventana, bucle y escenas
├── consola.py           # consola F12, comandos y cheats
├── mando.py             # mando de PlayStation/Xbox, con hot-plug
├── personaje.py         # física y dibujo del jugador
├── obstaculo.py         # sprites y rectángulos de los obstáculos
├── fondo.py             # escenarios y suelo que se desplazan
├── constantes.py        # todos los valores ajustables
├── pruebas.py           # verificaciones automáticas
├── sonido.py            # carga y reproduce los SFX del juego
├── ranking.py           # datos: lee, valida y agrega en ranking.txt (sin pygame)
├── generar_ranking.py   # lee ranking.txt y arma ranking.html (no importa pygame)
├── config.json          # tutorial visto y sonido activo
├── ranking.txt          # datos, crece con cada partida
├── estilos.css          # estilos de la página
├── ranking.html         # se regenera en cada partida
├── assets/              # imágenes y sonidos
│   └── sonidos/         # efectos de sonido (.wav)
└── docs/                # consigna, temática y especificación
```

`config.json`, `ranking.txt` y `ranking.html` están versionados a propósito: el
config guarda las preferencias, y los dos últimos son entregables de la consigna,
así que su estado forma parte del proyecto.

## Flujo de trabajo

El proyecto usa un flujo de **dos ramas permanentes** más ramas de trabajo
temporales.

| Rama | Rol |
| --- | --- |
| `main` | El juego final y funcional. **Nunca se commitea directo.** Entra únicamente por Pull Request desde `develop`. |
| `develop` | El laboratorio. Acá se prueban las PR de todas las ramas de trabajo en conjunto, antes de integrar nada. |

### Reglas

1. `main` solo cambia por **PR desde `develop`**.
2. `develop` solo cambia por **PR desde una rama de trabajo**.
3. Toda rama de trabajo nace de `develop` actualizada.
4. Los merges usan **merge commit** (`--no-ff`), para que la historia muestre
   qué PR se integró.
5. **No se borra ninguna rama, ni en local ni en GitHub.** Jamás
   `git branch -d` ni `git branch -D`, nunca la casilla *Delete branch* al
   completar un PR. Una rama ya integrada deja de recibir trabajo, pero se
   queda en el repositorio para siempre: es parte del historial del proyecto.
6. `main` está **protegida** en GitHub: GitHub rechaza cualquier push directo y
   exige una Pull Request.

### Nombres de rama

```text
feat/    funcionalidad nueva      -> feat/salto-personaje
fix/     corrección de un bug     -> fix/colision-barril
chore/   tareas de mantenimiento  -> chore/entorno
docs/    documentación            -> docs/informe
```

### Commits

Conventional Commits, en español, siguiendo el mismo criterio que el resto de
los repositorios del curso:

```text
feat: Agrego el salto con gravedad al personaje
fix: Corrijo la colision con el barril
docs: Explico el formato de ranking.txt
chore: Agrego .gitignore y requirements.txt
```

### Cómo trabajo en una rama

```bash
git switch develop
git pull
git switch -c feat/mi-cambio
# ... escribir código, probarlo ...
git add -A
git commit -m "feat: Mi cambio"
git push -u origin feat/mi-cambio
```

Después se abre la Pull Request contra `develop` desde GitHub. Cuando `develop`
tiene todo lo integrado y andando, se abre la PR de `develop` contra `main`.

## Changelog

Los cambios del proyecto se anotan en [`CHANGELOG.md`](CHANGELOG.md), de la versión
más reciente a la más antigua.

Cada versión es un encabezado `## X.Y.Z - AAAA-MM-DD` con la fecha del día en que
se escribió, y abajo los cambios agrupados en `Agregado` y `Corregido`. No hay
tags de git ni releases: el número de versión vive únicamente en ese archivo.

Cuando se termina una tanda de trabajo, se agrega un encabezado nuevo arriba.
