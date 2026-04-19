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


class SystemController(QObject):
    """Controlador de ações do sistema operacional."""

    error_occurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._volume_interface = None
        self._pycaw_available = None  # None = não tentou, True/False = resultado
        self._init_volume()

    def _init_volume(self):
        """Inicializa a interface de volume do sistema (Windows)."""
        if not _IS_WINDOWS:
            return

        try:
            # Importação lazy — evita conflito COM no nível de módulo
            import comtypes
            comtypes.CoInitialize()  # Garante inicialização COM na thread atual

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
            logger.info("Interface de volume do Windows inicializada (pycaw).")
        except ImportError as e:
            self._pycaw_available = False
            logger.warning(
                "pycaw/comtypes não instalado (%s). "
                "Usando fallback PowerShell para volume.", e
            )
        except Exception as e:
            self._pycaw_available = False
            logger.warning(
                "Falha ao inicializar pycaw (%s: %s). "
                "Usando fallback PowerShell para volume.",
                type(e).__name__, e
            )

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

        Usa pycaw no Windows para controle preciso.
        No Linux, usa pactl como fallback.
        No Windows sem pycaw, usa PowerShell como fallback.
        """
        clamped = max(0.0, min(1.0, value))

        # Tenta re-inicializar se ainda não tentou ou falhou anteriormente
        if _IS_WINDOWS and not self._volume_interface and self._pycaw_available is not False:
            logger.info("Tentando inicializar interface de volume...")
            self._init_volume()

        # Opção 1: pycaw (Windows — controle preciso)
        if self._volume_interface:
            try:
                self._volume_interface.SetMasterVolumeLevelScalar(clamped, None)
                logger.debug("Volume definido para %.0f%% (pycaw)", clamped * 100)
                return
            except Exception as e:
                logger.error("Erro pycaw ao definir volume: %s", e)
                self._volume_interface = None
                self._pycaw_available = None  # Permite re-tentativa

        # Opção 2: pactl (Linux)
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

        # Opção 3: PowerShell (Windows — fallback sem pycaw)
        if _IS_WINDOWS:
            self._volume_set_powershell(clamped)
            return

        logger.warning("Controle preciso de volume não disponível para este sistema.")

    def _volume_set_powershell(self, value: float):
        """Fallback: define volume via PowerShell no Windows."""
        # Usa a API de áudio do Windows via PowerShell/C#
        ps_script = f"""
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;

[Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IAudioEndpointVolume {{
    int NotImpl0(); int NotImpl1(); int NotImpl2();
    int GetMasterVolumeLevelScalar(out float level);
    int SetMasterVolumeLevelScalar(float level, ref Guid eventContext);
    int NotImpl3();
    int SetMute([MarshalAs(UnmanagedType.Bool)] bool mute, ref Guid eventContext);
    int GetMute(out bool mute);
}}

[Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDevice {{
    int Activate(ref Guid iid, int clsCtx, IntPtr pParams, [MarshalAs(UnmanagedType.IUnknown)] out object iface);
}}

[Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDeviceEnumerator {{
    int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMDevice device);
}}

[ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")]
class MMDeviceEnumerator {{}}

public class AudioManager {{
    public static void SetVolume(float level) {{
        var enumerator = new MMDeviceEnumerator() as IMMDeviceEnumerator;
        IMMDevice device;
        enumerator.GetDefaultAudioEndpoint(0, 1, out device);
        Guid iid = new Guid("5CDF2C82-841E-4546-9722-0CF74078229A");
        object iface;
        device.Activate(ref iid, 23, IntPtr.Zero, out iface);
        var volume = iface as IAudioEndpointVolume;
        Guid empty = Guid.Empty;
        volume.SetMasterVolumeLevelScalar(level, ref empty);
    }}
}}
'@
[AudioManager]::SetVolume({value:.6f})
"""
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                logger.debug("Volume definido para %.0f%% via PowerShell", value * 100)
            else:
                logger.error("Erro PowerShell ao definir volume: %s", result.stderr.strip())
        except subprocess.TimeoutExpired:
            logger.error("Timeout ao definir volume via PowerShell")
        except FileNotFoundError:
            logger.error("PowerShell não encontrado. Controle de volume indisponível.")

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
            import sys
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
