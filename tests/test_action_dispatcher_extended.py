"""
Extended tests for ActionDispatcher — covers uncovered lines:
  - line 70: inverted pot normalization
  - lines 189-190: button action exception handling
  - line 204: unknown pot action logging
  - lines 209-210: pot action exception handling
Also adds edge-case and signal-emission tests.
"""

from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QApplication

from app.core.action_dispatcher import ActionDispatcher
from app.core.profile_manager import ActionType, ProfileManager


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def profile_manager(tmp_path):
    return ProfileManager(config_dir=str(tmp_path))


@pytest.fixture
def mock_obs():
    return MagicMock()


@pytest.fixture
def mock_sys():
    return MagicMock()


@pytest.fixture
def dispatcher(profile_manager, mock_obs, mock_sys, qapp):
    return ActionDispatcher(
        profile_manager=profile_manager,
        obs_controller=mock_obs,
        system_controller=mock_sys,
    )


class TestPotInverted:
    """Covers line 70: normalized = 1.0 - normalized when inverted=True."""

    def test_pot_inverted(self, dispatcher, profile_manager, mock_sys):
        profile_manager.set_pot_action(
            0, ActionType.SYS_VOLUME_SET.value, {}, "", inverted=True
        )
        dispatcher.on_pot_event(0, 0)
        # 0 / 1023 = 0.0, inverted → 1.0
        mock_sys.volume_set.assert_called_once_with(1.0)

    def test_pot_inverted_mid_value(self, dispatcher, profile_manager, mock_sys):
        profile_manager.set_pot_action(
            0, ActionType.SYS_VOLUME_SET.value, {}, "", inverted=True
        )
        dispatcher.on_pot_event(0, 1023)
        # 1023 / 1023 = 1.0, inverted → 0.0
        mock_sys.volume_set.assert_called_once_with(0.0)


class TestButtonActionException:
    """Covers lines 189-190: exception caught in _execute_button_action."""

    def test_button_action_exception_is_caught(
        self, dispatcher, profile_manager, mock_obs
    ):
        mock_obs.start_streaming.side_effect = RuntimeError("connection lost")
        profile_manager.set_button_action(
            0, 0, ActionType.OBS_START_STREAMING.value, {}, ""
        )
        # Must not propagate the exception
        dispatcher.on_button_event(0, 0, pressed=True)


class TestPotActionException:
    """Covers lines 209-210: exception caught in _execute_pot_action."""

    def test_pot_action_exception_is_caught(
        self, dispatcher, profile_manager, mock_sys
    ):
        mock_sys.volume_set.side_effect = OSError("audio device error")
        profile_manager.set_pot_action(
            0, ActionType.SYS_VOLUME_SET.value, {}, ""
        )
        # Must not propagate the exception
        dispatcher.on_pot_event(0, 512)

    def test_pot_action_obs_exception_is_caught(
        self, dispatcher, profile_manager, mock_obs
    ):
        mock_obs.set_source_volume_normalized.side_effect = RuntimeError("obs down")
        profile_manager.set_pot_action(
            1, ActionType.OBS_SOURCE_VOLUME.value, {"source_name": "Mic"}, ""
        )
        dispatcher.on_pot_event(1, 512)


