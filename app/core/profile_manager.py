"""
ProfileManager — Gerencia layouts/perfis de mapeamento.

Cada layout define o que cada botão e potenciômetro faz.
Suporta múltiplos layouts (ex: "OBS Streaming", "Windows", "Gaming").
Todos os dados são salvos em um arquivo JSON de configuração.
"""

import json
import logging
import os
import copy
from pathlib import Path
from enum import Enum

from PySide6.QtCore import QObject, Signal

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


def _empty_layout() -> dict:
    """Cria um layout vazio (sem ações configuradas)."""
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


def _default_config() -> dict:
    """Configuração padrão com um layout vazio."""
    return {
        "layouts": {
            "Layout 1": _empty_layout(),
        },
        "active_layout": "Layout 1",
        "serial": {
            "port": "",
            "baudrate": 115200,
        },
        "obs": {
            "host": "localhost",
            "port": 4455,
            "password": "",
        },
    }


class ProfileManager(QObject):
    """Gerencia layouts e configurações da aplicação."""

    layout_changed = Signal(str)          # Nome do layout ativo
    layouts_updated = Signal()            # Lista de layouts foi modificada
    config_changed = Signal()             # Qualquer config mudou

    def __init__(self, config_dir: str = None, parent=None):
        super().__init__(parent)

        if config_dir is None:
            # Usa diretório local ao lado do app
            config_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "config"
            )

        self._config_dir = config_dir
        self._config_path = os.path.join(config_dir, "config.json")
        self._config = {}

        self._ensure_config_dir()
        self._load()

    def _ensure_config_dir(self):
        """Cria o diretório de configuração se não existir."""
        os.makedirs(self._config_dir, exist_ok=True)

    def _load(self):
        """Carrega a configuração do disco."""
        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    self._config = json.load(f)
                logger.info("Configuração carregada de %s", self._config_path)
            except (json.JSONDecodeError, IOError) as e:
                logger.error("Erro ao carregar config: %s. Usando padrão.", e)
                self._config = _default_config()
        else:
            self._config = _default_config()
            self._save()
            logger.info("Configuração padrão criada em %s", self._config_path)

    def _save(self):
        """Salva a configuração no disco."""
        try:
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            logger.debug("Configuração salva.")
        except IOError as e:
            logger.error("Erro ao salvar config: %s", e)

    # ---- Layouts ----

    def get_layout_names(self) -> list[str]:
        """Retorna nomes de todos os layouts."""
        return list(self._config.get("layouts", {}).keys())

    def get_active_layout_name(self) -> str:
        """Retorna o nome do layout ativo."""
        return self._config.get("active_layout", "")

    def get_active_layout(self) -> dict:
        """Retorna os dados do layout ativo."""
        name = self.get_active_layout_name()
        return self._config.get("layouts", {}).get(name, _empty_layout())

    def switch_layout(self, name: str) -> bool:
        """Troca para o layout especificado."""
        if name not in self._config.get("layouts", {}):
            logger.warning("Layout '%s' não encontrado.", name)
            return False

        self._config["active_layout"] = name
        self._save()
        self.layout_changed.emit(name)
        logger.info("Layout trocado para '%s'.", name)
        return True

    def create_layout(self, name: str) -> bool:
        """Cria um novo layout vazio."""
        if name in self._config.get("layouts", {}):
            logger.warning("Layout '%s' já existe.", name)
            return False

        self._config.setdefault("layouts", {})[name] = _empty_layout()
        self._save()
        self.layouts_updated.emit()
        logger.info("Layout '%s' criado.", name)
        return True

    def duplicate_layout(self, source_name: str, new_name: str) -> bool:
        """Duplica um layout existente."""
        layouts = self._config.get("layouts", {})
        if source_name not in layouts:
            return False
        if new_name in layouts:
            return False

        layouts[new_name] = copy.deepcopy(layouts[source_name])
        self._save()
        self.layouts_updated.emit()
        logger.info("Layout '%s' duplicado como '%s'.", source_name, new_name)
        return True

    def rename_layout(self, old_name: str, new_name: str) -> bool:
        """Renomeia um layout."""
        layouts = self._config.get("layouts", {})
        if old_name not in layouts or new_name in layouts:
            return False

        layouts[new_name] = layouts.pop(old_name)
        if self._config.get("active_layout") == old_name:
            self._config["active_layout"] = new_name
        self._save()
        self.layouts_updated.emit()
        return True

    def delete_layout(self, name: str) -> bool:
        """Deleta um layout (não permite deletar o último)."""
        layouts = self._config.get("layouts", {})
        if name not in layouts or len(layouts) <= 1:
            return False

        del layouts[name]
        # Se deletou o ativo, troca para o primeiro disponível
        if self._config.get("active_layout") == name:
            self._config["active_layout"] = next(iter(layouts))
            self.layout_changed.emit(self._config["active_layout"])

        self._save()
        self.layouts_updated.emit()
        logger.info("Layout '%s' deletado.", name)
        return True

    # ---- Mapeamento de Botões e Potenciômetros ----

    def get_button_action(self, row: int, col: int) -> dict:
        """Retorna a ação configurada para um botão no layout ativo."""
        layout = self.get_active_layout()
        key = f"{row},{col}"
        return layout.get("buttons", {}).get(key, {
            "action": ActionType.NONE.value,
            "params": {},
            "label": "",
        })

    def set_button_action(self, row: int, col: int, action: str, params: dict, label: str):
        """Define a ação de um botão no layout ativo."""
        name = self.get_active_layout_name()
        key = f"{row},{col}"
        self._config["layouts"][name]["buttons"][key] = {
            "action": action,
            "params": params,
            "label": label,
        }
        self._save()
        self.config_changed.emit()

    def get_pot_action(self, index: int) -> dict:
        """Retorna a ação configurada para um potenciômetro."""
        layout = self.get_active_layout()
        return layout.get("pots", {}).get(str(index), {
            "action": ActionType.NONE.value,
            "params": {},
            "label": "",
        })

    def set_pot_action(self, index: int, action: str, params: dict, label: str):
        """Define a ação de um potenciômetro no layout ativo."""
        name = self.get_active_layout_name()
        self._config["layouts"][name]["pots"][str(index)] = {
            "action": action,
            "params": params,
            "label": label,
        }
        self._save()
        self.config_changed.emit()

    # ---- Configurações de Conexão ----

    def get_serial_config(self) -> dict:
        """Retorna configurações da porta serial."""
        return self._config.get("serial", {"port": "", "baudrate": 115200})

    def set_serial_config(self, port: str, baudrate: int = 115200):
        """Salva configurações da porta serial."""
        self._config["serial"] = {"port": port, "baudrate": baudrate}
        self._save()

    def get_obs_config(self) -> dict:
        """Retorna configurações do OBS WebSocket."""
        return self._config.get("obs", {"host": "localhost", "port": 4455, "password": ""})

    def set_obs_config(self, host: str, port: int, password: str):
        """Salva configurações do OBS WebSocket."""
        self._config["obs"] = {"host": host, "port": port, "password": password}
        self._save()
