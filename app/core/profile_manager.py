"""
ProfileManager — Gerencia layouts/perfis de mapeamento.

Cada layout define o que cada botão e potenciômetro faz.
Suporta múltiplos layouts (ex: "OBS Streaming", "Windows", "Gaming").
Todos os dados são armazenados em banco de dados SQLite.
"""

import json
import logging
import os
from enum import Enum

from PySide6.QtCore import QObject, Signal

from app.core.database import Database, MigrationRunner

logger = logging.getLogger(__name__)


class ActionType(str, Enum):
    """Tipos de ação disponíveis para botões e potenciômetros."""

    # ---- OBS ----
    OBS_SWITCH_SCENE = "obs_switch_scene"
    OBS_TOGGLE_SOURCE = "obs_toggle_source"
    OBS_TOGGLE_MUTE = "obs_toggle_mute"
    OBS_START_STREAMING = "obs_start_streaming"
    OBS_STOP_STREAMING = "obs_stop_streaming"
    OBS_TOGGLE_STREAMING = "obs_toggle_streaming"
    OBS_START_RECORDING = "obs_start_recording"
    OBS_STOP_RECORDING = "obs_stop_recording"
    OBS_TOGGLE_RECORDING = "obs_toggle_recording"
    OBS_TOGGLE_VIRTUAL_CAM = "obs_toggle_virtual_cam"
    OBS_SOURCE_VOLUME = "obs_source_volume"

    # ---- Sistema ----
    SYS_VOLUME_UP = "sys_volume_up"
    SYS_VOLUME_DOWN = "sys_volume_down"
    SYS_VOLUME_MUTE = "sys_volume_mute"
    SYS_VOLUME_SET = "sys_volume_set"
    SYS_MEDIA_PLAY_PAUSE = "sys_media_play_pause"
    SYS_MEDIA_NEXT = "sys_media_next"
    SYS_MEDIA_PREV = "sys_media_prev"
    SYS_MEDIA_STOP = "sys_media_stop"
    SYS_HOTKEY = "sys_hotkey"
    SYS_OPEN_APP = "sys_open_app"
    SYS_RUN_COMMAND = "sys_run_command"

    # ---- Aplicação ----
    APP_SWITCH_LAYOUT = "app_switch_layout"

    # ---- Nenhuma ação ----
    NONE = "none"