class TestMissingParams:
    """Tests that actions with missing/empty params do not call controller methods."""

    def test_obs_source_volume_missing_source_name(
        self, dispatcher, profile_manager, mock_obs
    ):
        profile_manager.set_pot_action(
            0, ActionType.OBS_SOURCE_VOLUME.value, {"source_name": ""}, ""
        )
        dispatcher.on_pot_event(0, 512)
        mock_obs.set_source_volume_normalized.assert_not_called()

    def test_obs_source_volume_no_source_key(
        self, dispatcher, profile_manager, mock_obs
    ):
        profile_manager.set_pot_action(
            0, ActionType.OBS_SOURCE_VOLUME.value, {}, ""
        )
        dispatcher.on_pot_event(0, 512)
        mock_obs.set_source_volume_normalized.assert_not_called()

    def test_button_action_missing_scene_name(
        self, dispatcher, profile_manager, mock_obs
    ):
        profile_manager.set_button_action(
            0, 0, ActionType.OBS_SWITCH_SCENE.value, {"scene_name": ""}, ""
        )
        dispatcher.on_button_event(0, 0, pressed=True)
        mock_obs.switch_scene.assert_not_called()

    def test_button_action_missing_source_name_for_toggle(
        self, dispatcher, profile_manager, mock_obs
    ):
        profile_manager.set_button_action(
            0, 0, ActionType.OBS_TOGGLE_SOURCE.value,
            {"scene_name": "Main", "source_name": ""}, ""
        )
        dispatcher.on_button_event(0, 0, pressed=True)
        mock_obs.toggle_source.assert_not_called()

    def test_button_action_missing_source_name_for_mute(
        self, dispatcher, profile_manager, mock_obs
    ):
        profile_manager.set_button_action(
            0, 0, ActionType.OBS_TOGGLE_MUTE.value, {"source_name": ""}, ""
        )
        dispatcher.on_button_event(0, 0, pressed=True)
        mock_obs.toggle_mute.assert_not_called()

    def test_button_action_missing_keys_for_hotkey(
        self, dispatcher, profile_manager, mock_sys
    ):
        profile_manager.set_button_action(
            0, 0, ActionType.SYS_HOTKEY.value, {"keys": ""}, ""
        )
        dispatcher.on_button_event(0, 0, pressed=True)
        mock_sys.hotkey.assert_not_called()

    def test_button_action_missing_path_for_open_app(
        self, dispatcher, profile_manager, mock_sys
    ):
        profile_manager.set_button_action(
            0, 0, ActionType.SYS_OPEN_APP.value, {"path": ""}, ""
        )
        dispatcher.on_button_event(0, 0, pressed=True)
        mock_sys.open_app.assert_not_called()

    def test_button_action_missing_command_for_run(
        self, dispatcher, profile_manager, mock_sys
    ):
        profile_manager.set_button_action(
            0, 0, ActionType.SYS_RUN_COMMAND.value, {"command": ""}, ""
        )
        dispatcher.on_button_event(0, 0, pressed=True)
        mock_sys.run_command.assert_not_called()


class TestActionExecutedSignal:
    """Verifies that action_executed signal is emitted with the correct text."""

    def test_signal_on_switch_scene(self, dispatcher, profile_manager, mock_obs):
        signal_spy = MagicMock()
        dispatcher.action_executed.connect(signal_spy)
        profile_manager.set_button_action(
            0, 0, ActionType.OBS_SWITCH_SCENE.value, {"scene_name": "Game"}, ""
        )
        dispatcher.on_button_event(0, 0, pressed=True)
        signal_spy.assert_called_once_with("Cena: Game")

    def test_signal_on_volume_up(self, dispatcher, profile_manager, mock_sys):
        signal_spy = MagicMock()
        dispatcher.action_executed.connect(signal_spy)
        profile_manager.set_button_action(
            0, 0, ActionType.SYS_VOLUME_UP.value, {}, ""
        )
        dispatcher.on_button_event(0, 0, pressed=True)
        signal_spy.assert_called_once_with("Volume +")

    def test_signal_on_start_streaming(self, dispatcher, profile_manager, mock_obs):
        signal_spy = MagicMock()
        dispatcher.action_executed.connect(signal_spy)
        profile_manager.set_button_action(
            0, 0, ActionType.OBS_START_STREAMING.value, {}, ""
        )
        dispatcher.on_button_event(0, 0, pressed=True)
        signal_spy.assert_called_once_with("Streaming iniciado")

    def test_signal_on_layout_switch(self, dispatcher, profile_manager):
        signal_spy = MagicMock()
        dispatcher.action_executed.connect(signal_spy)
        profile_manager.set_button_action(
            0, 0, ActionType.APP_SWITCH_LAYOUT.value,
            {"layout_name": "Gaming"}, ""
        )
        dispatcher.on_button_event(0, 0, pressed=True)
        signal_spy.assert_called_once_with("Layout: Gaming")


class TestPotBoundaryValues:
    """Tests pot events at min and max values."""

    def test_pot_zero_value(self, dispatcher, profile_manager, mock_sys):
        profile_manager.set_pot_action(
            0, ActionType.SYS_VOLUME_SET.value, {}, ""
        )
        dispatcher.on_pot_event(0, 0)
        mock_sys.volume_set.assert_called_once_with(0.0)

    def test_pot_max_value(self, dispatcher, profile_manager, mock_sys):
        profile_manager.set_pot_action(
            0, ActionType.SYS_VOLUME_SET.value, {}, ""
        )
        dispatcher.on_pot_event(0, 1023)
        mock_sys.volume_set.assert_called_once_with(1.0)
