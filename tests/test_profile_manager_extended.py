"""
Extended tests for ProfileManager — covers edge cases and missing coverage lines.
"""

import pytest
from PySide6.QtWidgets import QApplication

from app.core.profile_manager import ProfileManager, ActionType


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def manager(qapp, tmp_path):
    return ProfileManager(config_dir=str(tmp_path / "config"))


class TestEmptyLayoutDict:
    def test_empty_layout_dict(self):
        result = ProfileManager._empty_layout_dict()
        assert "buttons" in result
        assert "pots" in result
        assert len(result["buttons"]) == 15
        assert len(result["pots"]) == 3
        for r in range(3):
            for c in range(5):
                btn = result["buttons"][f"{r},{c}"]
                assert btn["action"] == ActionType.NONE.value
                assert btn["params"] == {}
                assert btn["label"] == ""
        for i in range(3):
            pot = result["pots"][str(i)]
            assert pot["action"] == ActionType.NONE.value
            assert pot["params"] == {}
            assert pot["label"] == ""
            assert pot["inverted"] is False


class TestActiveLayoutFallback:
    def test_get_active_layout_name_fallback(self, manager):
        """When no layout has is_active=1, falls back to first layout by id."""
        manager._db.execute("UPDATE layouts SET is_active = 0")
        manager._db.commit()
        name = manager.get_active_layout_name()
        assert name == "Layout 1"


class TestGetLayoutDataNonexistent:
    def test_get_layout_data_nonexistent(self, manager):
        result = manager._get_layout_data("does_not_exist")
        expected = ProfileManager._empty_layout_dict()
        assert result == expected


class TestDuplicateLayoutSourceNotFound:
    def test_duplicate_layout_source_not_found(self, manager):
        assert manager.duplicate_layout("ghost", "copy") is False


class TestRenameLayoutEdgeCases:
    def test_rename_layout_old_not_found(self, manager):
        assert manager.rename_layout("nonexistent", "new_name") is False

    def test_rename_layout_new_already_exists(self, manager):
        manager.create_layout("Alpha")
        manager.create_layout("Beta")
        assert manager.rename_layout("Alpha", "Beta") is False


class TestDeleteNonexistentLayout:
    def test_delete_nonexistent_layout(self, manager):
        manager.create_layout("Extra")
        assert manager.delete_layout("no_such_layout") is False


class TestSystemConfig:
    def test_get_system_config_default(self, manager):
        cfg = manager.get_system_config()
        assert cfg == {"autostart": False}

    def test_set_system_config(self, manager):
        manager.set_system_config(autostart=True)
        cfg = manager.get_system_config()
        assert cfg["autostart"] is True

        manager.set_system_config(autostart=False)
        cfg = manager.get_system_config()
        assert cfg["autostart"] is False


class TestPotActionInverted:
    def test_set_pot_action_inverted(self, manager):
        manager.set_pot_action(
            0, ActionType.SYS_VOLUME_SET.value, {}, "Vol", inverted=True
        )
        action = manager.get_pot_action(0)
        assert action["action"] == ActionType.SYS_VOLUME_SET.value
        assert action["inverted"] is True


class TestNoLayoutInDB:
    """Tests for actions when all layouts have been removed from the DB."""

    def _remove_all_layouts(self, manager):
        manager._db.execute("DELETE FROM button_actions")
        manager._db.execute("DELETE FROM pot_actions")
        manager._db.execute("DELETE FROM layouts")
        manager._db.commit()

    def test_get_button_action_no_layout_in_db(self, manager):
        self._remove_all_layouts(manager)
        result = manager.get_button_action(0, 0)
        assert result["action"] == ActionType.NONE.value
        assert result["params"] == {}
        assert result["label"] == ""

    def test_set_button_action_no_layout_in_db(self, manager):
        self._remove_all_layouts(manager)
        # Should return early without error
        manager.set_button_action(0, 0, ActionType.SYS_HOTKEY.value, {"keys": "a"}, "A")

    def test_get_pot_action_no_layout_in_db(self, manager):
        self._remove_all_layouts(manager)
        result = manager.get_pot_action(0)
        assert result["action"] == ActionType.NONE.value
        assert result["params"] == {}
        assert result["label"] == ""
        assert result["inverted"] is False

    def test_set_pot_action_no_layout_in_db(self, manager):
        self._remove_all_layouts(manager)
        # Should return early without error
        manager.set_pot_action(0, ActionType.SYS_VOLUME_SET.value, {}, "Vol")


class TestDuplicateLayoutPreservesActions:
    def test_duplicate_layout_preserves_actions(self, manager):
        manager.create_layout("Source")
        manager.switch_layout("Source")
        manager.set_button_action(
            1, 3, ActionType.OBS_SWITCH_SCENE.value,
            {"scene_name": "Main"}, "Main Scene"
        )
        manager.duplicate_layout("Source", "Copy")
        manager.switch_layout("Copy")
        action = manager.get_button_action(1, 3)
        assert action["action"] == ActionType.OBS_SWITCH_SCENE.value
        assert action["params"]["scene_name"] == "Main"
        assert action["label"] == "Main Scene"


class TestDeleteActiveLayoutActivatesAnother:
    def test_delete_active_layout_activates_another(self, manager):
        manager.create_layout("Second")
        manager.switch_layout("Second")
        assert manager.get_active_layout_name() == "Second"
        manager.delete_layout("Second")
        active = manager.get_active_layout_name()
        assert active != "Second"
        assert active in manager.get_layout_names()
