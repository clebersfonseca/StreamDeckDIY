"""
Testes para o OBSController usando Mocks.
Verifica se as requisições ao websocket do OBS são formatadas corretamente.
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


class TestOBSConnection:
    """Testes de conexão com o OBS."""

    @patch("app.core.obs_controller.HAS_OBSWS", False)
    def test_connect_fails_if_library_missing(self, obs_ctrl):
        mock_slot = MagicMock()
        obs_ctrl.error_occurred.connect(mock_slot)
        
        result = obs_ctrl.connect()
        
        assert not result
        assert not obs_ctrl.is_connected
        mock_slot.assert_called_once()
        assert "não instalada" in mock_slot.call_args[0][0]

    @patch("app.core.obs_controller.obsws.ReqClient")
    @patch("app.core.obs_controller.HAS_OBSWS", True)
    def test_connect_success(self, mock_req_client, obs_ctrl):
        mock_slot = MagicMock()
        obs_ctrl.connection_changed.connect(mock_slot)
        
        result = obs_ctrl.connect("192.168.1.10", 4455, "senha")
        
        assert result
        assert obs_ctrl.is_connected
        mock_req_client.assert_called_once_with(
            host="192.168.1.10", port=4455, password="senha", timeout=5
        )
        mock_slot.assert_called_once_with(True)

    @patch("app.core.obs_controller.obsws.ReqClient")
    @patch("app.core.obs_controller.HAS_OBSWS", True)
    def test_connect_exception(self, mock_req_client, obs_ctrl):
        mock_req_client.side_effect = Exception("Connection refused")
        
        mock_err_slot = MagicMock()
        mock_conn_slot = MagicMock()
        obs_ctrl.error_occurred.connect(mock_err_slot)
        obs_ctrl.connection_changed.connect(mock_conn_slot)
        
        result = obs_ctrl.connect()
        
        assert not result
        assert not obs_ctrl.is_connected
        mock_err_slot.assert_called_once()
        mock_conn_slot.assert_called_once_with(False)

    @patch("app.core.obs_controller.obsws.ReqClient")
    @patch("app.core.obs_controller.HAS_OBSWS", True)
    def test_disconnect(self, mock_req_client, obs_ctrl):
        obs_ctrl.connect()
        assert obs_ctrl.is_connected
        
        mock_slot = MagicMock()
        obs_ctrl.connection_changed.connect(mock_slot)
        
        obs_ctrl.disconnect()
        
        assert not obs_ctrl.is_connected
        assert obs_ctrl._client is None
        mock_slot.assert_called_once_with(False)


@pytest.fixture
def obs_connected(obs_ctrl):
    """Retorna um OBSController já 'conectado' com um cliente mockado."""
    with patch("app.core.obs_controller.obsws.ReqClient") as mock_req:
        with patch("app.core.obs_controller.HAS_OBSWS", True):
            obs_ctrl.connect()
            yield obs_ctrl, mock_req.return_value


class TestOBSActions:
    """Testes para as ações executadas no OBS."""

    def test_ensure_connected_blocks_actions(self, obs_ctrl):
        """Se não estiver conectado, não deve executar nada e não dar erro."""
        # Se desse erro, levantaria exception
        obs_ctrl.switch_scene("Cena 1")
        obs_ctrl.start_streaming()
        # Não conectou, então _client é None e nada ocorre

    def test_switch_scene(self, obs_connected):
        obs, mock_client = obs_connected
        obs.switch_scene("Game")
        mock_client.set_current_program_scene.assert_called_once_with("Game")

    def test_get_scenes(self, obs_connected):
        obs, mock_client = obs_connected
        
        # Simular o objeto retornado pelo obsws
        mock_response = MagicMock()
        mock_response.scenes = [
            {"sceneName": "Main"},
            {"sceneName": "BRB"}
        ]
        mock_client.get_scene_list.return_value = mock_response
        
        scenes = obs.get_scenes()
        assert scenes == ["Main", "BRB"]
        mock_client.get_scene_list.assert_called_once()

    def test_get_scenes_exception(self, obs_connected):
        obs, mock_client = obs_connected
        mock_client.get_scene_list.side_effect = Exception("Erro na API")
        
        scenes = obs.get_scenes()
        assert scenes == []

    def test_toggle_source(self, obs_connected):
        obs, mock_client = obs_connected
        
        # Simular retornos em cadeia do OBS
        mock_id_resp = MagicMock()
        mock_id_resp.scene_item_id = 123
        mock_client.get_scene_item_id.return_value = mock_id_resp
        
        mock_enabled_resp = MagicMock()
        mock_enabled_resp.scene_item_enabled = True
        mock_client.get_scene_item_enabled.return_value = mock_enabled_resp
        
        obs.toggle_source("Scene1", "Source1")
        
        mock_client.get_scene_item_id.assert_called_once_with("Scene1", "Source1")
        mock_client.get_scene_item_enabled.assert_called_once_with("Scene1", 123)
        # Se estava True, deve setar pra False
        mock_client.set_scene_item_enabled.assert_called_once_with("Scene1", 123, False)

    def test_toggle_mute(self, obs_connected):
        obs, mock_client = obs_connected
        obs.toggle_mute("Mic")
        mock_client.toggle_input_mute.assert_called_once_with("Mic")

    def test_set_source_volume_db(self, obs_connected):
        obs, mock_client = obs_connected
        obs.set_source_volume("Mic", -10.5)
        mock_client.set_input_volume.assert_called_once_with("Mic", vol_db=-10.5)

    def test_set_source_volume_normalized(self, obs_connected):
        obs, mock_client = obs_connected
        obs.set_source_volume_normalized("Mic", 0.7)
        mock_client.set_input_volume.assert_called_once_with("Mic", vol_mul=0.7)

    def test_set_source_volume_normalized_clamps_values(self, obs_connected):
        obs, mock_client = obs_connected
        obs.set_source_volume_normalized("Mic", 1.5)
        mock_client.set_input_volume.assert_called_with("Mic", vol_mul=1.0)
        
        obs.set_source_volume_normalized("Mic", -0.5)
        mock_client.set_input_volume.assert_called_with("Mic", vol_mul=0.0)

    def test_streaming_toggles(self, obs_connected):
        obs, mock_client = obs_connected
        
        obs.start_streaming()
        mock_client.start_stream.assert_called_once()
        
        obs.stop_streaming()
        mock_client.stop_stream.assert_called_once()
        
        obs.toggle_streaming()
        mock_client.toggle_stream.assert_called_once()

    def test_recording_toggles(self, obs_connected):
        obs, mock_client = obs_connected
        
        obs.start_recording()
        mock_client.start_record.assert_called_once()
        
        obs.stop_recording()
        mock_client.stop_record.assert_called_once()
        
        obs.toggle_recording()
        mock_client.toggle_record.assert_called_once()

    def test_virtual_cam_toggle(self, obs_connected):
        obs, mock_client = obs_connected
        
        obs.toggle_virtual_cam()
        mock_client.toggle_virtual_cam.assert_called_once()

    def test_exceptions_emit_error_signal(self, obs_connected):
        obs, mock_client = obs_connected
        mock_client.start_stream.side_effect = Exception("OBS Crashed")
        
        mock_slot = MagicMock()
        obs.error_occurred.connect(mock_slot)
        
        obs.start_streaming()
        
        mock_slot.assert_called_once()
        assert "Erro ao iniciar transmissão" in mock_slot.call_args[0][0]
