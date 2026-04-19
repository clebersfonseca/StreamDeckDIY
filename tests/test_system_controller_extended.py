"""
Extended tests for SystemController.

Covers missing lines: pyautogui-absent branches, volume_set clamping,
platform-specific volume paths, media-key no-op branches, and set_autostart.
"""

import subprocess
from pathlib import Path
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
    return SystemController()


# ---- Volume up/down/mute with no pyautogui ----


class TestVolumeNoPyautogui:
    @patch("app.core.system_controller.HAS_PYAUTOGUI", False)
    def test_volume_up_no_pyautogui(self, sys_ctrl):
        # Should silently do nothing when pyautogui is unavailable
        sys_ctrl.volume_up()

    @patch("app.core.system_controller.HAS_PYAUTOGUI", False)
    def test_volume_down_no_pyautogui(self, sys_ctrl):
        sys_ctrl.volume_down()

    @patch("app.core.system_controller.HAS_PYAUTOGUI", False)
    def test_volume_mute_no_pyautogui(self, sys_ctrl):
        sys_ctrl.volume_mute()


# ---- volume_set clamping and platform branches ----


class TestVolumeSetExtended:
    @patch("app.core.system_controller.subprocess.run")
    @patch("app.core.system_controller.platform.system", return_value="Linux")
    @patch("app.core.system_controller._IS_WINDOWS", False)
    def test_volume_set_clamps_above_one(self, _plat, mock_run, sys_ctrl):
        sys_ctrl.volume_set(1.5)
        mock_run.assert_called_once_with(
            ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "100%"],
            check=True,
            capture_output=True,
        )

    @patch("app.core.system_controller.subprocess.run")
    @patch("app.core.system_controller.platform.system", return_value="Linux")
    @patch("app.core.system_controller._IS_WINDOWS", False)
    def test_volume_set_clamps_below_zero(self, _plat, mock_run, sys_ctrl):
        sys_ctrl.volume_set(-0.5)
        mock_run.assert_called_once_with(
            ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "0%"],
            check=True,
            capture_output=True,
        )

    @patch("app.core.system_controller.subprocess.run")
    @patch("app.core.system_controller.platform.system", return_value="Linux")
    @patch("app.core.system_controller._IS_WINDOWS", False)
    def test_volume_set_linux_pactl_failure(self, _plat, mock_run, sys_ctrl):
        mock_run.side_effect = subprocess.CalledProcessError(1, "pactl")
        sys_ctrl.volume_set(0.5)  # should not raise

    @patch("app.core.system_controller.subprocess.run")
    @patch("app.core.system_controller.platform.system", return_value="Linux")
    @patch("app.core.system_controller._IS_WINDOWS", False)
    def test_volume_set_linux_pactl_not_found(self, _plat, mock_run, sys_ctrl):
        mock_run.side_effect = FileNotFoundError("pactl not found")
        sys_ctrl.volume_set(0.5)  # should not raise

    @patch("app.core.system_controller.platform.system", return_value="Darwin")
    @patch("app.core.system_controller._IS_WINDOWS", False)
    def test_volume_set_unsupported_platform(self, _plat, sys_ctrl):
        # Darwin is neither Windows nor Linux — just logs a warning
        sys_ctrl.volume_set(0.5)  # should not raise

    @patch("app.core.system_controller._IS_WINDOWS", True)
    def test_volume_set_windows_no_endpoint_retry_fails(self, sys_ctrl):
        sys_ctrl._volume_endpoint = None
        with patch.object(sys_ctrl, "_init_volume"):
            # _init_volume is called but still doesn't set endpoint
            sys_ctrl.volume_set(0.5)
        # Endpoint remains None — just logs warning, no error

    @patch("app.core.system_controller._IS_WINDOWS", True)
    def test_volume_set_windows_pycaw_exception(self, sys_ctrl):
        mock_ep = MagicMock()
        mock_ep.SetMasterVolumeLevelScalar.side_effect = Exception("COM failure")
        sys_ctrl._volume_endpoint = mock_ep
        sys_ctrl.volume_set(0.5)
        # After exception endpoint should be reset to None
        assert sys_ctrl._volume_endpoint is None


