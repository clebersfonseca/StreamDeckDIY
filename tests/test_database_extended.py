"""
Extended tests for app.core.database — covers uncovered lines:
  - executemany (line 56)
  - close sets _conn to None (line 67)
  - connection / db_path properties
  - MigrationRunner.discover with missing directory (line 147)
  - MigrationRunner.discover skipping logic (non-.py, underscore, non-numeric)
  - MigrationRunner.run_pending exception handling (lines 193-195)
  - Database._register_migration (line 115-120)
"""

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.database import Database, MigrationRunner


@pytest.fixture
def tmp_db(tmp_path):
    """Create a temporary database."""
    db_path = str(tmp_path / "test.db")
    db = Database(db_path)
    yield db
    db.close()


# ══════════════════════════════════════════════════════════════
#  Database helper methods
# ══════════════════════════════════════════════════════════════


class TestDatabaseExtended:
    """Tests for previously-uncovered Database helpers."""

    def test_executemany(self, tmp_db):
        tmp_db.execute("CREATE TABLE bulk (id INTEGER PRIMARY KEY, v TEXT)")
        tmp_db.executemany(
            "INSERT INTO bulk (v) VALUES (?)",
            [("a",), ("b",), ("c",)],
        )
        tmp_db.commit()
        rows = tmp_db.fetchall("SELECT v FROM bulk ORDER BY v")
        assert [r["v"] for r in rows] == ["a", "b", "c"]

    def test_executescript_multiple(self, tmp_db):
        tmp_db.executescript("""
            CREATE TABLE t1 (id INTEGER PRIMARY KEY, name TEXT);
            INSERT INTO t1 (name) VALUES ('x');
            CREATE TABLE t2 (id INTEGER PRIMARY KEY, label TEXT);
            INSERT INTO t2 (label) VALUES ('y');
        """)
        row1 = tmp_db.fetchone("SELECT name FROM t1")
        row2 = tmp_db.fetchone("SELECT label FROM t2")
        assert row1["name"] == "x"
        assert row2["label"] == "y"

    def test_close_sets_conn_none(self, tmp_path):
        db = Database(str(tmp_path / "close.db"))
        assert db._conn is not None
        db.close()
        assert db._conn is None

    def test_close_idempotent(self, tmp_path):
        db = Database(str(tmp_path / "close2.db"))
        db.close()
        db.close()  # should not raise

    def test_connection_property(self, tmp_db):
        conn = tmp_db.connection
        assert isinstance(conn, sqlite3.Connection)

    def test_db_path_property(self, tmp_path):
        db_path = str(tmp_path / "path.db")
        db = Database(db_path)
        assert db.db_path == db_path
        db.close()

    def test_register_migration(self, tmp_db):
        tmp_db._register_migration(99, "0099_test")
        tmp_db.commit()
        row = tmp_db.fetchone(
            "SELECT version, name FROM schema_version WHERE version = 99"
        )
        assert row is not None
        assert row["version"] == 99
        assert row["name"] == "0099_test"


# ══════════════════════════════════════════════════════════════
#  MigrationRunner.discover edge cases
# ══════════════════════════════════════════════════════════════


class TestMigrationRunnerDiscover:
    """Tests for MigrationRunner.discover filtering logic."""

    def test_discover_missing_directory(self, tmp_db, tmp_path):
        runner = MigrationRunner(tmp_db, migrations_dir=tmp_path / "nonexistent")
        assert runner.discover() == []

    def test_discover_skips_non_py_files(self, tmp_db, tmp_path):
        mdir = tmp_path / "migs"
        mdir.mkdir()
        (mdir / "0001_init.txt").touch()
        (mdir / "0002_other.sql").touch()
        runner = MigrationRunner(tmp_db, migrations_dir=mdir)
        assert runner.discover() == []

    def test_discover_skips_underscore_files(self, tmp_db, tmp_path):
        mdir = tmp_path / "migs"
        mdir.mkdir()
        (mdir / "__init__.py").touch()
        (mdir / "_private.py").touch()
        runner = MigrationRunner(tmp_db, migrations_dir=mdir)
        assert runner.discover() == []

    def test_discover_skips_non_numeric_prefix(self, tmp_db, tmp_path):
        mdir = tmp_path / "migs"
        mdir.mkdir()
        (mdir / "abc_test.py").touch()
        runner = MigrationRunner(tmp_db, migrations_dir=mdir)
        assert runner.discover() == []

    def test_discover_valid_migration(self, tmp_db, tmp_path):
        mdir = tmp_path / "migs"
        mdir.mkdir()
        (mdir / "0001_initial.py").touch()
        runner = MigrationRunner(tmp_db, migrations_dir=mdir)
        result = runner.discover()
        assert len(result) == 1
        assert result[0][0] == 1
        assert result[0][1] == "0001_initial"


# ══════════════════════════════════════════════════════════════
#  MigrationRunner.run_pending exception handling
# ══════════════════════════════════════════════════════════════


class TestMigrationRunnerRunPending:
    """Tests for run_pending error propagation (lines 193-195)."""

    def test_run_pending_bad_migration(self, tmp_db):
        bad_module = MagicMock()
        bad_module.upgrade.side_effect = RuntimeError("migration exploded")

        runner = MigrationRunner(tmp_db)
        runner.get_pending = MagicMock(
            return_value=[(999, "0999_bad", "fake.module")]
        )

        with patch("importlib.import_module", return_value=bad_module):
            with pytest.raises(RuntimeError, match="migration exploded"):
                runner.run_pending()
