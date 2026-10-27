"""Consola de comandos del juego, al estilo CS2.

Se abre con F12. Mientras esta abierta, la partida sigue corriendo pero los
eventos van solo a la consola: asi se puede escribir un codigo sin que el
personaje salte o se agache.

El archivo tiene dos partes, como el resto del proyecto:

1. los comandos (``ejecutar``), que no dependen de pygame y se pueden probar
   por separado;
2. la ``Consola``, que se encarga del overlay, el teclado y el historial.

Los comandos nunca lanzan una excepcion hacia afuera: devuelven un texto de
error y el juego sigue andando.
"""
from dataclasses import dataclass

import pygame

import constantes
import obstaculo
import sonido


class ErrorDeComando(Exception):
    """Un error esperable: argumento invalido, comando fuera de contexto."""


# --- Ayudantes de parseo --------------------------------------------------

def _a_booleano(texto):
    """Convierte on/off (y sinónimos) a True/False."""
    valor = texto.strip().lower()
    if valor in ("on", "si", "sí", "1", "true", "activar"):
        return True
    if valor in ("off", "no", "0", "false", "desactivar"):
        return False
    raise ErrorDeComando(f"se esperaba on u off, no '{texto}'")


def _guardar_config(juego):
    """Pide guardar la config, si el juego lo soporta."""
    guardar = getattr(juego, "guardar_config", None)
    if callable(guardar):
        try:
            guardar()
        except Exception:
            pass


def _cheats(juego):
    cheats = getattr(juego, "cheats", None)
    if not isinstance(cheats, dict):
        raise ErrorDeComando("este juego no tiene cheats disponibles")
    return cheats


def _alternar_cheat(juego, clave, etiqueta):
    cheats = _cheats(juego)
    cheats[clave] = not bool(cheats.get(clave, False))
    estado = "ON" if cheats[clave] else "OFF"
    return f"{etiqueta}: {estado}"


def _ir_a_escena(juego, nombre):
    cambiar = getattr(juego, "cambiar_escena", None)
    if not callable(cambiar):
        raise ErrorDeComando("el juego no puede cambiar de escena")
    try:
        cambiar(nombre)
    except KeyError:
        raise ErrorDeComando(f"la escena '{nombre}' no existe")
    return f"Escena: {nombre}"


# --- Comandos -------------------------------------------------------------

def _cmd_help(juego, argumentos):
    if argumentos:
        comando = POR_NOMBRE.get(argumentos[0].lower())
        if comando is None:
            raise ErrorDeComando(f"no existe el comando '{argumentos[0]}'")
        alias = ", ".join(comando.alias) if comando.alias else "ninguno"
        return (
            f"{comando.nombre}: {comando.descripcion}\n"
            f"  uso: {comando.uso}\n"
            f"  alias: {alias}"
        )

    lineas = ["Comandos disponibles:"]
    for comando in COMANDOS:
        lineas.append(f"  {comando.nombre:<14} {comando.descripcion}")
    lineas.append("Escribi 'help <comando>' para ver el uso y los alias.")
    return "\n".join(lineas)


def _cmd_cheats(juego, argumentos):
    cheats = _cheats(juego)
    lineas = ["Estado de los cheats:"]
    for clave, etiqueta in (
        ("god", "god"),
        ("wallhack", "wallhack"),
        ("jumper", "jumper"),
        ("speedyg", "speedyg"),
    ):
        estado = "ON" if cheats.get(clave) else "OFF"
        lineas.append(f"  {etiqueta:<10} {estado}")
    return "\n".join(lineas)


def _cmd_god(juego, argumentos):
    return _alternar_cheat(juego, "god", "GOD")


def _cmd_wallhack(juego, argumentos):
    return _alternar_cheat(juego, "wallhack", "WALLHACK")


def _cmd_jumper(juego, argumentos):
    return _alternar_cheat(juego, "jumper", "JUMPER")


