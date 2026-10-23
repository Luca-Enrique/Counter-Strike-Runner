"""Gestor de SFX para Counter-Strike: Runner.

Carga y reproduce los sonidos desde assets/sonidos/. Si el mixer no está
disponible o falta algún archivo, falla silenciosamente para que el juego
nunca se rompa por audio.
"""
import os

import pygame

import constantes


RUTA_SONIDOS = os.path.join("assets", "sonidos")


def _ruta(nombre):
    """Ruta completa a un archivo de sonido."""
    return os.path.join(RUTA_SONIDOS, nombre)


SONIDOS = {}
HABILITADO = False


def inicializar():
    """Inicializa el mixer con configuración para baja latencia."""
    global HABILITADO
    try:
        if pygame.mixer.get_init() is None:
            pygame.mixer.pre_init(44100, -16, 2, 512)
            pygame.mixer.init()
        HABILITADO = pygame.mixer.get_init() is not None
    except Exception:
        HABILITADO = False


def cargar():
    """Carga todos los sonidos en caché."""
    global HABILITADO
    if not HABILITADO or pygame.mixer.get_init() is None:
        HABILITADO = False
        return

    archivos = {
        "saltar": "saltar_personaje.wav",
        "agachar": "agachar_personaje.wav",
        "caminar_1": "caminar_personaje_1.wav",
        "caminar_2": "caminar_personaje_2.wav",
        "caminar_3": "caminar_personaje_3.wav",
        "caminar_4": "caminar_personaje_4.wav",
        "go": "go_inicio.wav",
        "die": "die_morir.wav",
        "headshot": "headshot_morir.wav",
        "ctwin": "ctwin_final.wav",
        "terwin": "terwin_final.wav",
        "pass_persona": "pass_persona_obstaculo.wav",
        "select": "select_ui.wav",
        "tick": "tick_ui.wav",
        "save_ok": "save_ok_ui.wav",
        "save_error": "save_error_ui.wav",
    }

    for clave, archivo in archivos.items():
        ruta = _ruta(archivo)
        if not os.path.exists(ruta):
            continue
        try:
            SONIDOS[clave] = pygame.mixer.Sound(ruta)
        except Exception:
            continue


def _volumen_para(clave):
    if clave in ("tick", "select"):
        return constantes.VOLUMEN_UI
    if clave in ("caminar_1", "caminar_2", "caminar_3", "caminar_4"):
        return constantes.VOLUMEN_PASOS
    if clave in ("die", "headshot"):
        return constantes.VOLUMEN_MUERTE
    if clave in ("ctwin", "terwin"):
        return constantes.VOLUMEN_FINAL
    if clave == "pass_persona":
        return constantes.VOLUMEN_OBSTACULO
    return constantes.VOLUMEN_SFX


def reproducir(clave, volumen=None):
    """Reproduce un sonido una vez. Silencioso si no está disponible."""
    if not HABILITADO or pygame.mixer.get_init() is None:
        return None
    sonido = SONIDOS.get(clave)
    if sonido is None:
        return None
    try:
        if volumen is None:
            volumen = _volumen_para(clave)
        sonido.set_volume(max(0.0, min(1.0, volumen)))
        return sonido.play()
    except Exception:
        return None


def obtener(clave):
    if not HABILITADO or pygame.mixer.get_init() is None:
        return None
    return SONIDOS.get(clave)


def reproduciendose(canal):
    if not HABILITADO or canal is None:
        return False
    try:
        return canal.get_busy()
    except Exception:
        return False


def longitud_segundos(clave):
    sonido = SONIDOS.get(clave)
    if sonido is None:
        return 0.0
    try:
        return sonido.get_length()
    except Exception:
        return 0.0
