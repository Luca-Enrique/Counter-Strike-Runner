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

## Pruebas

```bash
python pruebas.py
```

Devuelve `0` si todo pasa y `1` si algo falla, así que sirve para automatizar el
control. Solo verifica funciones puras, sin abrir ventana: corre incluso en una
máquina sin pantalla.

Las pruebas cubren el escalado con letterbox, el centrado de la imagen, el
recorte de delta y la altura del salto. Cuando se agregue el personaje, la física
y el ranking, se suman las suyas.

## Estructura de archivos

```text
Counter-Strike-Runner/
├── juego.py             # punto de entrada: ventana, bucle y escenas
├── constantes.py        # todos los valores ajustables
├── pruebas.py           # verificaciones automáticas
├── generar_ranking.py   # lee ranking.txt y arma ranking.html (no importa pygame)
├── ranking.txt          # datos, crece con cada partida
├── estilos.css          # estilos de la página
├── ranking.html         # se regenera en cada partida
├── assets/              # imágenes y sonidos
└── docs/                # consigna, temática y especificación
```

`ranking.txt` y `ranking.html` están versionados a propósito: son entregables de
la consigna, así que su estado forma parte del proyecto.

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