def _cmd_speedyg(juego, argumentos):
    return _alternar_cheat(juego, "speedyg", "SPEEDYG")


def _cmd_tutorial(juego, argumentos):
    return _ir_a_escena(juego, "tutorial")


def _cmd_sonido(juego, argumentos):
    if not argumentos:
        raise ErrorDeComando("uso: sonido on|off")
    valor = _a_booleano(argumentos[0])
    juego.sonido_habilitado = valor
    try:
        sonido.set_activo(valor)
    except Exception:
        pass
    _guardar_config(juego)
    return f"Sonido: {'ON' if valor else 'OFF'}"


def _cmd_tutorial_auto(juego, argumentos):
    if not argumentos:
        raise ErrorDeComando("uso: tutorial_auto on|off")
    valor = _a_booleano(argumentos[0])
    juego.tutorial_habilitado = valor
    _guardar_config(juego)
    return f"Tutorial automatico: {'ON' if valor else 'OFF'}"


def _cmd_restart(juego, argumentos):
    return _ir_a_escena(juego, "juego")


def _cmd_menu(juego, argumentos):
    return _ir_a_escena(juego, "titulo")


def _cmd_spawn(juego, argumentos):
    escena = getattr(juego, "escena", None)
    generar = getattr(escena, "_generar_obstaculo", None)
    if not callable(generar):
        raise ErrorDeComando("spawn solo funciona durante la partida")

    tipos = _TIPOS_OBSTACULO
    if not argumentos:
        raise ErrorDeComando("uso: spawn " + "|".join(tipos))
    tipo = argumentos[0].lower()
    if tipo not in tipos:
        raise ErrorDeComando(
            f"tipo invalido: '{tipo}'. Opciones: " + "|".join(tipos)
        )
    generar(tipo)
    return f"Obstaculo generado: {tipo}"


def _cmd_rank(juego, argumentos):
    abrir = getattr(juego, "abrir_ranking", None)
    if not callable(abrir):
        raise ErrorDeComando("el juego no puede abrir el ranking")
    abrir()
    return "Ranking abierto en el navegador."


def _cmd_clear(juego, argumentos):
    consola = getattr(juego, "consola", None)
    limpiar = getattr(consola, "limpiar", None)
    if callable(limpiar):
        limpiar()
    return ""


def _cmd_quit(juego, argumentos):
    salir = getattr(juego, "salir", None)
    if not callable(salir):
        raise ErrorDeComando("el juego no puede cerrarse desde aca")
    salir()
    return "Saliendo..."


# --- Registro de comandos -------------------------------------------------

_TIPOS_OBSTACULO = tuple(getattr(obstaculo, "TIPOS", ()))


@dataclass(frozen=True)
class Comando:
    nombre: str
    alias: tuple
    descripcion: str
    uso: str
    funcion: object


COMANDOS = (
    Comando("help", ("ayuda", "?"), "Lista los comandos o detalla uno.",
            "help [comando]", _cmd_help),
    Comando("cheats", ("trampas",), "Muestra el estado de los cheats.",
            "cheats", _cmd_cheats),
    Comando("god", ("inmortal", "dios"), "Alterna la invulnerabilidad.",
            "god", _cmd_god),
    Comando("wallhack", ("wh",), "Marca el borde de las personas.",
            "wallhack", _cmd_wallhack),
    Comando("jumper", ("salto",), "Duplica la velocidad del salto (4x de alto).",
            "jumper", _cmd_jumper),
    Comando("speedyg", ("speed",), "Alterna el juego al doble de velocidad.",
            "speedyg", _cmd_speedyg),
    Comando("tutorial", (), "Vuelve a abrir el tutorial.",
            "tutorial", _cmd_tutorial),
    Comando("sonido", (), "Activa o desactiva el audio y lo guarda.",
            "sonido on|off", _cmd_sonido),
    Comando("tutorial_auto", (), "Activa o desactiva el tutorial automatico.",
            "tutorial_auto on|off", _cmd_tutorial_auto),
    Comando("restart", ("reiniciar",), "Reinicia la partida con el equipo actual.",
            "restart", _cmd_restart),
    Comando("menu", ("titulo",), "Vuelve a la pantalla de titulo.",
            "menu", _cmd_menu),
    Comando("spawn", (), "Genera un obstaculo durante la partida.",
            "spawn " + "|".join(_TIPOS_OBSTACULO), _cmd_spawn),
    Comando("rank", ("ranking",), "Abre ranking.html en el navegador.",
            "rank", _cmd_rank),
    Comando("clear", ("cls", "limpiar"), "Limpia el historial de la consola.",
            "clear", _cmd_clear),
    Comando("quit", ("salir",), "Cierra el juego.",
            "quit", _cmd_quit),
)

