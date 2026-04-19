"""
Migration 0002 — Adiciona coluna 'inverted' à tabela pot_actions.

Permite inverter o comportamento dos potenciômetros:
quando ativado, maior resistência = menor volume.
"""

import logging

logger = logging.getLogger(__name__)


def upgrade(db):
    """Adiciona coluna inverted à tabela pot_actions."""
    logger.info("Adicionando coluna 'inverted' à tabela pot_actions...")

    db.execute("""
        ALTER TABLE pot_actions
        ADD COLUMN inverted INTEGER NOT NULL DEFAULT 0
    """)
