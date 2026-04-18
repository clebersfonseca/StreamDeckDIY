"""
TrayIcon — Ícone na bandeja do sistema (System Tray).

Permite acesso rápido às funcionalidades do StreamDeck:
- Mostrar/esconder janela
- Trocar layout
- Conectar/desconectar
- Sair
"""

from PySide6.QtCore import Signal
from PySide6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor, QFont
from PySide6.QtWidgets import QSystemTrayIcon, QMenu

from app.gui.styles import COLORS


def _create_default_icon() -> QIcon:
    from pathlib import Path
    icon_path = Path(__file__).parent / "assets" / "icon.svg"
    return QIcon(str(icon_path))


class TrayIcon(QSystemTrayIcon):
    """System tray icon com menu de contexto."""

    show_requested = Signal()
    quit_requested = Signal()
    connect_serial_requested = Signal()
    disconnect_serial_requested = Signal()
    connect_obs_requested = Signal()
    disconnect_obs_requested = Signal()
    layout_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIcon(_create_default_icon())
        self.setToolTip("StreamDeck DIY")

        self._menu = QMenu()
        self._layout_menu = None
        self._serial_action = None
        self._obs_action = None

        self._setup_menu()
        self.setContextMenu(self._menu)

        # Duplo-clique mostra a janela
        self.activated.connect(self._on_activated)

    def _setup_menu(self):
        """Cria o menu do tray."""
        # Mostrar janela
        show_action = QAction("Abrir StreamDeck", self)
        show_action.triggered.connect(self.show_requested.emit)
        self._menu.addAction(show_action)

        self._menu.addSeparator()

        # Submenu de layouts
        self._layout_menu = self._menu.addMenu("Layouts")

        self._menu.addSeparator()

        # Conexões
        self._serial_action = QAction("Conectar Serial", self)
        self._serial_action.triggered.connect(self.connect_serial_requested.emit)
        self._menu.addAction(self._serial_action)

        self._obs_action = QAction("Conectar OBS", self)
        self._obs_action.triggered.connect(self.connect_obs_requested.emit)
        self._menu.addAction(self._obs_action)

        self._menu.addSeparator()

        # Sair
        quit_action = QAction("Sair", self)
        quit_action.triggered.connect(self.quit_requested.emit)
        self._menu.addAction(quit_action)

    def update_layouts(self, layouts: list[str], active: str):
        """Atualiza o submenu de layouts."""
        self._layout_menu.clear()
        for name in layouts:
            action = QAction(name, self)
            action.setCheckable(True)
            action.setChecked(name == active)
            action.triggered.connect(
                lambda checked, n=name: self.layout_selected.emit(n)
            )
            self._layout_menu.addAction(action)

    def update_serial_status(self, connected: bool):
        """Atualiza o texto da ação serial."""
        if connected:
            self._serial_action.setText("Desconectar Serial")
            try:
                self._serial_action.triggered.disconnect()
            except RuntimeError:
                pass
            self._serial_action.triggered.connect(self.disconnect_serial_requested.emit)
        else:
            self._serial_action.setText("Conectar Serial")
            try:
                self._serial_action.triggered.disconnect()
            except RuntimeError:
                pass
            self._serial_action.triggered.connect(self.connect_serial_requested.emit)

    def update_obs_status(self, connected: bool):
        """Atualiza o texto da ação OBS."""
        if connected:
            self._obs_action.setText("Desconectar OBS")
            try:
                self._obs_action.triggered.disconnect()
            except RuntimeError:
                pass
            self._obs_action.triggered.connect(self.disconnect_obs_requested.emit)
        else:
            self._obs_action.setText("Conectar OBS")
            try:
                self._obs_action.triggered.disconnect()
            except RuntimeError:
                pass
            self._obs_action.triggered.connect(self.connect_obs_requested.emit)

    def _on_activated(self, reason):
        """Trata ativação do ícone (duplo-clique)."""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_requested.emit()
