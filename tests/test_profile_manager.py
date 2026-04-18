"""
Testes para o ProfileManager — gerenciamento de layouts e configurações.

Usa diretório temporário para não interferir na configuração real.
"""

import json
import os

import pytest
from PySide6.QtWidgets import QApplication

from app.core.profile_manager import (
    ProfileManager,
    ActionType,
    ACTION_METADATA,
)


# ── Fixture para QApplication (necessário para QObject/Signals) ──


@pytest.fixture(scope="session")
def qapp():
    """Cria uma QApplication para a sessão de testes."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def tmp_config_dir(tmp_path):
    """Cria um diretório temporário para configuração."""
    return str(tmp_path / "config")


@pytest.fixture
def manager(qapp, tmp_config_dir):
    """Cria um ProfileManager com diretório temporário."""
    return ProfileManager(config_dir=tmp_config_dir)


# ══════════════════════════════════════════════════════════════
#  Testes do ProfileManager
# ══════════════════════════════════════════════════════════════


class TestProfileManagerInit:
    """Testes de inicialização."""

    def test_creates_config_dir(self, manager, tmp_config_dir):
        assert os.path.isdir(tmp_config_dir)

    def test_creates_db_file(self, manager, tmp_config_dir):
        db_file = os.path.join(tmp_config_dir, "streamdeck.db")
        assert os.path.isfile(db_file)

    def test_default_layout_exists(self, manager):
        names = manager.get_layout_names()
        assert "Layout 1" in names

    def test_active_layout_is_layout_1(self, manager):
        assert manager.get_active_layout_name() == "Layout 1"


class TestLayoutManagement:
    """Testes de CRUD de layouts."""

    def test_create_layout(self, manager):
        assert manager.create_layout("Gaming")
        assert "Gaming" in manager.get_layout_names()

    def test_create_duplicate_fails(self, manager):
        manager.create_layout("Teste")
        assert not manager.create_layout("Teste")

    def test_switch_layout(self, manager):
        manager.create_layout("OBS")
        assert manager.switch_layout("OBS")
        assert manager.get_active_layout_name() == "OBS"

    def test_switch_nonexistent_fails(self, manager):
        assert not manager.switch_layout("NãoExiste")

    def test_duplicate_layout(self, manager):
        manager.create_layout("Original")
        assert manager.duplicate_layout("Original", "Cópia")
        assert "Cópia" in manager.get_layout_names()

    def test_duplicate_to_existing_fails(self, manager):
        manager.create_layout("A")
        manager.create_layout("B")
        assert not manager.duplicate_layout("A", "B")

    def test_rename_layout(self, manager):
        manager.create_layout("Antigo")
        assert manager.rename_layout("Antigo", "Novo")
        assert "Novo" in manager.get_layout_names()
        assert "Antigo" not in manager.get_layout_names()

    def test_rename_active_updates_active(self, manager):
        manager.create_layout("Ativo")
        manager.switch_layout("Ativo")
        manager.rename_layout("Ativo", "Renomeado")
        assert manager.get_active_layout_name() == "Renomeado"

    def test_delete_layout(self, manager):
        manager.create_layout("ParaDeletar")
        assert manager.delete_layout("ParaDeletar")
        assert "ParaDeletar" not in manager.get_layout_names()

    def test_delete_last_layout_fails(self, manager):
        """Não pode deletar o último layout."""
        assert not manager.delete_layout("Layout 1")

    def test_delete_active_switches(self, manager):
        manager.create_layout("Segundo")
        manager.switch_layout("Segundo")
        manager.delete_layout("Segundo")
        # Deve ter trocado para outro layout
        assert manager.get_active_layout_name() != "Segundo"


class TestButtonActions:
    """Testes de configuração de botões."""

    def test_default_action_is_none(self, manager):
        action = manager.get_button_action(0, 0)
        assert action["action"] == ActionType.NONE.value

    def test_set_and_get_button(self, manager):
        manager.set_button_action(
            1, 2, ActionType.OBS_SWITCH_SCENE.value,
            {"scene_name": "Gaming"}, "Cena Gaming"
        )
        action = manager.get_button_action(1, 2)
        assert action["action"] == ActionType.OBS_SWITCH_SCENE.value
        assert action["params"]["scene_name"] == "Gaming"
        assert action["label"] == "Cena Gaming"

    def test_button_persists_on_reload(self, qapp, tmp_config_dir):
        """Configuração deve persistir entre instâncias."""
        mgr1 = ProfileManager(config_dir=tmp_config_dir)
        mgr1.set_button_action(
            0, 0, ActionType.SYS_HOTKEY.value,
            {"keys": "ctrl+s"}, "Salvar"
        )

        mgr2 = ProfileManager(config_dir=tmp_config_dir)
        action = mgr2.get_button_action(0, 0)
        assert action["action"] == ActionType.SYS_HOTKEY.value


class TestPotActions:
    """Testes de configuração de potenciômetros."""

    def test_default_action_is_none(self, manager):
        action = manager.get_pot_action(0)
        assert action["action"] == ActionType.NONE.value

    def test_set_and_get_pot(self, manager):
        manager.set_pot_action(
            1, ActionType.SYS_VOLUME_SET.value,
            {}, "Volume"
        )
        action = manager.get_pot_action(1)
        assert action["action"] == ActionType.SYS_VOLUME_SET.value
        assert action["label"] == "Volume"


class TestConnectionConfigs:
    """Testes de configuração serial e OBS."""

    def test_default_serial(self, manager):
        cfg = manager.get_serial_config()
        assert cfg["baudrate"] == 115200

    def test_set_serial(self, manager):
        manager.set_serial_config("/dev/ttyACM0", 9600)
        cfg = manager.get_serial_config()
        assert cfg["port"] == "/dev/ttyACM0"
        assert cfg["baudrate"] == 9600

    def test_default_obs(self, manager):
        cfg = manager.get_obs_config()
        assert cfg["host"] == "localhost"
        assert cfg["port"] == 4455

    def test_set_obs(self, manager):
        manager.set_obs_config("192.168.1.100", 4460, "senha123")
        cfg = manager.get_obs_config()
        assert cfg["host"] == "192.168.1.100"
        assert cfg["port"] == 4460
        assert cfg["password"] == "senha123"


# ══════════════════════════════════════════════════════════════
#  Testes dos ActionTypes e Metadados
# ══════════════════════════════════════════════════════════════


class TestActionTypes:
    """Testes para os tipos de ação e seus metadados."""

    def test_all_actions_have_metadata(self):
        """Todo ActionType deve ter entrada no ACTION_METADATA."""
        for action in ActionType:
            assert action in ACTION_METADATA, (
                f"ActionType.{action.name} não tem metadados"
            )

    def test_metadata_has_required_keys(self):
        """Cada metadado deve ter as chaves necessárias."""
        required = {"label", "category", "params", "for_pot"}
        for action, meta in ACTION_METADATA.items():
            assert required.issubset(meta.keys()), (
                f"Metadados de {action.name} faltam chaves: "
                f"{required - meta.keys()}"
            )

    def test_none_action_exists(self):
        assert ActionType.NONE.value == "none"

    def test_action_values_are_strings(self):
        for action in ActionType:
            assert isinstance(action.value, str)


class TestLayoutData:
    """Testes para get_active_layout que retorna dict completo."""

    def test_returns_dict_with_buttons_and_pots(self, manager):
        layout = manager.get_active_layout()
        assert "buttons" in layout
        assert "pots" in layout

    def test_has_15_buttons(self, manager):
        layout = manager.get_active_layout()
        assert len(layout["buttons"]) == 15

    def test_has_3_pots(self, manager):
        layout = manager.get_active_layout()
        assert len(layout["pots"]) == 3

    def test_button_keys_format(self, manager):
        layout = manager.get_active_layout()
        for row in range(3):
            for col in range(5):
                assert f"{row},{col}" in layout["buttons"]
