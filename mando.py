"""Soporte de mando para menus y partida.

El mando no habla con las escenas directamente: traduce botones, D-pad y stick
a un puñado de acciones (``confirmar``, ``secundario``, ``atras``, direcciones)
y ``juego.py`` las convierte en los mismos eventos de teclado que ya usan las
escenas. Asi el teclado y el raton siguen funcionando igual y no hay dos
caminos de entrada que mantener.

Para que un DualShock/DualSense no dependa de los indices crudos de sus
botones, se usa la API de controladores de pygame (``pygame._sdl2.controller``),
que normaliza Cross/Circle/Options/Share a los botones A/B/Start/Back de SDL.
Si el mando no tiene mapping, se cae al respaldo crudo de ``pygame.joystick``.

Todo falla en silencio: sin mando, con un mando desconocido o si pygame no
expone la API de controladores, el juego arranca y se juega con teclado.
"""
import pygame

import constantes


def _constante(nombre, defecto):
    """Una constante de pygame, o el valor de respaldo si no existe."""
    return getattr(pygame, nombre, defecto)


# Botones normalizados de SDL. En PlayStation, A es Cross, B es Circle,
# Start es Options y Back es Share. En Xbox son A, B, Start y Back.
BOTON_A = _constante("CONTROLLER_BUTTON_A", 0)
BOTON_B = _constante("CONTROLLER_BUTTON_B", 1)
BOTON_BACK = _constante("CONTROLLER_BUTTON_BACK", 4)
BOTON_START = _constante("CONTROLLER_BUTTON_START", 6)
BOTON_ARRIBA = _constante("CONTROLLER_BUTTON_DPAD_UP", 11)
BOTON_ABAJO = _constante("CONTROLLER_BUTTON_DPAD_DOWN", 12)
BOTON_IZQUIERDA = _constante("CONTROLLER_BUTTON_DPAD_LEFT", 13)
BOTON_DERECHA = _constante("CONTROLLER_BUTTON_DPAD_RIGHT", 14)
EJE_X = _constante("CONTROLLER_AXIS_LEFTX", 0)
EJE_Y = _constante("CONTROLLER_AXIS_LEFTY", 1)

BOTONES_NORMALIZADOS = (
    (BOTON_A, "confirmar"),
    (BOTON_B, "secundario"),
    (BOTON_START, "inicio"),
    (BOTON_BACK, "atras"),
)

BOTONES_CRUDOS = (
    (constantes.MANDO_BOTON_A_CRUDO, "confirmar"),
    (constantes.MANDO_BOTON_B_CRUDO, "secundario"),
    (constantes.MANDO_BOTON_START_CRUDO, "inicio"),
    (constantes.MANDO_BOTON_BACK_CRUDO, "atras"),
)

ACCIONES_BOTON = tuple(accion for _, accion in BOTONES_NORMALIZADOS)

# Eventos que pertenecen al mando y no tienen que llegar a las escenas. Se
# consumen aunque el mando no este conectado.
EVENTOS_DE_MANDO = tuple(
    tipo
    for tipo in (
        _constante("JOYBUTTONDOWN", None),
        _constante("JOYBUTTONUP", None),
        _constante("JOYHATMOTION", None),
        _constante("JOYAXISMOTION", None),
        _constante("JOYBALLMOTION", None),
        _constante("CONTROLLERBUTTONDOWN", None),
        _constante("CONTROLLERBUTTONUP", None),
        _constante("CONTROLLERAXISMOTION", None),
        _constante("CONTROLLERTOUCHPADDOWN", None),
        _constante("CONTROLLERTOUCHPADMOTION", None),
        _constante("CONTROLLERTOUCHPADUP", None),
        _constante("CONTROLLERSENSORUPDATE", None),
    )
    if tipo is not None
)

EVENTOS_DE_CONEXION = tuple(
    tipo
    for tipo in (
        _constante("JOYDEVICEADDED", None),
        _constante("CONTROLLERDEVICEADDED", None),
    )
    if tipo is not None
)

EVENTOS_DE_DESCONEXION = tuple(
    tipo
    for tipo in (
        _constante("JOYDEVICEREMOVED", None),
        _constante("CONTROLLERDEVICEREMOVED", None),
    )
    if tipo is not None
)


# --- Funciones puras -----------------------------------------------------
# Se pueden probar sin conectar ningun mando.

def direccion_de_hat(valor):
    """La direccion de un D-pad expuesto como hat, o None si esta centrado.

    pygame usa (x, y) con y positivo hacia arriba. Se prioriza lo vertical
    porque en la partida arriba/abajo son saltar/agachar.
    """
    x, y = valor
    if y > 0:
        return "arriba"
    if y < 0:
        return "abajo"
    if x < 0:
        return "izquierda"
    if x > 0:
        return "derecha"
    return None