# Metadados das ações para a GUI
ACTION_METADATA = {
    ActionType.NONE: {
        "label": "Nenhuma ação",
        "category": "Geral",
        "params": [],
        "for_pot": False,
    },
    # OBS
    ActionType.OBS_SWITCH_SCENE: {
        "label": "OBS: Trocar Cena",
        "category": "OBS",
        "params": [{"name": "scene_name", "label": "Nome da Cena", "type": "text"}],
        "for_pot": False,
    },
    ActionType.OBS_TOGGLE_SOURCE: {
        "label": "OBS: Alternar Fonte",
        "category": "OBS",
        "params": [
            {"name": "scene_name", "label": "Nome da Cena", "type": "text"},
            {"name": "source_name", "label": "Nome da Fonte", "type": "text"},
        ],
        "for_pot": False,
    },
    ActionType.OBS_TOGGLE_MUTE: {
        "label": "OBS: Alternar Mudo",
        "category": "OBS",
        "params": [{"name": "source_name", "label": "Nome da Fonte de Áudio", "type": "text"}],
        "for_pot": False,
    },
    ActionType.OBS_START_STREAMING: {
        "label": "OBS: Iniciar Transmissão",
        "category": "OBS",
        "params": [],
        "for_pot": False,
    },
    ActionType.OBS_STOP_STREAMING: {
        "label": "OBS: Parar Transmissão",
        "category": "OBS",
        "params": [],
        "for_pot": False,
    },
    ActionType.OBS_TOGGLE_STREAMING: {
        "label": "OBS: Alternar Transmissão",
        "category": "OBS",
        "params": [],
        "for_pot": False,
    },
    ActionType.OBS_START_RECORDING: {
        "label": "OBS: Iniciar Gravação",
        "category": "OBS",
        "params": [],
        "for_pot": False,
    },
    ActionType.OBS_STOP_RECORDING: {
        "label": "OBS: Parar Gravação",
        "category": "OBS",
        "params": [],
        "for_pot": False,
    },
    ActionType.OBS_TOGGLE_RECORDING: {
        "label": "OBS: Alternar Gravação",
        "category": "OBS",
        "params": [],
        "for_pot": False,
    },
    ActionType.OBS_TOGGLE_VIRTUAL_CAM: {
        "label": "OBS: Alternar Câmera Virtual",
        "category": "OBS",
        "params": [],
        "for_pot": False,
    },
    ActionType.OBS_SOURCE_VOLUME: {
        "label": "OBS: Volume da Fonte",
        "category": "OBS",
        "params": [{"name": "source_name", "label": "Nome da Fonte de Áudio", "type": "text"}],
        "for_pot": True,
    },
    # Sistema
    ActionType.SYS_VOLUME_UP: {
        "label": "Sistema: Volume +",
        "category": "Sistema",
        "params": [],
        "for_pot": False,
    },
    ActionType.SYS_VOLUME_DOWN: {
        "label": "Sistema: Volume -",
        "category": "Sistema",
        "params": [],
        "for_pot": False,
    },
    ActionType.SYS_VOLUME_MUTE: {
        "label": "Sistema: Mudo",
        "category": "Sistema",
        "params": [],
        "for_pot": False,
    },
    ActionType.SYS_VOLUME_SET: {
        "label": "Sistema: Definir Volume",
        "category": "Sistema",
        "params": [],
        "for_pot": True,
    },
    ActionType.SYS_MEDIA_PLAY_PAUSE: {
        "label": "Sistema: Play/Pause",
        "category": "Sistema",
        "params": [],
        "for_pot": False,
    },
    ActionType.SYS_MEDIA_NEXT: {
        "label": "Sistema: Próxima Faixa",
        "category": "Sistema",
        "params": [],
        "for_pot": False,
    },
    ActionType.SYS_MEDIA_PREV: {
        "label": "Sistema: Faixa Anterior",
        "category": "Sistema",
        "params": [],
        "for_pot": False,
    },
    ActionType.SYS_MEDIA_STOP: {
        "label": "Sistema: Parar Mídia",
        "category": "Sistema",
        "params": [],
        "for_pot": False,
    },
    ActionType.SYS_HOTKEY: {
        "label": "Sistema: Atalho de Teclado",
        "category": "Sistema",
        "params": [{"name": "keys", "label": "Teclas (ex: ctrl+shift+a)", "type": "text"}],
        "for_pot": False,
    },
    ActionType.SYS_OPEN_APP: {
        "label": "Sistema: Abrir Programa",
        "category": "Sistema",
        "params": [{"name": "path", "label": "Caminho do Programa", "type": "file"}],
        "for_pot": False,
    },
    ActionType.SYS_RUN_COMMAND: {
        "label": "Sistema: Executar Comando",
        "category": "Sistema",
        "params": [{"name": "command", "label": "Comando", "type": "text"}],
        "for_pot": False,
    },
    # Aplicação
    ActionType.APP_SWITCH_LAYOUT: {
        "label": "App: Trocar Layout",
        "category": "Aplicação",
        "params": [{"name": "layout_name", "label": "Nome do Layout", "type": "text"}],
        "for_pot": False,
    },
}


