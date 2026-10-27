"""Datos del ranking historico.

Este modulo no sabe nada de Pygame ni de HTML: solo lee, valida y agrega
partidas en ranking.txt. Asi la generacion de la pagina se puede probar por
separado, igual que el resto de las funciones puras del juego.

Formato de una linea, definido en docs/ESPECIFICACION.md:

    INICIALES;PUNTAJE;EQUIPO;AAAA-MM-DD HH:MM:SS;PERSONAS

Las iniciales tienen siempre tres letras. El campo PERSONAS es la cantidad de
obstaculos de tipo persona superados en esa partida.
"""
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


RUTA_RANKING = Path(__file__).resolve().with_name("ranking.txt")

FORMATO_FECHA = "%Y-%m-%d %H:%M:%S"
LARGO_INICIALES = 3
CANTIDAD_EN_RANKING = 10
ALFABETO = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
EQUIPOS = ("CT", "T")


@dataclass(frozen=True)
class Partida:
    """Una partida guardada, ya validada."""

    iniciales: str
    puntaje: int
    equipo: str
    fecha: datetime
    personas: int

    def linea(self):
        """La representacion exacta que se escribe en ranking.txt."""
        return "{};{};{};{};{}".format(
            self.iniciales,
            self.puntaje,
            self.equipo,
            self.fecha.strftime(FORMATO_FECHA),
            self.personas,
        )


def validar_iniciales(iniciales):
    """Devuelve las iniciales en mayusculas, o lanza ValueError."""
    texto = str(iniciales).strip().upper()
    if len(texto) != LARGO_INICIALES:
        raise ValueError("las iniciales deben tener 3 letras")
    if any(letra not in ALFABETO for letra in texto):
        raise ValueError("las iniciales solo pueden ser letras de la A a la Z")
    return texto


def validar_equipo(equipo):
    """Devuelve el equipo normalizado, o lanza ValueError."""
    texto = str(equipo).strip().upper()
    if texto not in EQUIPOS:
        raise ValueError("el equipo debe ser CT o T")
    return texto


def _validar_entero(valor, nombre, minimo=0):
    """Convierte un entero y comprueba que no sea negativo."""
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        raise ValueError("{} debe ser un numero entero".format(nombre))

    if numero < minimo:
        raise ValueError("{} no puede ser negativo".format(nombre))
    return numero


def parsear_linea(linea):
    """Convierte una linea en Partida.

    Devuelve None para una linea vacia. Si la linea existe pero esta mal
    formada lanza ValueError; `leer_partidas` se encarga de saltearla con un
    aviso para que un archivo editado a mano no rompa el juego.
    """
    texto = linea.strip()
    if not texto:
        return None

    campos = texto.split(";")
    if len(campos) != 5:
        raise ValueError("se esperaban 5 campos separados por punto y coma")

    iniciales = validar_iniciales(campos[0])
    puntaje = _validar_entero(campos[1], "el puntaje")
    equipo = validar_equipo(campos[2])

    try:
        fecha = datetime.strptime(campos[3].strip(), FORMATO_FECHA)
    except ValueError:
        raise ValueError("la fecha debe tener el formato AAAA-MM-DD HH:MM:SS")

    personas = _validar_entero(campos[4], "la cantidad de personas")
    return Partida(iniciales, puntaje, equipo, fecha, personas)


def _avisar_por_defecto(mensaje):
    """Aviso para una linea invalida. No corta la lectura del archivo."""
    print("AVISO ranking.txt: {}".format(mensaje))


def leer_partidas(ruta=RUTA_RANKING, avisar=None):
    """Lee todas las partidas validas de `ruta`.

    Si el archivo no existe se crea vacio. Las lineas mal formadas se saltean
    con un aviso, asi que el archivo siempre se puede recuperar a mano.
    """
    ruta = Path(ruta)
    avisar = avisar or _avisar_por_defecto

    if not ruta.exists():
        ruta.touch()
        return []

    partidas = []
    with ruta.open("r", encoding="utf-8") as archivo:
        for numero, linea in enumerate(archivo, start=1):
            try:
                partida = parsear_linea(linea)
            except ValueError as error:
                avisar("linea {}: {}".format(numero, error))
                continue

            if partida is not None:
                partidas.append(partida)

    return partidas


def agregar_partida(ruta, iniciales, puntaje, equipo, personas, fecha=None):
    """Agrega una partida al final del archivo y la devuelve.

    Nunca sobreescribe: el ranking es historico. Si el archivo no existe lo
    crea, asi que la primera partida tampoco puede fallar por eso.
    """
    ruta = Path(ruta)
    partida = Partida(
        validar_iniciales(iniciales),
        _validar_entero(puntaje, "el puntaje"),
        validar_equipo(equipo),
        fecha or datetime.now().replace(microsecond=0),
        _validar_entero(personas, "la cantidad de personas"),
    )

    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("a", encoding="utf-8", newline="\n") as archivo:
        archivo.write(partida.linea() + "\n")

    return partida


def clasificar(partidas):
    """Ordena para el ranking: puntaje descendente y empate a favor del viejo.

    La fecha se usa como segundo criterio, no como texto: asi el orden es el
    mismo aunque el formato cambie de ancho.
    """
    return sorted(partidas, key=lambda partida: (-partida.puntaje, partida.fecha))


def top(partidas, cantidad=CANTIDAD_EN_RANKING):
    """Las mejores `cantidad` partidas, ya ordenadas."""
    return clasificar(partidas)[:cantidad]


def contar_por_iniciales(partidas):
    """Cuantas partidas tiene cada par de iniciales (la columna D)."""
    cantidades = {}
    for partida in partidas:
        cantidades[partida.iniciales] = cantidades.get(partida.iniciales, 0) + 1
    return cantidades


def ratio(k, d):
    """K/D con un decimal. D nunca es cero porque sale de contar partidas."""
    return "{:.1f}".format(k / d if d else 0.0)
