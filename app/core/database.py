"""
Database — Motor de banco de dados SQLite e sistema de migrations.

Gerencia a conexão com o banco e executa migrations pendentes
automaticamente na inicialização da aplicação.
"""

import importlib
import logging
import os
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

# Diretório padrão de migrations
_MIGRATIONS_PACKAGE = "app.core.migrations"
_MIGRATIONS_DIR = Path(__file__).parent / "migrations"


class Database:
    """
    Gerenciador do banco de dados SQLite.

    Fornece conexão, helpers de query, e execução de migrations.
    """

    def __init__(self, db_path: str = None):
        if db_path is None:
            config_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "config",
            )
            os.makedirs(config_dir, exist_ok=True)
            db_path = os.path.join(config_dir, "streamdeck.db")

        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None

        self._connect()
        self._ensure_schema_version_table()

    # ── Conexão ──────────────────────────────────────────────

    def _connect(self):
        """Abre a conexão com o banco de dados."""
        logger.info("Conectando ao banco de dados: %s", self._db_path)
        self._conn = sqlite3.connect(self._db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")

    @property
    def connection(self) -> sqlite3.Connection:
        """Retorna a conexão ativa."""
        return self._conn

    @property
    def db_path(self) -> str:
        """Retorna o caminho do banco de dados."""
        return self._db_path

    def close(self):
        """Fecha a conexão."""
        if self._conn:
            self._conn.close()
            self._conn = None

    # ── Helpers de Query ─────────────────────────────────────

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Executa uma query SQL."""
        return self._conn.execute(sql, params)

    def executemany(self, sql: str, params_list: list) -> sqlite3.Cursor:
        """Executa uma query SQL para múltiplos parâmetros."""
        return self._conn.executemany(sql, params_list)

    def executescript(self, sql: str):
        """Executa múltiplas queries SQL de uma vez."""
        self._conn.executescript(sql)

    def fetchone(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        """Executa e retorna uma linha."""
        return self._conn.execute(sql, params).fetchone()

    def fetchall(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        """Executa e retorna todas as linhas."""
        return self._conn.execute(sql, params).fetchall()

    def commit(self):
        """Faz commit da transação."""
        self._conn.commit()

    # ── Schema Version ───────────────────────────────────────

    def _ensure_schema_version_table(self):
        """Cria a tabela de controle de migrations se não existir."""
        self.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version  INTEGER PRIMARY KEY,
                name     TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.commit()

    def get_current_version(self) -> int:
        """Retorna a versão atual do schema (0 se nenhuma migration foi aplicada)."""
        row = self.fetchone(
            "SELECT MAX(version) as ver FROM schema_version"
        )
        return row["ver"] if row and row["ver"] is not None else 0

    def _register_migration(self, version: int, name: str):
        """Registra que uma migration foi aplicada."""
        self.execute(
            "INSERT INTO schema_version (version, name) VALUES (?, ?)",
            (version, name),
        )


class MigrationRunner:
    """
    Descobre e executa migrations pendentes.

    Migrations são módulos Python em app/core/migrations/ com o padrão:
        NNNN_descricao.py

    Cada módulo deve ter uma função:
        upgrade(db: Database) -> None
    """

    def __init__(self, db: Database, migrations_dir: Path = None):
        self._db = db
        self._migrations_dir = migrations_dir or _MIGRATIONS_DIR

    def discover(self) -> list[tuple[int, str, str]]:
        """
        Descobre todas as migrations disponíveis.

        Retorna lista de (version, name, module_name) ordenada por version.
        """
        migrations = []

        if not self._migrations_dir.exists():
            return migrations

        for f in sorted(self._migrations_dir.iterdir()):
            if f.suffix != ".py" or f.name.startswith("_"):
                continue

            # Extrai número: "0001_initial.py" → 1
            parts = f.stem.split("_", 1)
            if not parts[0].isdigit():
                continue

            version = int(parts[0])
            name = f.stem
            module_name = f"{_MIGRATIONS_PACKAGE}.{f.stem}"
            migrations.append((version, name, module_name))

        return migrations

    def get_pending(self) -> list[tuple[int, str, str]]:
        """Retorna as migrations que ainda não foram aplicadas."""
        current = self._db.get_current_version()
        return [
            (ver, name, mod)
            for ver, name, mod in self.discover()
            if ver > current
        ]

    def run_pending(self):
        """Executa todas as migrations pendentes em ordem."""
        pending = self.get_pending()

        if not pending:
            logger.info(
                "Banco de dados atualizado (versão %d).",
                self._db.get_current_version(),
            )
            return

        for version, name, module_name in pending:
            logger.info("Executando migration %s...", name)
            try:
                module = importlib.import_module(module_name)
                module.upgrade(self._db)
                self._db._register_migration(version, name)
                self._db.commit()
                logger.info("Migration %s aplicada com sucesso.", name)
            except Exception:
                logger.exception("Erro ao executar migration %s", name)
                raise

        logger.info(
            "Todas as migrations aplicadas. Versão atual: %d",
            self._db.get_current_version(),
        )