def direccion_de_botones(arriba, abajo, izquierda, derecha):
    """La direccion de un D-pad expuesto como botones, o None."""
    if arriba:
        return "arriba"
    if abajo:
        return "abajo"
    if izquierda:
        return "izquierda"
    if derecha:
        return "derecha"
    return None


def direccion_de_ejes(x, y, zona_muerta=constantes.MANDO_ZONA_MUERTA):
    """La direccion dominante del stick, o None si esta dentro de la zona muerta.

    Se elige un solo eje para que un movimiento diagonal no dispare dos
    acciones a la vez. En SDL, el eje Y crece hacia abajo.
    """
    x = x or 0.0
    y = y or 0.0
    if abs(x) < zona_muerta and abs(y) < zona_muerta:
        return None
    if abs(y) >= abs(x):
        return "abajo" if y > 0 else "arriba"
    return "derecha" if x > 0 else "izquierda"


# --- El mando ------------------------------------------------------------

class Mando:
    """Un mando conectado y las acciones que produjo desde el ultimo fotograma."""

    def __init__(self, controlador=None, autodetectar=True):
        self._controlador = None
        self._joystick = None
        self._modo = None
        self._botones_anteriores = {}
        self._direccion = None
        self._tiempo_direccion = 0.0
        self._espera_repetir = constantes.MANDO_RETRASO_REPETICION
        self._esperando_centro = False
        self._desconectado = False

        if controlador is not None:
            # Camino de las pruebas: un controlador falso con get_button(),
            # get_axis() y attached().
            self._controlador = controlador
            self._modo = "controlador"
            self._preparar_estado()
        elif autodetectar:
            self.conectar()

    # --- Estado

    @property
    def activo(self):
        """True si hay un mando abierto."""
        return self._controlador is not None or self._joystick is not None

    def consumir_desconexion(self):
        """True una sola vez despues de que el mando se desconecto."""
        if self._desconectado:
            self._desconectado = False
            return True
        return False

    def reiniciar_direccion(self):
        """Olvida la direccion actual y espera a que el stick vuelva al centro.

        Se llama al cambiar de escena o al abrir/cerrar la consola. Asi una
        direccion que venia apretada no mueve sola la pantalla siguiente.
        """
        self._direccion = None
        self._tiempo_direccion = 0.0
        self._espera_repetir = constantes.MANDO_RETRASO_REPETICION
        self._esperando_centro = True

    def _preparar_estado(self):
        """Toma el estado actual como punto de partida.

        Si un boton ya estaba apretado al conectar, no se dispara solo: hay que
        soltarlo y volver a apretarlo.
        """
        self._botones_anteriores = {accion: False for accion in ACCIONES_BOTON}
        try:
            self._botones_anteriores.update(self._leer_botones())
        except Exception:
            pass
        try:
            self._direccion = self._leer_direccion()
        except Exception:
            self._direccion = None
        self._tiempo_direccion = 0.0
        self._espera_repetir = constantes.MANDO_RETRASO_REPETICION
        # Si el stick ya venia movido al conectar, no se dispara nada hasta
        # que vuelva al centro. Si estaba centrado, la primera direccion nueva
        # funciona enseguida.
        self._esperando_centro = self._direccion is not None
        if self._esperando_centro:
            self._direccion = None
        self._desconectado = False

    # --- Conexion

    def conectar(self):
        """Abre el primer mando disponible. Devuelve True si lo consiguio."""
        if self.activo:
            return True

        sdl = None
        try:
            pygame.joystick.init()
            import pygame._sdl2.controller as sdl_controller

            sdl_controller.init()
            sdl = sdl_controller
        except Exception:
            sdl = None

        try:
            cantidad = pygame.joystick.get_count()
        except Exception:
            cantidad = 0

        # Primero se intenta el camino normalizado, que es el que hace que un
        # DualShock/DualSense tenga los mismos botones que un mando de Xbox.
        if sdl is not None:
            for indice in range(cantidad):
                joystick = None
                try:
                    if not sdl.is_controller(indice):
                        continue
                    joystick = pygame.joystick.Joystick(indice)
                    joystick.init()
                    controlador = sdl.Controller.from_joystick(joystick)
                    self._controlador = controlador
                    self._joystick = joystick
                    self._modo = "controlador"
                    self._preparar_estado()
                    return True
                except Exception:
                    try:
                        if joystick is not None:
                            joystick.quit()
                    except Exception:
                        pass
                    continue

        # Respaldo crudo: sirve para mandos viejos o sin mapping. En Xbox los
        # indices coinciden; en otros mandos puede haber que ajustarlos.
        for indice in range(cantidad):
            joystick = None
            try:
                joystick = pygame.joystick.Joystick(indice)
                joystick.init()
                self._joystick = joystick
                self._controlador = None
                self._modo = "crudo"
                self._preparar_estado()
                return True
            except Exception:
                try:
                    if joystick is not None:
                        joystick.quit()
                except Exception:
                    pass
                continue

        return False

    def desconectar(self):
        """Cierra el mando y olvida todo lo que estaba apretado."""
        if self._controlador is not None:
            try:
                self._controlador.quit()
            except Exception:
                pass
        if self._joystick is not None:
            try:
                self._joystick.quit()
            except Exception:
                pass

        self._controlador = None
        self._joystick = None
        self._modo = None
        self._botones_anteriores = {}
        self.reiniciar_direccion()
        self._desconectado = True

    def manejar_evento(self, evento):
        """Procesa un evento de conexion. True si el evento era del mando.

        Los botones no se leen de los eventos: se consultan una vez por
        fotograma en ``actualizar()``. Asi el estado nunca queda a medias si se
        pierde un evento.
        """
        if evento.type in EVENTOS_DE_CONEXION:
            if not self.activo:
                self.conectar()
            return True

        if evento.type in EVENTOS_DE_DESCONEXION:
            if self.activo:
                self.desconectar()
            return True

        return evento.type in EVENTOS_DE_MANDO

    # --- Lectura

    def _leer_botones(self):
        """El estado de cada accion de boton en este instante."""
        estado = {}
        if self._modo == "controlador" and self._controlador is not None:
            for boton, accion in BOTONES_NORMALIZADOS:
                try:
                    presionado = bool(self._controlador.get_button(boton))
                except Exception:
                    presionado = False
                estado[accion] = estado.get(accion, False) or presionado
        elif self._modo == "crudo" and self._joystick is not None:
            for boton, accion in BOTONES_CRUDOS:
                try:
                    presionado = bool(self._joystick.get_button(boton))
                except Exception:
                    presionado = False
                estado[accion] = estado.get(accion, False) or presionado
        return estado

    def _leer_direccion(self):
        """La direccion actual del D-pad o del stick izquierdo."""
        if self._modo == "controlador" and self._controlador is not None:
            try:
                direccion = direccion_de_botones(
                    self._controlador.get_button(BOTON_ARRIBA),
                    self._controlador.get_button(BOTON_ABAJO),
                    self._controlador.get_button(BOTON_IZQUIERDA),
                    self._controlador.get_button(BOTON_DERECHA),
                )
            except Exception:
                direccion = None
            if direccion is not None:
                return direccion
            try:
                return direccion_de_ejes(
                    self._controlador.get_axis(EJE_X),
                    self._controlador.get_axis(EJE_Y),
                    constantes.MANDO_ZONA_MUERTA,
                )
            except Exception:
                return None

        if self._modo == "crudo" and self._joystick is not None:
            try:
                direccion = direccion_de_hat(
                    self._joystick.get_hat(constantes.MANDO_HAT_CRUDO)
                )
            except Exception:
                direccion = None
            if direccion is not None:
                return direccion
            try:
                return direccion_de_ejes(
                    self._joystick.get_axis(constantes.MANDO_EJE_X_CRUDO),
                    self._joystick.get_axis(constantes.MANDO_EJE_Y_CRUDO),
                    constantes.MANDO_ZONA_MUERTA,
                )
            except Exception:
                return None

        return None

    def _sigue_conectado(self):
        """False si el controlador avisa que ya no esta conectado."""
        if self._controlador is None:
            return True
        try:
            return bool(self._controlador.attached())
        except Exception:
            return True

    def actualizar(self, delta, repetir_direcciones=True):
        """Devuelve las acciones nuevas: (accion, presionado, repetido).

        Los botones se disparan una vez al apretar y una vez al soltar. Las
        direcciones se disparan al cambiar y, si se pide, se repiten mientras
        se mantienen apretadas.
        """
        if not self.activo:
            return []

        if not self._sigue_conectado():
            self.desconectar()
            return []

        acciones = []

        estado = self._leer_botones()
        for accion in ACCIONES_BOTON:
            presionado = bool(estado.get(accion, False))
            antes = bool(self._botones_anteriores.get(accion, False))
            if presionado != antes:
                acciones.append((accion, presionado, False))
            self._botones_anteriores[accion] = presionado

        direccion = self._leer_direccion()
        if self._esperando_centro:
            if direccion is None:
                self._esperando_centro = False
            else:
                direccion = None

        if direccion != self._direccion:
            if self._direccion is not None:
                acciones.append((self._direccion, False, False))
            self._direccion = direccion
            self._tiempo_direccion = 0.0
            self._espera_repetir = constantes.MANDO_RETRASO_REPETICION
            if direccion is not None:
                acciones.append((direccion, True, False))
        elif direccion is not None and repetir_direcciones:
            self._tiempo_direccion += max(0.0, delta)
            if self._tiempo_direccion >= self._espera_repetir:
                self._tiempo_direccion = 0.0
                self._espera_repetir = constantes.MANDO_INTERVALO_REPETICION
                acciones.append((direccion, True, True))

        return acciones
