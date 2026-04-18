"""
Testes para o ActionDispatcher usando Mocks.
Verifica se as ações configuradas chamam os métodos corretos nos controllers.
"""

from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QApplication

from app.core.action_dispatcher import ActionDispatcher
from app.core.profile_manager import ProfileManager, ActionType


@pytest.fixture(scope="session")
def qapp():
    """QApplication para permitir Signal/Slot do PySide6."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def profile_manager(tmp_path):
    """ProfileManager usando banco SQLite temporário."""
    return ProfileManager(config_dir=str(tmp_path))


@pytest.fixture
def mock_obs():
    return MagicMock()


@pytest.fixture
def mock_sys():
    return MagicMock()


@pytest.fixture
def dispatcher(profile_manager, mock_obs, mock_sys, qapp):
    """Retorna o dispatcher com dependências mockadas."""
    return ActionDispatcher(
        profile_manager=profile_manager,
        obs_controller=mock_obs,
        system_controller=mock_sys
    )


class TestButtonActions:
    """Testa o roteamento de ações de botões."""

    def test_ignore_release_event(self, dispatcher, profile_manager, mock_sys):
        """Eventos de 'soltar botão' (pressed=False) devem ser ignorados."""
        profile_manager.set_button_action(0, 0, ActionType.SYS_VOLUME_UP.value, {}, "")
        dispatcher.on_button_event(0, 0, pressed=False)
        mock_sys.volume_up.assert_not_called()

    def test_obs_switch_scene(self, dispatcher, profile_manager, mock_obs):
        profile_manager.set_button_action(
            0, 0, ActionType.OBS_SWITCH_SCENE.value, {"scene_name": "Game"}, ""
        )
        dispatcher.on_button_event(0, 0, pressed=True)
        mock_obs.switch_scene.assert_called_once_with("Game")

    def test_obs_toggle_source(self, dispatcher, profile_manager, mock_obs):
        profile_manager.set_button_action(
            1, 1, ActionType.OBS_TOGGLE_SOURCE.value, 
            {"scene_name": "Main", "source_name": "Cam"}, ""
        )
        dispatcher.on_button_event(1, 1, pressed=True)
        mock_obs.toggle_source.assert_called_once_with("Main", "Cam")

    def test_obs_toggle_mute(self, dispatcher, profile_manager, mock_obs):
        profile_manager.set_button_action(
            0, 2, ActionType.OBS_TOGGLE_MUTE.value, {"source_name": "Mic"}, ""
        )
        dispatcher.on_button_event(0, 2, pressed=True)
        mock_obs.toggle_mute.assert_called_once_with("Mic")

    def test_obs_simple_toggles(self, dispatcher, profile_manager, mock_obs):
        actions = [
            (ActionType.OBS_START_STREAMING, mock_obs.start_streaming),
            (ActionType.OBS_STOP_STREAMING, mock_obs.stop_streaming),
            (ActionType.OBS_TOGGLE_STREAMING, mock_obs.toggle_streaming),
            (ActionType.OBS_START_RECORDING, mock_obs.start_recording),
            (ActionType.OBS_STOP_RECORDING, mock_obs.stop_recording),
            (ActionType.OBS_TOGGLE_RECORDING, mock_obs.toggle_recording),
            (ActionType.OBS_TOGGLE_VIRTUAL_CAM, mock_obs.toggle_virtual_cam),
        ]
        for idx, (action_type, mock_method) in enumerate(actions):
            profile_manager.set_button_action(0, 0, action_type.value, {}, "")
            dispatcher.on_button_event(0, 0, pressed=True)
            mock_method.assert_called_once()
            mock_method.reset_mock()

    def test_sys_volume_controls(self, dispatcher, profile_manager, mock_sys):
        actions = [
            (ActionType.SYS_VOLUME_UP, mock_sys.volume_up),
            (ActionType.SYS_VOLUME_DOWN, mock_sys.volume_down),
            (ActionType.SYS_VOLUME_MUTE, mock_sys.volume_mute),
        ]
        for idx, (action_type, mock_method) in enumerate(actions):
            profile_manager.set_button_action(0, 0, action_type.value, {}, "")
            dispatcher.on_button_event(0, 0, pressed=True)
            mock_method.assert_called_once()
            mock_method.reset_mock()

    def test_sys_media_controls(self, dispatcher, profile_manager, mock_sys):
        actions = [
            (ActionType.SYS_MEDIA_PLAY_PAUSE, mock_sys.media_play_pause),
            (ActionType.SYS_MEDIA_NEXT, mock_sys.media_next),
            (ActionType.SYS_MEDIA_PREV, mock_sys.media_prev),
            (ActionType.SYS_MEDIA_STOP, mock_sys.media_stop),
        ]
        for idx, (action_type, mock_method) in enumerate(actions):
            profile_manager.set_button_action(0, 0, action_type.value, {}, "")
            dispatcher.on_button_event(0, 0, pressed=True)
            mock_method.assert_called_once()
            mock_method.reset_mock()

    def test_sys_hotkey(self, dispatcher, profile_manager, mock_sys):
        profile_manager.set_button_action(
            0, 0, ActionType.SYS_HOTKEY.value, {"keys": "ctrl+c"}, ""
        )
        dispatcher.on_button_event(0, 0, pressed=True)
        mock_sys.hotkey.assert_called_once_with("ctrl+c")

    def test_sys_open_app(self, dispatcher, profile_manager, mock_sys):
        profile_manager.set_button_action(
            0, 0, ActionType.SYS_OPEN_APP.value, {"path": "notepad.exe"}, ""
        )
        dispatcher.on_button_event(0, 0, pressed=True)
        mock_sys.open_app.assert_called_once_with("notepad.exe")

    def test_sys_run_command(self, dispatcher, profile_manager, mock_sys):
        profile_manager.set_button_action(
            0, 0, ActionType.SYS_RUN_COMMAND.value, {"command": "echo hello"}, ""
        )
        dispatcher.on_button_event(0, 0, pressed=True)
        mock_sys.run_command.assert_called_once_with("echo hello")

    def test_app_switch_layout(self, dispatcher, profile_manager):
        # Sinal deve ser emitido
        mock_slot = MagicMock()
        dispatcher.layout_switch_requested.connect(mock_slot)
        
        profile_manager.set_button_action(
            0, 0, ActionType.APP_SWITCH_LAYOUT.value, {"layout_name": "Layout 2"}, ""
        )
        dispatcher.on_button_event(0, 0, pressed=True)
        
        mock_slot.assert_called_once_with("Layout 2")

    def test_unknown_action(self, dispatcher, profile_manager):
        """Ações inválidas devem ser capturadas sem crash."""
        profile_manager.set_button_action(0, 0, "nonexistent_action", {}, "")
        # Apenas chamamos, não deve quebrar
        dispatcher.on_button_event(0, 0, pressed=True)

    def test_none_action(self, dispatcher, profile_manager, mock_obs, mock_sys):
        """Ação NONE não deve chamar nada."""
        profile_manager.set_button_action(0, 0, ActionType.NONE.value, {}, "")
        dispatcher.on_button_event(0, 0, pressed=True)
        mock_obs.switch_scene.assert_not_called()
        mock_sys.volume_up.assert_not_called()


class TestPotActions:
    """Testa roteamento de ações de potenciômetros."""

    def test_sys_volume_set(self, dispatcher, profile_manager, mock_sys):
        profile_manager.set_pot_action(0, ActionType.SYS_VOLUME_SET.value, {}, "")
        # 512 / 1023 ≈ 0.500488
        dispatcher.on_pot_event(0, 512)
        mock_sys.volume_set.assert_called_once_with(512 / 1023.0)

    def test_obs_source_volume(self, dispatcher, profile_manager, mock_obs):
        profile_manager.set_pot_action(
            1, ActionType.OBS_SOURCE_VOLUME.value, {"source_name": "Mic"}, ""
        )
        # 1023 / 1023 = 1.0
        dispatcher.on_pot_event(1, 1023)
        mock_obs.set_source_volume_normalized.assert_called_once_with("Mic", 1.0)

    def test_none_action(self, dispatcher, profile_manager, mock_sys):
        profile_manager.set_pot_action(2, ActionType.NONE.value, {}, "")
        dispatcher.on_pot_event(2, 512)
        mock_sys.volume_set.assert_not_called()

    def test_unknown_pot_action(self, dispatcher, profile_manager):
        profile_manager.set_pot_action(0, "unknown_pot", {}, "")
        # Não deve crashear
        dispatcher.on_pot_event(0, 512)
