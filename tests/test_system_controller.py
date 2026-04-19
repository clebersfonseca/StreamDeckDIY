"""
Testes para SystemController usando Mocks.
Verifica se as chamadas de volume, teclado e processos são feitas corretamente
em diferentes sistemas operacionais.
"""

from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QApplication

from app.core.system_controller import SystemController


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def sys_ctrl(qapp):
    """Retorna uma instância limpa de SystemController."""
    return SystemController()


class TestVolumeControls:
    """Testes de atalhos de volume (pyautogui)."""

    @patch("app.core.system_controller.pyautogui", create=True)
    @patch("app.core.system_controller.HAS_PYAUTOGUI", True)
    def test_volume_up(self, mock_pyautogui, sys_ctrl):
        sys_ctrl.volume_up()
        mock_pyautogui.press.assert_called_once_with("volumeup")

    @patch("app.core.system_controller.pyautogui", create=True)
    @patch("app.core.system_controller.HAS_PYAUTOGUI", True)
    def test_volume_down(self, mock_pyautogui, sys_ctrl):
        sys_ctrl.volume_down()
        mock_pyautogui.press.assert_called_once_with("volumedown")

    @patch("app.core.system_controller.pyautogui", create=True)
    @patch("app.core.system_controller.HAS_PYAUTOGUI", True)
    def test_volume_mute(self, mock_pyautogui, sys_ctrl):
        sys_ctrl.volume_mute()
        mock_pyautogui.press.assert_called_once_with("volumemute")

    @patch("app.core.system_controller.subprocess.run")
    @patch("app.core.system_controller.platform.system", return_value="Linux")
    @patch("app.core.system_controller._IS_WINDOWS", False)
    def test_volume_set_linux(self, mock_platform, mock_run, sys_ctrl):
        """No Linux, volume_set deve chamar o pactl via subprocess."""
        sys_ctrl._volume_interface = None
        sys_ctrl.volume_set(0.75) # 75%
        mock_run.assert_called_once_with(
            ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "75%"],
            check=True, capture_output=True
        )

    @patch("app.core.system_controller.platform.system", return_value="Windows")
    def test_volume_set_windows_pycaw(self, mock_platform, sys_ctrl):
        """No Windows, se pycaw estiver presente, usa a interface COM."""
        # Configurar o mock da interface
        mock_interface = MagicMock()
        sys_ctrl._volume_interface = mock_interface

        sys_ctrl.volume_set(0.5)
        mock_interface.SetMasterVolumeLevelScalar.assert_called_once_with(0.5, None)


class TestMediaControls:
    """Testes de controles de mídia (pyautogui)."""

    @patch("app.core.system_controller.pyautogui", create=True)
    @patch("app.core.system_controller.HAS_PYAUTOGUI", True)
    def test_media_play_pause(self, mock_pyautogui, sys_ctrl):
        sys_ctrl.media_play_pause()
        mock_pyautogui.press.assert_called_once_with("playpause")

    @patch("app.core.system_controller.pyautogui", create=True)
    @patch("app.core.system_controller.HAS_PYAUTOGUI", True)
    def test_media_next(self, mock_pyautogui, sys_ctrl):
        sys_ctrl.media_next()
        mock_pyautogui.press.assert_called_once_with("nexttrack")

    @patch("app.core.system_controller.pyautogui", create=True)
    @patch("app.core.system_controller.HAS_PYAUTOGUI", True)
    def test_media_prev(self, mock_pyautogui, sys_ctrl):
        sys_ctrl.media_prev()
        mock_pyautogui.press.assert_called_once_with("prevtrack")

    @patch("app.core.system_controller.pyautogui", create=True)
    @patch("app.core.system_controller.HAS_PYAUTOGUI", True)
    def test_media_stop(self, mock_pyautogui, sys_ctrl):
        sys_ctrl.media_stop()
        mock_pyautogui.press.assert_called_once_with("stop")