class ProfileManager(QObject):
    """Gerencia layouts e configurações da aplicação via SQLite."""

    layout_changed = Signal(str)          # Nome do layout ativo
    layouts_updated = Signal()            # Lista de layouts foi modificada
    config_changed = Signal()             # Qualquer config mudou

    def __init__(self, config_dir: str = None, parent=None):
        super().__init__(parent)

        if config_dir is None:
            config_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "config",
            )

        os.makedirs(config_dir, exist_ok=True)
        db_path = os.path.join(config_dir, "streamdeck.db")

        self._db = Database(db_path)

        # Rodar migrations pendentes
        runner = MigrationRunner(self._db)
        runner.run_pending()

        logger.info("Configuração carregada de %s", db_path)

    # ── Layouts ──────────────────────────────────────────────

    def get_layout_names(self) -> list[str]:
        """Retorna nomes de todos os layouts."""
        rows = self._db.fetchall("SELECT name FROM layouts ORDER BY id")
        return [row["name"] for row in rows]

    def get_active_layout_name(self) -> str:
        """Retorna o nome do layout ativo."""
        row = self._db.fetchone("SELECT name FROM layouts WHERE is_active = 1")
        if row:
            return row["name"]
        # Fallback: primeiro layout
        row = self._db.fetchone("SELECT name FROM layouts ORDER BY id LIMIT 1")
        return row["name"] if row else ""

    def get_active_layout(self) -> dict:
        """Retorna os dados do layout ativo no formato esperado pela GUI."""
        name = self.get_active_layout_name()
        return self._get_layout_data(name)

    def _get_layout_data(self, name: str) -> dict:
        """Monta dict do layout a partir do banco."""
        row = self._db.fetchone("SELECT id FROM layouts WHERE name = ?", (name,))
        if not row:
            return self._empty_layout_dict()

        layout_id = row["id"]

        # Botões
        buttons = {}
        for btn in self._db.fetchall(
            "SELECT row, col, action, params, label FROM button_actions WHERE layout_id = ?",
            (layout_id,),
        ):
            key = f"{btn['row']},{btn['col']}"
            buttons[key] = {
                "action": btn["action"],
                "params": json.loads(btn["params"]),
                "label": btn["label"],
            }

        # Preenche botões faltantes
        for r in range(3):
            for c in range(5):
                key = f"{r},{c}"
                if key not in buttons:
                    buttons[key] = {
                        "action": ActionType.NONE.value,
                        "params": {},
                        "label": "",
                    }

        # Potenciômetros
        pots = {}
        for pot in self._db.fetchall(
            "SELECT pot_index, action, params, label FROM pot_actions WHERE layout_id = ?",
            (layout_id,),
        ):
            pots[str(pot["pot_index"])] = {
                "action": pot["action"],
                "params": json.loads(pot["params"]),
                "label": pot["label"],
            }

        for i in range(3):
            if str(i) not in pots:
                pots[str(i)] = {
                    "action": ActionType.NONE.value,
                    "params": {},
                    "label": "",
                }

        return {"buttons": buttons, "pots": pots}

    @staticmethod
    def _empty_layout_dict() -> dict:
        """Cria um dict de layout vazio (para compatibilidade)."""
        buttons = {}
        for row in range(3):
            for col in range(5):
                buttons[f"{row},{col}"] = {
                    "action": ActionType.NONE.value,
                    "params": {},
                    "label": "",
                }
        pots = {}
        for i in range(3):
            pots[str(i)] = {
                "action": ActionType.NONE.value,
                "params": {},
                "label": "",
            }
        return {"buttons": buttons, "pots": pots}

    def switch_layout(self, name: str) -> bool:
        """Troca para o layout especificado."""
        row = self._db.fetchone("SELECT id FROM layouts WHERE name = ?", (name,))
        if not row:
            logger.warning("Layout '%s' não encontrado.", name)
            return False

        self._db.execute("UPDATE layouts SET is_active = 0")
        self._db.execute(
            "UPDATE layouts SET is_active = 1 WHERE name = ?", (name,)
        )
        self._db.commit()
        self.layout_changed.emit(name)
        logger.info("Layout trocado para '%s'.", name)
        return True

    def create_layout(self, name: str) -> bool:
        """Cria um novo layout vazio."""
        existing = self._db.fetchone(
            "SELECT id FROM layouts WHERE name = ?", (name,)
        )
        if existing:
            logger.warning("Layout '%s' já existe.", name)
            return False

        self._db.execute(
            "INSERT INTO layouts (name, is_active) VALUES (?, 0)", (name,)
        )
        layout_id = self._db.fetchone(
            "SELECT id FROM layouts WHERE name = ?", (name,)
        )["id"]

        # Criar botões vazios (3×5)
        for row in range(3):
            for col in range(5):
                self._db.execute(
                    """INSERT INTO button_actions
                       (layout_id, row, col, action, params, label)
                       VALUES (?, ?, ?, 'none', '{}', '')""",
                    (layout_id, row, col),
                )

        # Criar pots vazios (3)
        for i in range(3):
            self._db.execute(
                """INSERT INTO pot_actions
                   (layout_id, pot_index, action, params, label)
                   VALUES (?, ?, 'none', '{}', '')""",
                (layout_id, i),
            )

        self._db.commit()
        self.layouts_updated.emit()
        logger.info("Layout '%s' criado.", name)
        return True

    def duplicate_layout(self, source_name: str, new_name: str) -> bool:
        """Duplica um layout existente."""
        source = self._db.fetchone(
            "SELECT id FROM layouts WHERE name = ?", (source_name,)
        )
        if not source:
            return False

        existing = self._db.fetchone(
            "SELECT id FROM layouts WHERE name = ?", (new_name,)
        )
        if existing:
            return False

        source_id = source["id"]

        # Criar novo layout
        self._db.execute(
            "INSERT INTO layouts (name, is_active) VALUES (?, 0)", (new_name,)
        )
        new_id = self._db.fetchone(
            "SELECT id FROM layouts WHERE name = ?", (new_name,)
        )["id"]

        # Copiar botões
        self._db.execute(
            """INSERT INTO button_actions (layout_id, row, col, action, params, label)
               SELECT ?, row, col, action, params, label
               FROM button_actions WHERE layout_id = ?""",
            (new_id, source_id),
        )

        # Copiar pots
        self._db.execute(
            """INSERT INTO pot_actions (layout_id, pot_index, action, params, label)
               SELECT ?, pot_index, action, params, label
               FROM pot_actions WHERE layout_id = ?""",
            (new_id, source_id),
        )

        self._db.commit()
        self.layouts_updated.emit()
        logger.info("Layout '%s' duplicado como '%s'.", source_name, new_name)
        return True

    def rename_layout(self, old_name: str, new_name: str) -> bool:
        """Renomeia um layout."""
        old = self._db.fetchone(
            "SELECT id FROM layouts WHERE name = ?", (old_name,)
        )
        if not old:
            return False

        existing = self._db.fetchone(
            "SELECT id FROM layouts WHERE name = ?", (new_name,)
        )
        if existing:
            return False

        self._db.execute(
            "UPDATE layouts SET name = ? WHERE name = ?", (new_name, old_name)
        )
        self._db.commit()
        self.layouts_updated.emit()
        return True

    def delete_layout(self, name: str) -> bool:
        """Deleta um layout (não permite deletar o último)."""
        count = self._db.fetchone("SELECT COUNT(*) as cnt FROM layouts")["cnt"]
        if count <= 1:
            return False

        row = self._db.fetchone(
            "SELECT id, is_active FROM layouts WHERE name = ?", (name,)
        )
        if not row:
            return False

        was_active = row["is_active"]

        # CASCADE deleta button_actions e pot_actions
        self._db.execute("DELETE FROM layouts WHERE name = ?", (name,))

        # Se deletou o ativo, ativa o primeiro disponível
        if was_active:
            first = self._db.fetchone("SELECT name FROM layouts ORDER BY id LIMIT 1")
            if first:
                self._db.execute(
                    "UPDATE layouts SET is_active = 1 WHERE name = ?",
                    (first["name"],),
                )
                self._db.commit()
                self.layout_changed.emit(first["name"])
            else:
                self._db.commit()
        else:
            self._db.commit()

        self.layouts_updated.emit()
        logger.info("Layout '%s' deletado.", name)
        return True

    # ── Mapeamento de Botões e Potenciômetros ────────────────

    def get_button_action(self, row: int, col: int) -> dict:
        """Retorna a ação configurada para um botão no layout ativo."""
        layout_name = self.get_active_layout_name()
        layout = self._db.fetchone(
            "SELECT id FROM layouts WHERE name = ?", (layout_name,)
        )
        if not layout:
            return {"action": ActionType.NONE.value, "params": {}, "label": ""}

        btn = self._db.fetchone(
            """SELECT action, params, label FROM button_actions
               WHERE layout_id = ? AND row = ? AND col = ?""",
            (layout["id"], row, col),
        )
        if not btn:
            return {"action": ActionType.NONE.value, "params": {}, "label": ""}

        return {
            "action": btn["action"],
            "params": json.loads(btn["params"]),
            "label": btn["label"],
        }

    def set_button_action(self, row: int, col: int, action: str, params: dict, label: str):
        """Define a ação de um botão no layout ativo."""
        layout_name = self.get_active_layout_name()
        layout = self._db.fetchone(
            "SELECT id FROM layouts WHERE name = ?", (layout_name,)
        )
        if not layout:
            return

        params_json = json.dumps(params)
        self._db.execute(
            """INSERT INTO button_actions (layout_id, row, col, action, params, label)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(layout_id, row, col)
               DO UPDATE SET action=?, params=?, label=?""",
            (layout["id"], row, col, action, params_json, label,
             action, params_json, label),
        )
        self._db.commit()
        self.config_changed.emit()

    def get_pot_action(self, index: int) -> dict:
        """Retorna a ação configurada para um potenciômetro."""
        layout_name = self.get_active_layout_name()
        layout = self._db.fetchone(
            "SELECT id FROM layouts WHERE name = ?", (layout_name,)
        )
        if not layout:
            return {"action": ActionType.NONE.value, "params": {}, "label": ""}

        pot = self._db.fetchone(
            """SELECT action, params, label FROM pot_actions
               WHERE layout_id = ? AND pot_index = ?""",
            (layout["id"], index),
        )
        if not pot:
            return {"action": ActionType.NONE.value, "params": {}, "label": ""}

        return {
            "action": pot["action"],
            "params": json.loads(pot["params"]),
            "label": pot["label"],
        }

    def set_pot_action(self, index: int, action: str, params: dict, label: str):
        """Define a ação de um potenciômetro no layout ativo."""
        layout_name = self.get_active_layout_name()
        layout = self._db.fetchone(
            "SELECT id FROM layouts WHERE name = ?", (layout_name,)
        )
        if not layout:
            return

        params_json = json.dumps(params)
        self._db.execute(
            """INSERT INTO pot_actions (layout_id, pot_index, action, params, label)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(layout_id, pot_index)
               DO UPDATE SET action=?, params=?, label=?""",
            (layout["id"], index, action, params_json, label,
             action, params_json, label),
        )
        self._db.commit()
        self.config_changed.emit()

    # ── Configurações de Conexão ─────────────────────────────

    def _get_setting(self, key: str, default: str = "") -> str:
        """Retorna um valor de configuração."""
        row = self._db.fetchone(
            "SELECT value FROM settings WHERE key = ?", (key,)
        )
        return row["value"] if row else default

    def _set_setting(self, key: str, value: str):
        """Define um valor de configuração."""
        self._db.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )
        self._db.commit()

    def get_serial_config(self) -> dict:
        """Retorna configurações da porta serial."""
        return {
            "port": self._get_setting("serial_port", ""),
            "baudrate": int(self._get_setting("serial_baudrate", "115200")),
        }

    def set_serial_config(self, port: str, baudrate: int = 115200):
        """Salva configurações da porta serial."""
        self._set_setting("serial_port", port)
        self._set_setting("serial_baudrate", str(baudrate))

    def get_obs_config(self) -> dict:
        """Retorna configurações do OBS WebSocket."""
        return {
            "host": self._get_setting("obs_host", "localhost"),
            "port": int(self._get_setting("obs_port", "4455")),
            "password": self._get_setting("obs_password", ""),
        }

    def set_obs_config(self, host: str, port: int, password: str):
        """Salva configurações do OBS WebSocket."""
        self._set_setting("obs_host", host)
        self._set_setting("obs_port", str(port))
        self._set_setting("obs_password", password)

    def get_system_config(self) -> dict:
        """Retorna configurações do sistema (ex: autostart)."""
        return {
            "autostart": self._get_setting("sys_autostart", "false").lower() == "true",
        }

    def set_system_config(self, autostart: bool):
        """Salva configurações do sistema."""
        self._set_setting("sys_autostart", "true" if autostart else "false")

