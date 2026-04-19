"""
Extended tests for OBSController — covers disconnected-guard paths
and exception paths for all individual methods.
"""

from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QApplication

from app.core.obs_controller import OBSController


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def obs_ctrl(qapp):
    return OBSController()


@pytest.fixture
def obs_connected(obs_ctrl):
    with patch("app.core.obs_controller.obsws.ReqClient") as mock_req:
        with patch("app.core.obs_controller.HAS_OBSWS", True):
            obs_ctrl.connect()
            yield obs_ctrl, mock_req.return_value


# ---- Exception paths (connected) ----


class TestExceptionPaths:
    """Each method's except branch should emit error_occurred."""

    def test_switch_scene_exception(self, obs_connected):
        obs, mock_client = obs_connected
        mock_client.set_current_program_scene.side_effect = Exception("fail")

        slot = MagicMock()
        obs.error_occurred.connect(slot)

        obs.switch_scene("Scene1")

        slot.assert_called_once()
        assert "Erro ao trocar cena" in slot.call_args[0][0]

    def test_toggle_source_exception(self, obs_connected):
        obs, mock_client = obs_connected
        mock_client.get_scene_item_id.side_effect = Exception("fail")

        slot = MagicMock()
        obs.error_occurred.connect(slot)

        obs.toggle_source("Scene1", "Source1")

        slot.assert_called_once()
        assert "Erro ao alternar fonte" in slot.call_args[0][0]

    def test_toggle_mute_exception(self, obs_connected):
        obs, mock_client = obs_connected
        mock_client.toggle_input_mute.side_effect = Exception("fail")

        slot = MagicMock()
        obs.error_occurred.connect(slot)

        obs.toggle_mute("Mic")

        slot.assert_called_once()
        assert "Erro ao alternar mudo" in slot.call_args[0][0]

    def test_set_source_volume_exception(self, obs_connected):
        obs, mock_client = obs_connected
        mock_client.set_input_volume.side_effect = Exception("fail")

        slot = MagicMock()
        obs.error_occurred.connect(slot)

        obs.set_source_volume("Mic", -10.0)

        slot.assert_called_once()
        assert "Erro ao definir volume" in slot.call_args[0][0]

    def test_set_source_volume_normalized_exception(self, obs_connected):
        obs, mock_client = obs_connected
        mock_client.set_input_volume.side_effect = Exception("fail")

        slot = MagicMock()
        obs.error_occurred.connect(slot)

        obs.set_source_volume_normalized("Mic", 0.5)

        slot.assert_called_once()
        assert "Erro ao definir volume" in slot.call_args[0][0]

    def test_stop_streaming_exception(self, obs_connected):
        obs, mock_client = obs_connected
        mock_client.stop_stream.side_effect = Exception("fail")

        slot = MagicMock()
        obs.error_occurred.connect(slot)

        obs.stop_streaming()

        slot.assert_called_once()
        assert "Erro ao parar transmissão" in slot.call_args[0][0]

    def test_toggle_streaming_exception(self, obs_connected):
        obs, mock_client = obs_connected
        mock_client.toggle_stream.side_effect = Exception("fail")

        slot = MagicMock()
        obs.error_occurred.connect(slot)

        obs.toggle_streaming()

        slot.assert_called_once()
        assert "Erro ao alternar transmissão" in slot.call_args[0][0]

    def test_start_recording_exception(self, obs_connected):
        obs, mock_client = obs_connected
        mock_client.start_record.side_effect = Exception("fail")

        slot = MagicMock()
        obs.error_occurred.connect(slot)

        obs.start_recording()

        slot.assert_called_once()
        assert "Erro ao iniciar gravação" in slot.call_args[0][0]

    def test_stop_recording_exception(self, obs_connected):
        obs, mock_client = obs_connected
        mock_client.stop_record.side_effect = Exception("fail")

        slot = MagicMock()
        obs.error_occurred.connect(slot)

        obs.stop_recording()

        slot.assert_called_once()
        assert "Erro ao parar gravação" in slot.call_args[0][0]

    def test_toggle_recording_exception(self, obs_connected):
        obs, mock_client = obs_connected
        mock_client.toggle_record.side_effect = Exception("fail")

        slot = MagicMock()
        obs.error_occurred.connect(slot)

        obs.toggle_recording()

        slot.assert_called_once()
        assert "Erro ao alternar gravação" in slot.call_args[0][0]

    def test_toggle_virtual_cam_exception(self, obs_connected):
        obs, mock_client = obs_connected
        mock_client.toggle_virtual_cam.side_effect = Exception("fail")

        slot = MagicMock()
        obs.error_occurred.connect(slot)

        obs.toggle_virtual_cam()

        slot.assert_called_once()
        assert "Erro ao alternar câmera virtual" in slot.call_args[0][0]