class TestHotkeys:
    """Testes de execução de atalhos e tradução de modificadores."""

    @patch("app.core.system_controller.pyautogui", create=True)
    @patch("app.core.system_controller.HAS_PYAUTOGUI", True)
    def test_hotkey_simple(self, mock_pyautogui, sys_ctrl):
        sys_ctrl.hotkey("ctrl+c")
        mock_pyautogui.hotkey.assert_called_once_with("ctrlleft", "c")

    @patch("app.core.system_controller.pyautogui", create=True)
    @patch("app.core.system_controller.HAS_PYAUTOGUI", True)
    def test_hotkey_complex(self, mock_pyautogui, sys_ctrl):
        sys_ctrl.hotkey("ctrl+shift+alt+a")
        mock_pyautogui.hotkey.assert_called_once_with(
            "ctrlleft", "shiftleft", "altleft", "a"
        )

    @patch("app.core.system_controller.pyautogui", create=True)
    @patch("app.core.system_controller.HAS_PYAUTOGUI", True)
    def test_hotkey_win(self, mock_pyautogui, sys_ctrl):
        sys_ctrl.hotkey("win+d")
        mock_pyautogui.hotkey.assert_called_once_with("winleft", "d")

    @patch("app.core.system_controller.pyautogui", create=True)
    @patch("app.core.system_controller.HAS_PYAUTOGUI", False)
    def test_hotkey_disabled_without_pyautogui(self, mock_pyautogui, sys_ctrl):
        """Se pyautogui não estiver instalado, hotkey não faz nada."""
        sys_ctrl.hotkey("ctrl+c")
        mock_pyautogui.hotkey.assert_not_called()

    @patch("app.core.system_controller.pyautogui", create=True)
    @patch("app.core.system_controller.HAS_PYAUTOGUI", True)
    def test_hotkey_exception_emits_error(self, mock_pyautogui, sys_ctrl):
        """Erros ao executar atalho devem emitir o sinal de erro."""
        mock_pyautogui.hotkey.side_effect = Exception("Teclado falhou")
        
        mock_slot = MagicMock()
        sys_ctrl.error_occurred.connect(mock_slot)
        
        sys_ctrl.hotkey("ctrl+c")
        mock_slot.assert_called_once()
        assert "Erro ao executar atalho" in mock_slot.call_args[0][0]


class TestProcessExecution:
    """Testes para abrir aplicativos e rodar comandos no SO."""

    @patch("app.core.system_controller.os.startfile", create=True)
    @patch("app.core.system_controller.platform.system", return_value="Windows")
    def test_open_app_windows(self, mock_platform, mock_startfile, sys_ctrl):
        sys_ctrl.open_app("notepad.exe")
        mock_startfile.assert_called_once_with("notepad.exe")

    @patch("app.core.system_controller.subprocess.Popen")
    @patch("app.core.system_controller.platform.system", return_value="Linux")
    def test_open_app_linux(self, mock_platform, mock_popen, sys_ctrl):
        sys_ctrl.open_app("/usr/bin/gedit")
        mock_popen.assert_called_once_with(["/usr/bin/gedit"], start_new_session=True)

    @patch("app.core.system_controller.subprocess.Popen")
    @patch("app.core.system_controller.platform.system", return_value="Darwin")
    def test_open_app_mac(self, mock_platform, mock_popen, sys_ctrl):
        sys_ctrl.open_app("/Applications/Safari.app")
        mock_popen.assert_called_once_with(["open", "/Applications/Safari.app"])

    @patch("app.core.system_controller.os.startfile", create=True)
    @patch("app.core.system_controller.platform.system", return_value="Windows")
    def test_open_app_exception_emits_error(self, mock_platform, mock_startfile, sys_ctrl):
        mock_startfile.side_effect = FileNotFoundError("Arquivo não encontrado")
        
        mock_slot = MagicMock()
        sys_ctrl.error_occurred.connect(mock_slot)
        
        sys_ctrl.open_app("inexistente.exe")
        mock_slot.assert_called_once()

    @patch("app.core.system_controller.subprocess.Popen")
    def test_run_command(self, mock_popen, sys_ctrl):
        sys_ctrl.run_command("echo hello")
        mock_popen.assert_called_once_with(
            "echo hello", shell=True, start_new_session=True
        )

    @patch("app.core.system_controller.subprocess.Popen")
    def test_run_command_exception_emits_error(self, mock_popen, sys_ctrl):
        mock_popen.side_effect = Exception("Shell quebrou")
        
        mock_slot = MagicMock()
        sys_ctrl.error_occurred.connect(mock_slot)
        
        sys_ctrl.run_command("bad command")
        mock_slot.assert_called_once()
