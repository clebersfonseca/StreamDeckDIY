"""
SystemController — Controle do sistema operacional.

Gerencia ações de sistema como volume, teclas de mídia,
atalhos de teclado e abertura de programas.

Funciona em Windows (com pycaw para volume preciso) e Linux (fallback).
"""

import logging
import os
import platform
import subprocess
import sys

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)

# pyautogui para media keys e hotkeys
try:
    import pyautogui
    pyautogui.FAILSAFE = True  # Habilita failsafe (canto da tela)
    HAS_PYAUTOGUI = True
except (ImportError, KeyError) as e:
    HAS_PYAUTOGUI = False
    logger.warning("pyautogui não disponível (%s). Atalhos de teclado desabilitados.", e)

# pycaw para controle preciso de volume (Windows only)
# Importação lazy para evitar conflito COM com PySide6/Qt
_IS_WINDOWS = platform.system() == "Windows"

# Script Python auxiliar para controle de volume no Windows.
# Roda em processo separado com COM independente do Qt.
_VOLUME_HELPER_SCRIPT = r"""
import sys
import comtypes
comtypes.CoInitialize()
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

devices = AudioUtilities.GetSpeakers()
interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
volume = cast(interface, POINTER(IAudioEndpointVolume))
sys.stdout.write("READY\n")
sys.stdout.flush()
for line in sys.stdin:
    try:
        val = float(line.strip())
        volume.SetMasterVolumeLevelScalar(max(0.0, min(1.0, val)), None)
    except Exception:
        pass
"""


