"""
Testes para o módulo Database — conexão, migrations e importação de dados.
"""

import json
import os
import tempfile

import pytest
from PySide6.QtWidgets import QApplication

from app.core.database import Database, MigrationRunner


@pytest.fixture(scope="session")
def qapp():
    """Cria uma QApplication para a sessão de testes."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def tmp_db(tmp_path):
    """Cria um banco de dados temporário."""
    db_path = str(tmp_path / "test.db")
    db = Database(db_path)
    yield db
    db.close()


# ══════════════════════════════════════════════════════════════
#  Testes do Database
# ══════════════════════════════════════════════════════════════


class TestDatabaseConnection:
    """Testes de conexão e operações básicas."""

    def test_creates_db_file(self, tmp_path):
        db_path = str(tmp_path / "new.db")
        db = Database(db_path)
        assert os.path.isfile(db_path)
        db.close()

    def test_schema_version_table_exists(self, tmp_db):
        row = tmp_db.fetchone(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
        )
        assert row is not None

    def test_initial_version_is_zero(self, tmp_db):
        assert tmp_db.get_current_version() == 0

    def test_execute_and_fetchone(self, tmp_db):
        tmp_db.execute(
            "CREATE TABLE test (id INTEGER PRIMARY KEY, val TEXT)"
        )
        tmp_db.execute("INSERT INTO test (val) VALUES (?)", ("hello",))
        tmp_db.commit()
        row = tmp_db.fetchone("SELECT val FROM test WHERE id = 1")
        assert row["val"] == "hello"

    def test_fetchall(self, tmp_db):
        tmp_db.execute(
            "CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT)"
        )
        tmp_db.execute("INSERT INTO items (name) VALUES ('a')")
        tmp_db.execute("INSERT INTO items (name) VALUES ('b')")
        tmp_db.commit()
        rows = tmp_db.fetchall("SELECT name FROM items ORDER BY name")
        assert len(rows) == 2
        assert rows[0]["name"] == "a"
        assert rows[1]["name"] == "b"

    def test_foreign_keys_enabled(self, tmp_db):
        row = tmp_db.fetchone("PRAGMA foreign_keys")
        assert row[0] == 1


# ══════════════════════════════════════════════════════════════
#  Testes do MigrationRunner
# ══════════════════════════════════════════════════════════════


class TestMigrationRunner:
    """Testes para o sistema de migrations."""

    def test_discover_finds_migrations(self, tmp_db):
        runner = MigrationRunner(tmp_db)
        migrations = runner.discover()
        # Deve encontrar ao menos 0001_initial
        assert len(migrations) >= 1
        assert migrations[0][0] == 1  # version
        assert "0001_initial" in migrations[0][1]  # name

    def test_pending_before_run(self, tmp_db):
        runner = MigrationRunner(tmp_db)
        pending = runner.get_pending()
        assert len(pending) >= 1

    def test_run_creates_tables(self, tmp_db):
        runner = MigrationRunner(tmp_db)
        runner.run_pending()

        # Verifica que as tabelas foram criadas
        tables = tmp_db.fetchall(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        table_names = [t["name"] for t in tables]
        assert "settings" in table_names
        assert "layouts" in table_names
        assert "button_actions" in table_names
        assert "pot_actions" in table_names

    def test_run_creates_default_layout(self, tmp_db):
        runner = MigrationRunner(tmp_db)
        runner.run_pending()

        row = tmp_db.fetchone("SELECT name, is_active FROM layouts LIMIT 1")
        assert row is not None
        assert row["name"] == "Layout 1"
        assert row["is_active"] == 1

    def test_run_creates_default_settings(self, tmp_db):
        runner = MigrationRunner(tmp_db)
        runner.run_pending()

        baud = tmp_db.fetchone(
            "SELECT value FROM settings WHERE key = 'serial_baudrate'"
        )
        assert baud["value"] == "115200"

    def test_version_updated_after_run(self, tmp_db):
        runner = MigrationRunner(tmp_db)
        runner.run_pending()
        assert tmp_db.get_current_version() >= 1

    def test_idempotent(self, tmp_db):
        """Rodar migrations duas vezes não causa erro."""
        runner = MigrationRunner(tmp_db)
        runner.run_pending()
        version1 = tmp_db.get_current_version()

        runner.run_pending()
        version2 = tmp_db.get_current_version()

        assert version1 == version2

    def test_no_pending_after_run(self, tmp_db):
        runner = MigrationRunner(tmp_db)
        runner.run_pending()
        assert len(runner.get_pending()) == 0


# ══════════════════════════════════════════════════════════════
#  Testes da importação do config.json
# ══════════════════════════════════════════════════════════════


class TestJsonImport:
    """Testes para importação de dados do config.json."""

    def _create_config_json(self, config_dir: str) -> str:
        """Cria um config.json de teste."""
        config = {
            "layouts": {
                "Streaming": {
                    "buttons": {
                        "0,0": {
                            "action": "obs_switch_scene",
                            "params": {"scene_name": "Gaming"},
                            "label": "Gaming",
                        },
                        "1,0": {
                            "action": "none",
                            "params": {},
                            "label": "",
                        },
                    },
                    "pots": {
                        "0": {
                            "action": "sys_volume_set",
                            "params": {},
                            "label": "Volume",
                        },
                    },
                },
                "Desktop": {
                    "buttons": {
                        "0,0": {
                            "action": "sys_hotkey",
                            "params": {"keys": "ctrl+c"},
                            "label": "Copiar",
                        },
                    },
                    "pots": {
                        "0": {"action": "none", "params": {}, "label": ""},
                    },
                },
            },
            "active_layout": "Streaming",
            "serial": {"port": "/dev/ttyACM0", "baudrate": 9600},
            "obs": {"host": "192.168.1.10", "port": 4460, "password": "s3nh4"},
        }

        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, "config.json")
        with open(config_path, "w") as f:
            json.dump(config, f)
        return config_path

    def test_imports_layouts(self, tmp_path):
        config_dir = str(tmp_path / "config")
        self._create_config_json(config_dir)

        db_path = str(tmp_path / "config" / "streamdeck.db")
        db = Database(db_path)
        runner = MigrationRunner(db)
        runner.run_pending()

        layouts = db.fetchall("SELECT name, is_active FROM layouts ORDER BY name")
        names = [l["name"] for l in layouts]
        assert "Streaming" in names
        assert "Desktop" in names

        # Streaming deve ser o ativo
        active = db.fetchone("SELECT name FROM layouts WHERE is_active = 1")
        assert active["name"] == "Streaming"
        db.close()

    def test_imports_button_actions(self, tmp_path):
        config_dir = str(tmp_path / "config")
        self._create_config_json(config_dir)

        db_path = str(tmp_path / "config" / "streamdeck.db")
        db = Database(db_path)
        MigrationRunner(db).run_pending()

        layout = db.fetchone("SELECT id FROM layouts WHERE name = 'Streaming'")
        btn = db.fetchone(
            "SELECT action, params, label FROM button_actions WHERE layout_id = ? AND row = 0 AND col = 0",
            (layout["id"],),
        )
        assert btn["action"] == "obs_switch_scene"
        assert json.loads(btn["params"])["scene_name"] == "Gaming"
        assert btn["label"] == "Gaming"
        db.close()

    def test_imports_serial_config(self, tmp_path):
        config_dir = str(tmp_path / "config")
        self._create_config_json(config_dir)

        db_path = str(tmp_path / "config" / "streamdeck.db")
        db = Database(db_path)
        MigrationRunner(db).run_pending()

        port = db.fetchone("SELECT value FROM settings WHERE key = 'serial_port'")
        assert port["value"] == "/dev/ttyACM0"

        baud = db.fetchone("SELECT value FROM settings WHERE key = 'serial_baudrate'")
        assert baud["value"] == "9600"
        db.close()

    def test_imports_obs_config(self, tmp_path):
        config_dir = str(tmp_path / "config")
        self._create_config_json(config_dir)

        db_path = str(tmp_path / "config" / "streamdeck.db")
        db = Database(db_path)
        MigrationRunner(db).run_pending()

        host = db.fetchone("SELECT value FROM settings WHERE key = 'obs_host'")
        assert host["value"] == "192.168.1.10"

        pwd = db.fetchone("SELECT value FROM settings WHERE key = 'obs_password'")
        assert pwd["value"] == "s3nh4"
        db.close()

    def test_renames_config_json(self, tmp_path):
        config_dir = str(tmp_path / "config")
        config_path = self._create_config_json(config_dir)

        db_path = str(tmp_path / "config" / "streamdeck.db")
        db = Database(db_path)
        MigrationRunner(db).run_pending()

        assert not os.path.exists(config_path)
        assert os.path.exists(config_path + ".bak")
        db.close()
