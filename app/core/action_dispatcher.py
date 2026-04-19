"""
ActionDispatcher — Roteador de eventos para ações configuradas.

Recebe eventos do SerialWorker (botões e potenciômetros),
consulta o ProfileManager para saber a ação mapeada,
e despacha para o controller correto (OBS ou Sistema).
"""

import logging

from PySide6.QtCore import QObject, Signal, Slot

from app.core.profile_manager import ActionType, ProfileManager
from app.core.obs_controller import OBSController
from app.core.system_controller import SystemController

logger = logging.getLogger(__name__)


class ActionDispatcher(QObject):
    """Despacha eventos do Arduino para as ações configuradas."""

    # Sinal especial para troca de layout (tratado pela MainWindow)
    layout_switch_requested = Signal(str)   # nome do layout
    action_executed = Signal(str)           # descrição da ação executada

    def __init__(
        self,
        profile_manager: ProfileManager,
        obs_controller: OBSController,
        system_controller: SystemController,
        parent=None,
    ):
        super().__init__(parent)
        self._profiles = profile_manager
        self._obs = obs_controller
        self._sys = system_controller

    @Slot(int, int, bool)
    def on_button_event(self, row: int, col: int, pressed: bool):
        """Trata evento de botão do Arduino. Executa ação apenas no PRESS."""
        if not pressed:
            return  # Ignora evento de soltar (por enquanto)

        action_config = self._profiles.get_button_action(row, col)
        action_type = action_config.get("action", ActionType.NONE.value)
        params = action_config.get("params", {})
        label = action_config.get("label", "")

        logger.debug("Botão [%d,%d] → ação: %s, params: %s", row, col, action_type, params)

        self._execute_button_action(action_type, params, label)

    @Slot(int, int)
    def on_pot_event(self, index: int, value: int):
        """Trata evento de potenciômetro do Arduino."""
        action_config = self._profiles.get_pot_action(index)
        action_type = action_config.get("action", ActionType.NONE.value)
        params = action_config.get("params", {})
        inverted = action_config.get("inverted", False)

        if action_type == ActionType.NONE.value:
            return

        # Converte valor do Arduino (0-1023) para 0.0-1.0
        normalized = value / 1023.0

        # Inverte se configurado (maior resistência = menor valor)
        if inverted:
            normalized = 1.0 - normalized

        logger.debug("Pot [%d] = %d (%.1f%%) → ação: %s%s",
                      index, value, normalized * 100, action_type,
                      " (invertido)" if inverted else "")

        self._execute_pot_action(action_type, params, normalized)

    def _execute_button_action(self, action_type: str, params: dict, label: str):
        """Executa a ação de um botão."""
        try:
            # ---- OBS ----
            if action_type == ActionType.OBS_SWITCH_SCENE.value:
                scene = params.get("scene_name", "")
                if scene:
                    self._obs.switch_scene(scene)
                    self.action_executed.emit(f"Cena: {scene}")

            elif action_type == ActionType.OBS_TOGGLE_SOURCE.value:
                scene = params.get("scene_name", "")
                source = params.get("source_name", "")
                if scene and source:
                    self._obs.toggle_source(scene, source)
                    self.action_executed.emit(f"Fonte: {source}")

            elif action_type == ActionType.OBS_TOGGLE_MUTE.value:
                source = params.get("source_name", "")
                if source:
                    self._obs.toggle_mute(source)
                    self.action_executed.emit(f"Mudo: {source}")

            elif action_type == ActionType.OBS_START_STREAMING.value:
                self._obs.start_streaming()
                self.action_executed.emit("Streaming iniciado")

            elif action_type == ActionType.OBS_STOP_STREAMING.value:
                self._obs.stop_streaming()
                self.action_executed.emit("Streaming parado")

            elif action_type == ActionType.OBS_TOGGLE_STREAMING.value:
                self._obs.toggle_streaming()
                self.action_executed.emit("Streaming alternado")

            elif action_type == ActionType.OBS_START_RECORDING.value:
                self._obs.start_recording()
                self.action_executed.emit("Gravação iniciada")

            elif action_type == ActionType.OBS_STOP_RECORDING.value:
                self._obs.stop_recording()
                self.action_executed.emit("Gravação parada")

            elif action_type == ActionType.OBS_TOGGLE_RECORDING.value:
                self._obs.toggle_recording()
                self.action_executed.emit("Gravação alternada")

            elif action_type == ActionType.OBS_TOGGLE_VIRTUAL_CAM.value:
                self._obs.toggle_virtual_cam()
                self.action_executed.emit("Câmera virtual alternada")

            # ---- Sistema ----
            elif action_type == ActionType.SYS_VOLUME_UP.value:
                self._sys.volume_up()
                self.action_executed.emit("Volume +")

            elif action_type == ActionType.SYS_VOLUME_DOWN.value:
                self._sys.volume_down()
                self.action_executed.emit("Volume -")

            elif action_type == ActionType.SYS_VOLUME_MUTE.value:
                self._sys.volume_mute()
                self.action_executed.emit("Mudo")

            elif action_type == ActionType.SYS_MEDIA_PLAY_PAUSE.value:
                self._sys.media_play_pause()
                self.action_executed.emit("Play/Pause")

            elif action_type == ActionType.SYS_MEDIA_NEXT.value:
                self._sys.media_next()
                self.action_executed.emit("Próxima faixa")

            elif action_type == ActionType.SYS_MEDIA_PREV.value:
                self._sys.media_prev()
                self.action_executed.emit("Faixa anterior")

            elif action_type == ActionType.SYS_MEDIA_STOP.value:
                self._sys.media_stop()
                self.action_executed.emit("Mídia parada")

            elif action_type == ActionType.SYS_HOTKEY.value:
                keys = params.get("keys", "")
                if keys:
                    self._sys.hotkey(keys)
                    self.action_executed.emit(f"Atalho: {keys}")

            elif action_type == ActionType.SYS_OPEN_APP.value:
                path = params.get("path", "")
                if path:
                    self._sys.open_app(path)
                    self.action_executed.emit(f"Abrir: {path}")

            elif action_type == ActionType.SYS_RUN_COMMAND.value:
                command = params.get("command", "")
                if command:
                    self._sys.run_command(command)
                    self.action_executed.emit(f"Comando: {command}")

            # ---- Aplicação ----
            elif action_type == ActionType.APP_SWITCH_LAYOUT.value:
                layout_name = params.get("layout_name", "")
                if layout_name:
                    self.layout_switch_requested.emit(layout_name)
                    self.action_executed.emit(f"Layout: {layout_name}")

            elif action_type == ActionType.NONE.value:
                pass  # Sem ação configurada

            else:
                logger.warning("Tipo de ação desconhecida: %s", action_type)

        except Exception as e:
            logger.error("Erro ao executar ação %s: %s", action_type, e)

    def _execute_pot_action(self, action_type: str, params: dict, normalized: float):
        """Executa a ação de um potenciômetro com valor normalizado (0.0-1.0)."""
        try:
            if action_type == ActionType.SYS_VOLUME_SET.value:
                self._sys.volume_set(normalized)

            elif action_type == ActionType.OBS_SOURCE_VOLUME.value:
                source = params.get("source_name", "")
                if source:
                    self._obs.set_source_volume_normalized(source, normalized)

            elif action_type == ActionType.NONE.value:
                pass

            else:
                logger.warning("Ação de pot não suportada: %s", action_type)

        except Exception as e:
            logger.error("Erro ao executar ação de pot %s: %s", action_type, e)