POR_NOMBRE = {}
for _comando in COMANDOS:
    POR_NOMBRE[_comando.nombre] = _comando
    for _alias in _comando.alias:
        POR_NOMBRE[_alias] = _comando

NOMBRES = tuple(sorted(POR_NOMBRE))


def _color_de(texto):
    """El color con el que se muestra una respuesta."""
    if texto.startswith(("Error", "Comando desconocido")):
        return constantes.COLOR_CONSOLA_ERROR
    return constantes.COLOR_CONSOLA_TEXTO


def ejecutar(linea, juego):
    """Ejecuta una linea y devuelve el texto de respuesta.

    Siempre devuelve un string: los errores se informan como texto y nunca
    cortan el juego.
    """
    try:
        partes = linea.strip().split()
        if not partes:
            return ""
        comando = POR_NOMBRE.get(partes[0].lower())
        if comando is None:
            return (
                f"Comando desconocido: {partes[0]}. "
                "Escribi 'help' para ver la lista."
            )
        return comando.funcion(juego, partes[1:]) or ""
    except ErrorDeComando as error:
        return f"Error: {error}"
    except Exception as error:
        return f"Error inesperado: {error}"


# --- La consola en pantalla -----------------------------------------------

class Consola:
    """El overlay de la consola: teclado, historial y dibujo."""

    def __init__(self, juego):
        self.juego = juego
        # Se deja accesible desde el juego para que el comando 'clear' y las
        # pruebas puedan hablar con esta misma instancia.
        juego.consola = self
        self.abierta = False
        self.texto = ""
        self.historial = []
        self.indice_historial = 0
        self.salida = []
        self.desplazamiento = 0
        self.tiempo = 0.0
        self.fuente = self._elegir_fuente()

    def _elegir_fuente(self):
        fuentes = getattr(self.juego, "fuentes", {}) or {}
        return fuentes.get("consola") or fuentes.get("etiqueta")

    # --- Estado

    def alternar(self):
        if self.abierta:
            self.cerrar()
        else:
            self.abrir()

    def abrir(self):
        self.abierta = True
        self.tiempo = 0.0
        # Si venia agachado o con el click derecho apretado, la escena no va a
        # recibir el KEYUP mientras la consola este abierta: se suelta ahora.
        liberar = getattr(getattr(self.juego, "escena", None), "liberar_controles", None)
        if callable(liberar):
            liberar()
        try:
            pygame.key.set_repeat(400, 40)
        except Exception:
            pass
        if not self.salida:
            self.escribir(
                "Consola de Counter-Strike: Runner. Escribi 'help'.",
                constantes.COLOR_CONSOLA_AYUDA,
            )

    def cerrar(self):
        self.abierta = False
        self.texto = ""
        try:
            pygame.key.set_repeat()
        except Exception:
            pass

    def limpiar(self):
        self.salida = []
        self.desplazamiento = 0

    # --- Eventos

    def manejar_eventos(self, evento):
        if not self.abierta:
            return

        if evento.type == pygame.KEYDOWN:
            if evento.key in (pygame.K_F12, pygame.K_BACKQUOTE, pygame.K_ESCAPE):
                self.cerrar()
                return
            if evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.ejecutar_texto()
                return
            if evento.key == pygame.K_BACKSPACE:
                self.texto = self.texto[:-1]
                return
            if evento.key == pygame.K_TAB:
                self._completar()
                return
            if evento.key == pygame.K_UP:
                self._mover_historial(-1)
                return
            if evento.key == pygame.K_DOWN:
                self._mover_historial(1)
                return
            if evento.key == pygame.K_PAGEUP:
                self._desplazar(self._lineas_visibles())
                return
            if evento.key == pygame.K_PAGEDOWN:
                self._desplazar(-self._lineas_visibles())
                return

            caracter = getattr(evento, "unicode", "")
            if (caracter and caracter.isprintable()
                    and len(self.texto) < constantes.MAX_TEXTO_CONSOLA):
                self.texto += caracter

        elif evento.type == pygame.MOUSEWHEEL:
            self._desplazar(evento.y * 3)

    def ejecutar_texto(self):
        linea = self.texto
        self.texto = ""
        if not linea.strip():
            return

        self.historial.append(linea)
        if len(self.historial) > constantes.MAX_HISTORIAL_CONSOLA:
            self.historial.pop(0)
        self.indice_historial = len(self.historial)

        self.escribir("> " + linea, constantes.COLOR_CONSOLA_PROMPT)
        respuesta = ejecutar(linea, self.juego)
        for renglon in respuesta.splitlines():
            self.escribir(renglon, _color_de(renglon))

    def escribir(self, texto, color=None):
        self.salida.append(
            (texto, color or constantes.COLOR_CONSOLA_TEXTO)
        )
        if len(self.salida) > constantes.MAX_LINEAS_CONSOLA:
            del self.salida[: len(self.salida) - constantes.MAX_LINEAS_CONSOLA]
        self.desplazamiento = 0

    def _completar(self):
        prefijo = self.texto.strip().lower()
        if not prefijo or " " in prefijo:
            return
        opciones = [nombre for nombre in NOMBRES if nombre.startswith(prefijo)]
        if len(opciones) == 1:
            comando = POR_NOMBRE[opciones[0]]
            self.texto = comando.nombre + " "
        elif opciones:
            self.escribir(
                "Sugerencias: " + ", ".join(opciones),
                constantes.COLOR_CONSOLA_AYUDA,
            )

    def _mover_historial(self, paso):
        if not self.historial:
            return
        self.indice_historial = max(
            0, min(len(self.historial), self.indice_historial + paso)
        )
        if self.indice_historial == len(self.historial):
            self.texto = ""
        else:
            self.texto = self.historial[self.indice_historial]

    def _lineas_visibles(self):
        _, alto = self._area_de_salida()
        linea = max(1, self.fuente.get_linesize())
        return max(1, alto // linea)

    def _desplazar(self, paso):
        maximo = max(0, len(self.salida) - self._lineas_visibles())
        self.desplazamiento = max(
            0, min(maximo, self.desplazamiento + paso)
        )

    def actualizar(self, delta):
        self.tiempo += delta

    # --- Dibujo

    def _panel(self):
        alto = min(constantes.ALTO_CONSOLA, constantes.ALTO)
        return pygame.Rect(0, constantes.ALTO - alto, constantes.ANCHO, alto)

    def _area_de_salida(self):
        panel = self._panel()
        inicio = panel.y + 34
        fin = panel.bottom - 44
        return inicio, max(1, fin - inicio)

    def dibujar(self, superficie):
        if not self.abierta:
            return

        panel = self._panel()
        capa = pygame.Surface(panel.size, pygame.SRCALPHA)
        capa.fill((*constantes.COLOR_CONSOLA_FONDO, constantes.ALFA_CONSOLA_FONDO))
        superficie.blit(capa, panel.topleft)
        pygame.draw.line(
            superficie,
            constantes.COLOR_ACENTO,
            (panel.x, panel.y),
            (panel.right, panel.y),
            2,
        )

        self._dibujar_cabecera(superficie, panel)
        self._dibujar_salida(superficie, panel)
        self._dibujar_entrada(superficie, panel)

    def _dibujar_cabecera(self, superficie, panel):
        pygame.draw.line(
            superficie,
            constantes.COLOR_CONSOLA_AYUDA,
            (panel.x + 14, panel.y + 22),
            (panel.right - 14, panel.y + 22),
            1,
        )
        superficie.blit(
            self.fuente.render(
                "CONSOLA   F12/ESC: cerrar   ENTER: ejecutar   "
                "ARRIBA/ABAJO: historial   TAB: completar",
                True,
                constantes.COLOR_CONSOLA_AYUDA,
            ),
            (panel.x + 14, panel.y + 4),
        )

    def _dibujar_salida(self, superficie, panel):
        inicio, alto = self._area_de_salida()
        linea_alto = max(1, self.fuente.get_linesize())
        visibles = max(1, alto // linea_alto)

        fin = len(self.salida) - self.desplazamiento
        principio = max(0, fin - visibles)
        recorte = pygame.Rect(
            panel.x + 10, inicio, panel.width - 20, alto
        )
        anterior = superficie.get_clip()
        superficie.set_clip(recorte)
        for indice, (texto, color) in enumerate(self.salida[principio:fin]):
            superficie.blit(
                self.fuente.render(texto, True, color),
                (panel.x + 16, inicio + indice * linea_alto),
            )
        superficie.set_clip(anterior)

        if self.desplazamiento:
            aviso = self.fuente.render(
                f"^ {self.desplazamiento} linea(s) mas arriba",
                True,
                constantes.COLOR_CONSOLA_AYUDA,
            )
            superficie.blit(
                aviso, (panel.right - aviso.get_width() - 16, inicio)
            )

    def _dibujar_entrada(self, superficie, panel):
        y = panel.bottom - 34
        pygame.draw.line(
            superficie,
            constantes.COLOR_CONSOLA_AYUDA,
            (panel.x + 14, y - 6),
            (panel.right - 14, y - 6),
            1,
        )
        prompt = "> "
        ancho_prompt = self.fuente.size(prompt)[0]
        disponible = panel.width - 32 - ancho_prompt
        texto = self._texto_que_entra(self.texto, disponible)

        superficie.blit(
            self.fuente.render(prompt, True, constantes.COLOR_CONSOLA_PROMPT),
            (panel.x + 16, y),
        )
        superficie.blit(
            self.fuente.render(texto, True, constantes.COLOR_CONSOLA_TEXTO),
            (panel.x + 16 + ancho_prompt, y),
        )

        if _parpadea(self.tiempo):
            x_cursor = panel.x + 16 + ancho_prompt + self.fuente.size(texto)[0]
            alto = self.fuente.get_height()
            pygame.draw.rect(
                superficie,
                constantes.COLOR_CONSOLA_PROMPT,
                pygame.Rect(x_cursor, y + 2, 2, alto - 4),
            )

        ayuda = self.fuente.render(
            "ENTER: ejecutar   ·   F12/ESC: cerrar",
            True,
            constantes.COLOR_CONSOLA_AYUDA,
        )
        superficie.blit(
            ayuda, (panel.right - ayuda.get_width() - 16, panel.bottom - 16)
        )

    def _texto_que_entra(self, texto, ancho):
        """Recorta el principio del texto si no entra, para ver el final."""
        if self.fuente.size(texto)[0] <= ancho:
            return texto
        recortado = texto
        while recortado and self.fuente.size("..." + recortado)[0] > ancho:
            recortado = recortado[1:]
        return "..." + recortado


def _parpadea(tiempo, periodo=constantes.SEGUNDOS_CURSOR_CONSOLA):
    return (tiempo % (periodo * 2)) < periodo
