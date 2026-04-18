"""
Migration 0001 — Schema inicial do banco de dados.

Cria as tabelas base e importa dados do config.json existente (se houver).
"""

import json
import logging
import os

logger = logging.getLogger(__name__)


def upgrade(db):
    """Cria o schema inicial e migra dados do config.json."""

    # ── 1. Criar tabelas ─────────────────────────────────────

    db.executescript("""
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS layouts (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            name      TEXT NOT NULL UNIQUE,
            is_active INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS button_actions (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            layout_id INTEGER NOT NULL,
            row       INTEGER NOT NULL,
            col       INTEGER NOT NULL,
            action    TEXT NOT NULL DEFAULT 'none',
            params    TEXT NOT NULL DEFAULT '{}',
            label     TEXT NOT NULL DEFAULT '',
            FOREIGN KEY (layout_id) REFERENCES layouts(id) ON DELETE CASCADE,
            UNIQUE(layout_id, row, col)
        );

        CREATE TABLE IF NOT EXISTS pot_actions (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            layout_id INTEGER NOT NULL,
            pot_index INTEGER NOT NULL,
            action    TEXT NOT NULL DEFAULT 'none',
            params    TEXT NOT NULL DEFAULT '{}',
            label     TEXT NOT NULL DEFAULT '',
            FOREIGN KEY (layout_id) REFERENCES layouts(id) ON DELETE CASCADE,
            UNIQUE(layout_id, pot_index)
        );
    """)

    # ── 2. Importar dados do config.json (se existir) ────────

    config_dir = os.path.dirname(os.path.abspath(db.db_path))
    config_path = os.path.join(config_dir, "config.json")

    if os.path.exists(config_path):
        _import_from_json(db, config_path)
    else:
        _create_defaults(db)


def _import_from_json(db, config_path: str):
    """Importa dados do config.json existente para o SQLite."""
    logger.info("Importando dados de %s para SQLite...", config_path)

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error("Erro ao ler config.json: %s. Criando dados padrão.", e)
        _create_defaults(db)
        return

    # ── Settings (serial + OBS) ──
    serial = config.get("serial", {})
    db.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        ("serial_port", serial.get("port", "")),
    )
    db.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        ("serial_baudrate", str(serial.get("baudrate", 115200))),
    )

    obs = config.get("obs", {})
    db.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        ("obs_host", obs.get("host", "localhost")),
    )
    db.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        ("obs_port", str(obs.get("port", 4455))),
    )
    db.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        ("obs_password", obs.get("password", "")),
    )

    # ── Layouts ──
    active_layout = config.get("active_layout", "")
    layouts = config.get("layouts", {})

    if not layouts:
        _create_defaults(db)
        return

    for layout_name, layout_data in layouts.items():
        is_active = 1 if layout_name == active_layout else 0
        db.execute(
            "INSERT INTO layouts (name, is_active) VALUES (?, ?)",
            (layout_name, is_active),
        )
        layout_id = db.fetchone(
            "SELECT id FROM layouts WHERE name = ?", (layout_name,)
        )["id"]

        # Botões
        buttons = layout_data.get("buttons", {})
        for key, btn_data in buttons.items():
            parts = key.split(",")
            if len(parts) != 2:
                continue
            row, col = int(parts[0]), int(parts[1])
            db.execute(
                """INSERT INTO button_actions
                   (layout_id, row, col, action, params, label)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    layout_id,
                    row,
                    col,
                    btn_data.get("action", "none"),
                    json.dumps(btn_data.get("params", {})),
                    btn_data.get("label", ""),
                ),
            )

        # Potenciômetros
        pots = layout_data.get("pots", {})
        for idx_str, pot_data in pots.items():
            db.execute(
                """INSERT INTO pot_actions
                   (layout_id, pot_index, action, params, label)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    layout_id,
                    int(idx_str),
                    pot_data.get("action", "none"),
                    json.dumps(pot_data.get("params", {})),
                    pot_data.get("label", ""),
                ),
            )

    # ── Renomear config.json para backup ──
    backup_path = config_path + ".bak"
    try:
        os.rename(config_path, backup_path)
        logger.info("config.json renomeado para config.json.bak")
    except OSError as e:
        logger.warning("Não foi possível renomear config.json: %s", e)

    logger.info("Importação concluída com sucesso!")


def _create_defaults(db):
    """Cria configurações e layout padrão."""
    logger.info("Criando configurações padrão...")

    # Settings padrão
    defaults = [
        ("serial_port", ""),
        ("serial_baudrate", "115200"),
        ("obs_host", "localhost"),
        ("obs_port", "4455"),
        ("obs_password", ""),
    ]
    db.executemany(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        defaults,
    )

    # Layout padrão
    db.execute(
        "INSERT INTO layouts (name, is_active) VALUES (?, ?)",
        ("Layout 1", 1),
    )
    layout_id = db.fetchone(
        "SELECT id FROM layouts WHERE name = ?", ("Layout 1",)
    )["id"]

    # 15 botões (3×5)
    for row in range(3):
        for col in range(5):
            db.execute(
                """INSERT INTO button_actions
                   (layout_id, row, col, action, params, label)
                   VALUES (?, ?, ?, 'none', '{}', '')""",
                (layout_id, row, col),
            )

    # 3 potenciômetros
    for i in range(3):
        db.execute(
            """INSERT INTO pot_actions
               (layout_id, pot_index, action, params, label)
               VALUES (?, ?, 'none', '{}', '')""",
            (layout_id, i),
        )