# ---- Disconnected-guard paths ----


class TestNotConnectedGuards:
    """Methods should silently return when not connected."""

    def test_get_scenes_not_connected(self, obs_ctrl):
        result = obs_ctrl.get_scenes()
        assert result == []

    def test_toggle_source_not_connected(self, obs_ctrl):
        slot = MagicMock()
        obs_ctrl.error_occurred.connect(slot)

        obs_ctrl.toggle_source("Scene1", "Source1")

        slot.assert_not_called()

    def test_toggle_mute_not_connected(self, obs_ctrl):
        slot = MagicMock()
        obs_ctrl.error_occurred.connect(slot)

        obs_ctrl.toggle_mute("Mic")

        slot.assert_not_called()

    def test_set_source_volume_not_connected(self, obs_ctrl):
        slot = MagicMock()
        obs_ctrl.error_occurred.connect(slot)

        obs_ctrl.set_source_volume("Mic", -10.0)

        slot.assert_not_called()

    def test_set_source_volume_normalized_not_connected(self, obs_ctrl):
        slot = MagicMock()
        obs_ctrl.error_occurred.connect(slot)

        obs_ctrl.set_source_volume_normalized("Mic", 0.5)

        slot.assert_not_called()

    def test_stop_streaming_not_connected(self, obs_ctrl):
        slot = MagicMock()
        obs_ctrl.error_occurred.connect(slot)

        obs_ctrl.stop_streaming()

        slot.assert_not_called()

    def test_toggle_streaming_not_connected(self, obs_ctrl):
        slot = MagicMock()
        obs_ctrl.error_occurred.connect(slot)

        obs_ctrl.toggle_streaming()

        slot.assert_not_called()

    def test_start_recording_not_connected(self, obs_ctrl):
        slot = MagicMock()
        obs_ctrl.error_occurred.connect(slot)

        obs_ctrl.start_recording()

        slot.assert_not_called()

    def test_stop_recording_not_connected(self, obs_ctrl):
        slot = MagicMock()
        obs_ctrl.error_occurred.connect(slot)

        obs_ctrl.stop_recording()

        slot.assert_not_called()

    def test_toggle_recording_not_connected(self, obs_ctrl):
        slot = MagicMock()
        obs_ctrl.error_occurred.connect(slot)

        obs_ctrl.toggle_recording()

        slot.assert_not_called()

    def test_toggle_virtual_cam_not_connected(self, obs_ctrl):
        slot = MagicMock()
        obs_ctrl.error_occurred.connect(slot)

        obs_ctrl.toggle_virtual_cam()

        slot.assert_not_called()


# ---- Edge cases ----


class TestEdgeCases:
    """Additional edge-case coverage."""

    def test_disconnect_when_already_disconnected(self, obs_ctrl):
        slot = MagicMock()
        obs_ctrl.error_occurred.connect(slot)

        obs_ctrl.disconnect()

        assert not obs_ctrl.is_connected
        slot.assert_not_called()

    @patch("app.core.obs_controller.obsws.ReqClient")
    @patch("app.core.obs_controller.HAS_OBSWS", True)
    def test_connect_empty_password(self, mock_req_client, obs_ctrl):
        obs_ctrl.connect("localhost", 4455, "")

        mock_req_client.assert_called_once_with(
            host="localhost", port=4455, password=None, timeout=5
        )
