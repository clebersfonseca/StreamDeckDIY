"""
OBSController — Integração com OBS Studio via WebSocket v5.

Usa a biblioteca obsws-python para controlar o OBS:
troca de cenas, toggle de fontes, mudo, streaming, gravação, volume.
"""

import logging
from typing import Optional

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)

try:
    import obsws_python as obsws
    HAS_OBSWS = True
except ImportError:
    HAS_OBSWS = False
    logger.warning("obsws-python não instalado. Funcionalidades OBS desabilitadas.")


class OBSController(QObject):
    """Controlador para OBS Studio via WebSocket."""

    connection_changed = Signal(bool)    # True=conectado
    error_occurred = Signal(str)         # Mensagem de erro

    def __init__(self, parent=None):
        super().__init__(parent)
        self._client: Optional[object] = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self, host: str = "localhost", port: int = 4455, password: str = ""):
        """Conecta ao OBS WebSocket."""
        if not HAS_OBSWS:
            self.error_occurred.emit("Biblioteca obsws-python não instalada.")
            return False

        try:
            self._client = obsws.ReqClient(
                host=host,
                port=port,
                password=password if password else None,
                timeout=5,
            )
            self._connected = True
            self.connection_changed.emit(True)
            logger.info("Conectado ao OBS em %s:%d", host, port)
            return True
        except Exception as e:
            self._connected = False
            self.connection_changed.emit(False)
            self.error_occurred.emit(f"Erro ao conectar ao OBS: {e}")
            logger.error("Erro ao conectar ao OBS: %s", e)
            return False

    def disconnect(self):
        """Desconecta do OBS."""
        if self._client:
            try:
                self._client = None
            except Exception:
                pass
        self._connected = False
        self.connection_changed.emit(False)
        logger.info("Desconectado do OBS.")

    def _ensure_connected(self) -> bool:
        """Verifica se está conectado antes de executar ação."""
        if not self._connected or not self._client:
            logger.warning("OBS não conectado. Ação ignorada.")
            return False
        return True

    # ---- Cenas ----

    def switch_scene(self, scene_name: str):
        """Troca para a cena especificada."""
        if not self._ensure_connected():
            return
        try:
            self._client.set_current_program_scene(scene_name)
            logger.info("Cena trocada para '%s'.", scene_name)
        except Exception as e:
            self.error_occurred.emit(f"Erro ao trocar cena: {e}")
            logger.error("Erro ao trocar cena: %s", e)

    def get_scenes(self) -> list[str]:
        """Retorna lista de nomes das cenas disponíveis."""
        if not self._ensure_connected():
            return []
        try:
            resp = self._client.get_scene_list()
            return [s["sceneName"] for s in resp.scenes]
        except Exception as e:
            logger.error("Erro ao obter cenas: %s", e)
            return []

    # ---- Fontes ----

    def toggle_source(self, scene_name: str, source_name: str):
        """Alterna a visibilidade de uma fonte na cena."""
        if not self._ensure_connected():
            return
        try:
            item_id = self._client.get_scene_item_id(
                scene_name, source_name
            ).scene_item_id
            current = self._client.get_scene_item_enabled(
                scene_name, item_id
            ).scene_item_enabled
            self._client.set_scene_item_enabled(
                scene_name, item_id, not current
            )
            logger.info("Fonte '%s' em '%s' %s.",
                        source_name, scene_name,
                        "desabilitada" if current else "habilitada")
        except Exception as e:
            self.error_occurred.emit(f"Erro ao alternar fonte: {e}")
            logger.error("Erro ao alternar fonte: %s", e)

    # ---- Áudio ----

    def toggle_mute(self, source_name: str):
        """Alterna mudo de uma fonte de áudio."""
        if not self._ensure_connected():
            return
        try:
            self._client.toggle_input_mute(source_name)
            logger.info("Mudo alternado para '%s'.", source_name)
        except Exception as e:
            self.error_occurred.emit(f"Erro ao alternar mudo: {e}")
            logger.error("Erro ao alternar mudo: %s", e)

    def set_source_volume(self, source_name: str, volume_db: float):
        """Define o volume de uma fonte de áudio (em dB)."""
        if not self._ensure_connected():
            return
        try:
            self._client.set_input_volume(source_name, vol_db=volume_db)
            logger.debug("Volume de '%s' definido para %.1f dB.", source_name, volume_db)
        except Exception as e:
            self.error_occurred.emit(f"Erro ao definir volume: {e}")
            logger.error("Erro ao definir volume: %s", e)

    def set_source_volume_normalized(self, source_name: str, value: float):
        """Define o volume de uma fonte (0.0 a 1.0, normalizado)."""
        if not self._ensure_connected():
            return
        try:
            # OBS usa valor mul (multiplicador) de 0.0 a 1.0
            self._client.set_input_volume(
                source_name, vol_mul=max(0.0, min(1.0, value))
            )
            logger.debug("Volume de '%s' definido para %.1f%%.",
                          source_name, value * 100)
        except Exception as e:
            self.error_occurred.emit(f"Erro ao definir volume: {e}")
            logger.error("Erro ao definir volume: %s", e)

    # ---- Streaming ----

    def start_streaming(self):
        """Inicia a transmissão."""
        if not self._ensure_connected():
            return
        try:
            self._client.start_stream()
            logger.info("Transmissão iniciada.")
        except Exception as e:
            self.error_occurred.emit(f"Erro ao iniciar transmissão: {e}")

    def stop_streaming(self):
        """Para a transmissão."""
        if not self._ensure_connected():
            return
        try:
            self._client.stop_stream()
            logger.info("Transmissão parada.")
        except Exception as e:
            self.error_occurred.emit(f"Erro ao parar transmissão: {e}")

    def toggle_streaming(self):
        """Alterna transmissão (inicia/para)."""
        if not self._ensure_connected():
            return
        try:
            self._client.toggle_stream()
            logger.info("Transmissão alternada.")
        except Exception as e:
            self.error_occurred.emit(f"Erro ao alternar transmissão: {e}")

    # ---- Gravação ----

    def start_recording(self):
        """Inicia gravação."""
        if not self._ensure_connected():
            return
        try:
            self._client.start_record()
            logger.info("Gravação iniciada.")
        except Exception as e:
            self.error_occurred.emit(f"Erro ao iniciar gravação: {e}")

    def stop_recording(self):
        """Para gravação."""
        if not self._ensure_connected():
            return
        try:
            self._client.stop_record()
            logger.info("Gravação parada.")
        except Exception as e:
            self.error_occurred.emit(f"Erro ao parar gravação: {e}")

    def toggle_recording(self):
        """Alterna gravação (inicia/para)."""
        if not self._ensure_connected():
            return
        try:
            self._client.toggle_record()
            logger.info("Gravação alternada.")
        except Exception as e:
            self.error_occurred.emit(f"Erro ao alternar gravação: {e}")

    # ---- Câmera Virtual ----

    def toggle_virtual_cam(self):
        """Alterna câmera virtual."""
        if not self._ensure_connected():
            return
        try:
            self._client.toggle_virtual_cam()
            logger.info("Câmera virtual alternada.")
        except Exception as e:
            self.error_occurred.emit(f"Erro ao alternar câmera virtual: {e}")