class SystemController(QObject):
    """Controlador de ações do sistema operacional."""

    error_occurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._volume_interface = None
        self._volume_process = None  # Processo auxiliar para volume no Windows
        self._pycaw_available = None  # None = não tentou, True/False = resultado
        self._init_volume()

    def _init_volume(self):
        """Inicializa a interface de volume do sistema (Windows)."""
        if not _IS_WINDOWS:
            return

        # Tenta importação direta (pode funcionar se COM estiver ok)
        try:
            import comtypes
            comtypes.CoInitialize()

            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(
                IAudioEndpointVolume._iid_, CLSCTX_ALL, None
            )
            self._volume_interface = cast(
                interface, POINTER(IAudioEndpointVolume)
            )
            self._pycaw_available = True
            logger.info("Interface de volume inicializada (pycaw direto).")
            return
        except ImportError as e:
            logger.warning("pycaw/comtypes não instalado: %s", e)
            self._pycaw_available = False
            return
        except Exception as e:
            logger.info(
                "pycaw direto falhou (%s: %s). Tentando via subprocesso...",
                type(e).__name__, e
            )

        # Fallback: subprocesso persistente com COM independente
        self._start_volume_helper()

    def _start_volume_helper(self):
        """Inicia processo auxiliar para controle de volume (Windows)."""
        if self._volume_process and self._volume_process.poll() is None:
            return  # Já está rodando

        try:
            creation_flags = 0
            if _IS_WINDOWS:
                creation_flags = subprocess.CREATE_NO_WINDOW

            self._volume_process = subprocess.Popen(
                [sys.executable, "-c", _VOLUME_HELPER_SCRIPT],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=creation_flags,
            )

            # Aguarda o READY do helper (com timeout manual)
            ready_line = self._volume_process.stdout.readline()

            if self._volume_process.poll() is not None:
                # Processo morreu durante inicialização
                stderr = self._volume_process.stderr.read()
                logger.error("Helper de volume falhou ao iniciar: %s", stderr.strip())
                self._volume_process = None
                self._pycaw_available = False
            elif "READY" in ready_line:
                self._pycaw_available = True
                logger.info("Helper de volume iniciado (subprocesso pycaw).")
            else:
                logger.error("Helper de volume não respondeu READY: %s", ready_line.strip())
                self._volume_process = None
                self._pycaw_available = False

        except Exception as e:
            logger.error("Erro ao iniciar helper de volume: %s", e)
            self._volume_process = None
            self._pycaw_available = False

    def _stop_volume_helper(self):
        """Para o processo auxiliar de volume."""
        if self._volume_process:
            try:
                self._volume_process.stdin.close()
                self._volume_process.wait(timeout=2)
            except Exception:
                try:
                    self._volume_process.kill()
                except Exception:
                    pass
            self._volume_process = None

    # ---- Volume ----

    def volume_up(self):
        """Aumenta o volume do sistema."""
        if HAS_PYAUTOGUI:
            pyautogui.press("volumeup")
            logger.debug("Volume +")

    def volume_down(self):
        """Diminui o volume do sistema."""
        if HAS_PYAUTOGUI:
            pyautogui.press("volumedown")
            logger.debug("Volume -")

    def volume_mute(self):
        """Alterna mudo do sistema."""
        if HAS_PYAUTOGUI:
            pyautogui.press("volumemute")
            logger.debug("Volume mute toggle")

    def volume_set(self, value: float):
        """
        Define o volume do sistema para um valor específico (0.0 a 1.0).

        Usa pycaw no Windows para controle preciso (direto ou via subprocesso).
        No Linux, usa pactl como fallback.
        """
        clamped = max(0.0, min(1.0, value))

        # Opção 1: pycaw direto (Windows — sem conflito COM)
        if self._volume_interface:
            try:
                self._volume_interface.SetMasterVolumeLevelScalar(clamped, None)
                logger.debug("Volume definido para %.0f%% (pycaw)", clamped * 100)
                return
            except Exception as e:
                logger.error("Erro pycaw ao definir volume: %s", e)
                self._volume_interface = None

        # Opção 2: subprocesso pycaw (Windows — COM independente)
        if _IS_WINDOWS:
            if self._volume_set_via_helper(clamped):
                return

            # Tenta reiniciar o helper se não está rodando
            if self._pycaw_available is not False:
                logger.info("Reiniciando helper de volume...")
                self._start_volume_helper()
                if self._volume_set_via_helper(clamped):
                    return

            logger.warning(
                "Controle de volume indisponível. "
                "Instale pycaw e comtypes: pip install pycaw comtypes"
            )
            return

        # Opção 3: pactl (Linux)
        if platform.system() == "Linux":
            percent = int(clamped * 100)
            try:
                subprocess.run(
                    ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{percent}%"],
                    check=True, capture_output=True,
                )
                logger.debug("Volume definido para %d%% via pactl", percent)
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                logger.error("Erro ao definir volume via pactl: %s", e)
            return

        logger.warning("Controle preciso de volume não disponível para este sistema.")

    def _volume_set_via_helper(self, value: float) -> bool:
        """Envia comando de volume para o processo auxiliar. Retorna True se ok."""
        if not self._volume_process or self._volume_process.poll() is not None:
            self._volume_process = None
            return False

        try:
            self._volume_process.stdin.write(f"{value:.6f}\n")
            self._volume_process.stdin.flush()
            logger.debug("Volume definido para %.0f%% (helper)", value * 100)
            return True
        except (BrokenPipeError, OSError) as e:
            logger.warning("Helper de volume desconectou: %s", e)
            self._volume_process = None
            return False

    # ---- Media Keys ----

    def media_play_pause(self):
        """Envia Play/Pause."""
        if HAS_PYAUTOGUI:
            pyautogui.press("playpause")
            logger.debug("Media: Play/Pause")

    def media_next(self):
        """Envia próxima faixa."""
        if HAS_PYAUTOGUI:
            pyautogui.press("nexttrack")
            logger.debug("Media: Next")

    def media_prev(self):
        """Envia faixa anterior."""
        if HAS_PYAUTOGUI:
            pyautogui.press("prevtrack")
            logger.debug("Media: Previous")

    def media_stop(self):
        """Envia parar mídia."""
        if HAS_PYAUTOGUI:
            pyautogui.press("stop")
            logger.debug("Media: Stop")

    # ---- Atalhos de Teclado ----

    def hotkey(self, keys: str):
        """
        Executa um atalho de teclado.

        Formato: 'ctrl+shift+a', 'alt+f4', 'win+d', etc.
        """
        if not HAS_PYAUTOGUI:
            return

        try:
            key_list = [k.strip().lower() for k in keys.split("+")]
            # Mapeia aliases comuns
            mapped = []
            for k in key_list:
                if k == "win":
                    mapped.append("winleft")
                elif k == "ctrl":
                    mapped.append("ctrlleft")
                elif k == "alt":
                    mapped.append("altleft")
                elif k == "shift":
                    mapped.append("shiftleft")
                else:
                    mapped.append(k)

            pyautogui.hotkey(*mapped)
            logger.info("Hotkey executada: %s", keys)
        except Exception as e:
            self.error_occurred.emit(f"Erro ao executar atalho '{keys}': {e}")
            logger.error("Erro ao executar hotkey: %s", e)

    # ---- Abrir Programas / Comandos ----

    def open_app(self, path: str):
        """Abre um programa pelo caminho."""
        try:
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Linux":
                subprocess.Popen([path], start_new_session=True)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", path])
            logger.info("Programa aberto: %s", path)
        except Exception as e:
            self.error_occurred.emit(f"Erro ao abrir programa: {e}")
            logger.error("Erro ao abrir programa: %s", e)

    def run_command(self, command: str):
        """Executa um comando no shell."""
        try:
            if platform.system() == "Windows":
                subprocess.Popen(command, shell=True, start_new_session=True)
            else:
                subprocess.Popen(command, shell=True, start_new_session=True)
            logger.info("Comando executado: %s", command)
        except Exception as e:
            self.error_occurred.emit(f"Erro ao executar comando: {e}")
            logger.error("Erro ao executar comando: %s", e)

    def set_autostart(self, enabled: bool):
        """Habilita ou desabilita a inicialização com o Windows."""
        if platform.system() != "Windows":
            logger.info("Autostart suportado apenas no Windows no momento.")
            return

        try:
            from pathlib import Path

            startup_dir = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
            if not startup_dir.exists():
                logger.error("Pasta Startup não encontrada.")
                self.error_occurred.emit("Pasta Startup do Windows não encontrada.")
                return

            vbs_path = startup_dir / "StreamDeckDIY.vbs"

            if enabled:
                project_root = Path(__file__).resolve().parent.parent.parent
                if getattr(sys, 'frozen', False):
                    python_exe = sys.executable
                    script_args = ""
                else:
                    python_exe = sys.executable.replace("python.exe", "pythonw.exe")
                    if not Path(python_exe).exists():
                        python_exe = sys.executable
                    script_args = "-m app.main"

                vbs_content = f'Set WshShell = CreateObject("WScript.Shell")\n' \
                              f'WshShell.CurrentDirectory = "{project_root}"\n' \
                              f'WshShell.Run """{python_exe}"" {script_args}", 0, False\n'
                              
                vbs_path.write_text(vbs_content, encoding="utf-8")
                logger.info("Script de autostart criado em %s", vbs_path)
            else:
                if vbs_path.exists():
                    vbs_path.unlink()
                logger.info("Script de autostart removido.")

        except Exception as e:
            logger.exception("Erro ao configurar autostart")
            self.error_occurred.emit(f"Erro ao configurar inicialização: {e}")