# ---- Media keys with no pyautogui ----


class TestMediaNoPyautogui:
    @patch("app.core.system_controller.HAS_PYAUTOGUI", False)
    def test_media_play_pause_no_pyautogui(self, sys_ctrl):
        sys_ctrl.media_play_pause()

    @patch("app.core.system_controller.HAS_PYAUTOGUI", False)
    def test_media_next_no_pyautogui(self, sys_ctrl):
        sys_ctrl.media_next()

    @patch("app.core.system_controller.HAS_PYAUTOGUI", False)
    def test_media_prev_no_pyautogui(self, sys_ctrl):
        sys_ctrl.media_prev()

    @patch("app.core.system_controller.HAS_PYAUTOGUI", False)
    def test_media_stop_no_pyautogui(self, sys_ctrl):
        sys_ctrl.media_stop()


# ---- set_autostart ----


class TestSetAutostart:
    @patch("app.core.system_controller.platform.system", return_value="Linux")
    def test_set_autostart_non_windows(self, _plat, sys_ctrl):
        # Should return early on non-Windows
        sys_ctrl.set_autostart(True)

    @patch("app.core.system_controller.platform.system", return_value="Windows")
    def test_set_autostart_enable_creates_vbs(self, _plat, sys_ctrl, tmp_path):
        startup_dir = (
            tmp_path / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        )
        startup_dir.mkdir(parents=True)

        with patch.dict("os.environ", {"APPDATA": str(tmp_path)}):
            sys_ctrl.set_autostart(True)

        vbs_path = startup_dir / "StreamDeckDIY.vbs"
        assert vbs_path.exists()
        content = vbs_path.read_text(encoding="utf-8")
        assert "WshShell" in content

    @patch("app.core.system_controller.platform.system", return_value="Windows")
    def test_set_autostart_disable_removes_vbs(self, _plat, sys_ctrl, tmp_path):
        startup_dir = (
            tmp_path / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        )
        startup_dir.mkdir(parents=True)
        vbs_path = startup_dir / "StreamDeckDIY.vbs"
        vbs_path.write_text("dummy", encoding="utf-8")

        with patch.dict("os.environ", {"APPDATA": str(tmp_path)}):
            sys_ctrl.set_autostart(False)

        assert not vbs_path.exists()

    @patch("app.core.system_controller.platform.system", return_value="Windows")
    def test_set_autostart_startup_dir_not_found(self, _plat, sys_ctrl, tmp_path):
        mock_slot = MagicMock()
        sys_ctrl.error_occurred.connect(mock_slot)

        # APPDATA points to tmp_path but the Startup sub-dir doesn't exist
        with patch.dict("os.environ", {"APPDATA": str(tmp_path)}):
            sys_ctrl.set_autostart(True)

        mock_slot.assert_called_once()
        assert "Startup" in mock_slot.call_args[0][0]

    @patch("app.core.system_controller.platform.system", return_value="Windows")
    def test_set_autostart_exception(self, _plat, sys_ctrl):
        mock_slot = MagicMock()
        sys_ctrl.error_occurred.connect(mock_slot)

        with patch.dict("os.environ", {"APPDATA": ""}):
            with patch("pathlib.Path.exists", side_effect=PermissionError("denied")):
                sys_ctrl.set_autostart(True)

        mock_slot.assert_called_once()
        assert "Erro ao configurar" in mock_slot.call_args[0][0]


# ---- open_app exception on Linux ----


class TestOpenAppExtended:
    @patch("app.core.system_controller.subprocess.Popen")
    @patch("app.core.system_controller.platform.system", return_value="Linux")
    def test_open_app_exception_emits_error_linux(self, _plat, mock_popen, sys_ctrl):
        mock_popen.side_effect = OSError("exec failed")
        mock_slot = MagicMock()
        sys_ctrl.error_occurred.connect(mock_slot)

        sys_ctrl.open_app("/usr/bin/nonexistent")

        mock_slot.assert_called_once()
        assert "Erro ao abrir programa" in mock_slot.call_args[0][0]
