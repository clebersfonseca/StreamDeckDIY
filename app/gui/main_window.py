"""
MainWindow — Janela principal da aplicação StreamDeck DIY.

3 abas:
  1. Dashboard: visualização em tempo real (grid + pots + status)
  2. Mapeamento: configuração de ações dos botões e pots
  3. Configurações: serial, OBS, gerenciamento de layouts
"""

import logging

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QPushButton, QGroupBox, QFormLayout,
    QLineEdit, QSpinBox, QStatusBar, QMessageBox, QInputDialog,
    QSizePolicy, QFrame,
)

from app.core.profile_manager import ProfileManager
from app.core.serial_worker import SerialManager, SerialWorker
from app.core.obs_controller import OBSController
from app.core.system_controller import SystemController
from app.core.action_dispatcher import ActionDispatcher
from app.gui.button_grid import ButtonGrid
from app.gui.pot_widget import PotWidget
from app.gui.action_dialog import ActionDialog
from app.gui.tray_icon import TrayIcon
from app.gui.styles import COLORS, STATUS_CONNECTED, STATUS_DISCONNECTED, STATUS_IDLE

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Janela principal do StreamDeck DIY."""

    def __init__(self):
        super().__init__()

        self.setWindowTitle("StreamDeck DIY")
        self.setMinimumSize(750, 580)
        self.resize(820, 640)

        # ---- Componentes Core ----
        self._profiles = ProfileManager()
        self._serial_mgr = SerialManager()
        self._obs = OBSController()
        self._sys_ctrl = SystemController()
        self._dispatcher = ActionDispatcher(
            self._profiles, self._obs, self._sys_ctrl
        )

        # ---- GUI ----
        self._setup_ui()
        self._setup_tray()
        self._connect_signals()
        self._load_config_to_ui()

        # Status bar
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)
        self._statusbar.showMessage("StreamDeck DIY pronto. Conecte o Arduino.")

    # ==========================================================
    # Setup
    # ==========================================================

    def _setup_ui(self):
        """Cria a interface principal."""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(12, 12, 12, 12)

        # ---- Barra de layout ----
        layout_bar = self._create_layout_bar()
        main_layout.addLayout(layout_bar)

        # ---- Abas ----
        self._tabs = QTabWidget()
        self._tabs.addTab(self._create_dashboard_tab(), "📊  Dashboard")
        self._tabs.addTab(self._create_mapping_tab(), "🎛  Mapeamento")
        self._tabs.addTab(self._create_settings_tab(), "⚙  Configurações")
        main_layout.addWidget(self._tabs)

    def _create_layout_bar(self) -> QHBoxLayout:
        """Barra superior com seletor de layout."""
        bar = QHBoxLayout()

        lbl = QLabel("Layout Ativo:")
        lbl.setStyleSheet(f"font-weight: 700; color: {COLORS['accent_light']};")
        bar.addWidget(lbl)

        self._layout_combo = QComboBox()
        self._layout_combo.setMinimumWidth(200)
        self._layout_combo.currentTextChanged.connect(self._on_layout_combo_changed)
        bar.addWidget(self._layout_combo)

        add_btn = QPushButton("+ Novo")
        add_btn.setFixedWidth(80)
        add_btn.clicked.connect(self._on_add_layout)
        bar.addWidget(add_btn)

        dup_btn = QPushButton("📋 Duplicar")
        dup_btn.setFixedWidth(100)
        dup_btn.clicked.connect(self._on_duplicate_layout)
        bar.addWidget(dup_btn)

        rename_btn = QPushButton("✏ Renomear")
        rename_btn.setFixedWidth(100)
        rename_btn.clicked.connect(self._on_rename_layout)
        bar.addWidget(rename_btn)

        del_btn = QPushButton("🗑 Excluir")
        del_btn.setFixedWidth(90)
        del_btn.setProperty("class", "danger")
        del_btn.clicked.connect(self._on_delete_layout)
        bar.addWidget(del_btn)

        bar.addStretch()

        return bar

    def _create_dashboard_tab(self) -> QWidget:
        """Aba Dashboard — visualização em tempo real."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        # Status de conexão
        status_group = QGroupBox("Status de Conexão")
        status_layout = QHBoxLayout(status_group)

        # Serial
        serial_frame = QVBoxLayout()
        serial_lbl = QLabel("Arduino Serial")
        serial_lbl.setStyleSheet(f"font-weight: 700; color: {COLORS['text']};")
        self._serial_status = QLabel("● Desconectado")
        self._serial_status.setStyleSheet(STATUS_DISCONNECTED)
        serial_frame.addWidget(serial_lbl)
        serial_frame.addWidget(self._serial_status)
        status_layout.addLayout(serial_frame)

        # Separador
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet(f"color: {COLORS['border']};")
        status_layout.addWidget(sep)

        # OBS
        obs_frame = QVBoxLayout()
        obs_lbl = QLabel("OBS WebSocket")
        obs_lbl.setStyleSheet(f"font-weight: 700; color: {COLORS['text']};")
        self._obs_status = QLabel("● Desconectado")
        self._obs_status.setStyleSheet(STATUS_DISCONNECTED)
        obs_frame.addWidget(obs_lbl)
        obs_frame.addWidget(self._obs_status)
        status_layout.addLayout(obs_frame)

        # Último evento
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.VLine)
        sep2.setStyleSheet(f"color: {COLORS['border']};")
        status_layout.addWidget(sep2)

        event_frame = QVBoxLayout()
        event_lbl = QLabel("Última Ação")
        event_lbl.setStyleSheet(f"font-weight: 700; color: {COLORS['text']};")
        self._last_action_label = QLabel("—")
        self._last_action_label.setStyleSheet(f"color: {COLORS['cyan']};")
        event_frame.addWidget(event_lbl)
        event_frame.addWidget(self._last_action_label)
        status_layout.addLayout(event_frame)

        layout.addWidget(status_group)

        # Grid de botões
        btn_group = QGroupBox("Botões (3×5)")
        btn_layout = QVBoxLayout(btn_group)
        self._dashboard_grid = ButtonGrid(self._profiles)
        self._dashboard_grid.button_config_requested.connect(self._on_button_config)
        btn_layout.addWidget(self._dashboard_grid)
        layout.addWidget(btn_group)

        # Potenciômetros
        pot_group = QGroupBox("Potenciômetros")
        pot_layout = QVBoxLayout(pot_group)
        self._dashboard_pots = PotWidget(self._profiles)
        self._dashboard_pots.pot_config_requested.connect(self._on_pot_config)
        pot_layout.addWidget(self._dashboard_pots)
        layout.addWidget(pot_group)

        return tab

    def _create_mapping_tab(self) -> QWidget:
        """Aba Mapeamento — configuração de ações."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        info = QLabel(
            "Clique em um botão ou no ⚙ de um potenciômetro para configurar sua ação."
        )
        info.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px; padding: 8px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        # Grid de botões (compartilha o mesmo ProfileManager)
        btn_group = QGroupBox("Configuração dos Botões")
        btn_layout = QVBoxLayout(btn_group)
        self._mapping_grid = ButtonGrid(self._profiles)
        self._mapping_grid.button_config_requested.connect(self._on_button_config)
        btn_layout.addWidget(self._mapping_grid)
        layout.addWidget(btn_group)

        # Potenciômetros
        pot_group = QGroupBox("Configuração dos Potenciômetros")
        pot_layout = QVBoxLayout(pot_group)
        self._mapping_pots = PotWidget(self._profiles)
        self._mapping_pots.pot_config_requested.connect(self._on_pot_config)
        pot_layout.addWidget(self._mapping_pots)
        layout.addWidget(pot_group)

        return tab

    def _create_settings_tab(self) -> QWidget:
        """Aba Configurações — serial, OBS, etc."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)

        # ---- Serial ----
        serial_group = QGroupBox("Conexão Serial (Arduino)")
        serial_layout = QFormLayout(serial_group)

        port_row = QHBoxLayout()
        self._port_combo = QComboBox()
        self._port_combo.setMinimumWidth(250)
        port_row.addWidget(self._port_combo)

        refresh_btn = QPushButton("🔄 Atualizar")
        refresh_btn.setFixedWidth(100)
        refresh_btn.clicked.connect(self._refresh_ports)
        port_row.addWidget(refresh_btn)
        serial_layout.addRow("Porta:", port_row)

        self._baud_spin = QSpinBox()
        self._baud_spin.setRange(9600, 2000000)
        self._baud_spin.setValue(115200)
        self._baud_spin.setSingleStep(9600)
        serial_layout.addRow("Baudrate:", self._baud_spin)

        serial_btn_row = QHBoxLayout()
        self._serial_connect_btn = QPushButton("Conectar")
        self._serial_connect_btn.setProperty("class", "success")
        self._serial_connect_btn.clicked.connect(self._on_serial_connect)
        serial_btn_row.addWidget(self._serial_connect_btn)

        self._serial_disconnect_btn = QPushButton("Desconectar")
        self._serial_disconnect_btn.setProperty("class", "danger")
        self._serial_disconnect_btn.setEnabled(False)
        self._serial_disconnect_btn.clicked.connect(self._on_serial_disconnect)
        serial_btn_row.addWidget(self._serial_disconnect_btn)

        serial_btn_row.addStretch()
        serial_layout.addRow("", serial_btn_row)

        layout.addWidget(serial_group)

        # ---- OBS ----
        obs_group = QGroupBox("OBS WebSocket")
        obs_layout = QFormLayout(obs_group)

        self._obs_host = QLineEdit("localhost")
        obs_layout.addRow("Host:", self._obs_host)

        self._obs_port = QSpinBox()
        self._obs_port.setRange(1, 65535)
        self._obs_port.setValue(4455)
        obs_layout.addRow("Porta:", self._obs_port)

        self._obs_password = QLineEdit()
        self._obs_password.setEchoMode(QLineEdit.Password)
        self._obs_password.setPlaceholderText("Deixe vazio se não tiver senha")
        obs_layout.addRow("Senha:", self._obs_password)

        obs_btn_row = QHBoxLayout()
        self._obs_connect_btn = QPushButton("Conectar")
        self._obs_connect_btn.setProperty("class", "success")
        self._obs_connect_btn.clicked.connect(self._on_obs_connect)
        obs_btn_row.addWidget(self._obs_connect_btn)

        self._obs_disconnect_btn = QPushButton("Desconectar")
        self._obs_disconnect_btn.setProperty("class", "danger")
        self._obs_disconnect_btn.setEnabled(False)
        self._obs_disconnect_btn.clicked.connect(self._on_obs_disconnect)
        obs_btn_row.addWidget(self._obs_disconnect_btn)

        obs_btn_row.addStretch()
        obs_layout.addRow("", obs_btn_row)

        layout.addWidget(obs_group)

        layout.addStretch()

        # Refresh ports ao abrir
        self._refresh_ports()

        return tab

    def _setup_tray(self):
        """Configura o system tray icon."""
        self._tray = TrayIcon(self)

        self._tray.show_requested.connect(self._show_from_tray)
        self._tray.quit_requested.connect(self._on_quit)
        self._tray.layout_selected.connect(self._on_tray_layout_selected)
        self._tray.connect_serial_requested.connect(self._on_serial_connect)
        self._tray.disconnect_serial_requested.connect(self._on_serial_disconnect)
        self._tray.connect_obs_requested.connect(self._on_obs_connect)
        self._tray.disconnect_obs_requested.connect(self._on_obs_disconnect)

        self._update_tray_layouts()
        self._tray.show()

    def _connect_signals(self):
        """Conecta todos os sinais entre componentes."""
        worker = self._serial_mgr.worker

        # Serial → Dispatcher
        worker.button_event.connect(self._dispatcher.on_button_event)
        worker.pot_event.connect(self._dispatcher.on_pot_event)

        # Serial → Dashboard (feedback visual)
        worker.button_event.connect(self._on_serial_button)
        worker.pot_event.connect(self._on_serial_pot)

        # Serial status
        worker.connection_changed.connect(self._on_serial_status_changed)
        worker.error_occurred.connect(self._on_serial_error)
        worker.arduino_ready.connect(
            lambda: self._statusbar.showMessage("Arduino conectado e pronto!", 5000)
        )

        # OBS status
        self._obs.connection_changed.connect(self._on_obs_status_changed)
        self._obs.error_occurred.connect(self._on_obs_error)

        # Dispatcher
        self._dispatcher.layout_switch_requested.connect(self._on_layout_switch_request)
        self._dispatcher.action_executed.connect(self._on_action_executed)

        # Profiles
        self._profiles.layouts_updated.connect(self._update_layout_combo)
        self._profiles.layouts_updated.connect(self._update_tray_layouts)

    def _load_config_to_ui(self):
        """Carrega configurações salvas na UI."""
        # Serial
        serial_cfg = self._profiles.get_serial_config()
        self._baud_spin.setValue(serial_cfg.get("baudrate", 115200))

        # OBS
        obs_cfg = self._profiles.get_obs_config()
        self._obs_host.setText(obs_cfg.get("host", "localhost"))
        self._obs_port.setValue(obs_cfg.get("port", 4455))
        self._obs_password.setText(obs_cfg.get("password", ""))

        # Layouts
        self._update_layout_combo()

    # ==========================================================
    # Layout Management
    # ==========================================================

    def _update_layout_combo(self):
        """Atualiza o combobox de layouts."""
        self._layout_combo.blockSignals(True)
        self._layout_combo.clear()
        names = self._profiles.get_layout_names()
        active = self._profiles.get_active_layout_name()
        for name in names:
            self._layout_combo.addItem(name)
        idx = self._layout_combo.findText(active)
        if idx >= 0:
            self._layout_combo.setCurrentIndex(idx)
        self._layout_combo.blockSignals(False)

    def _update_tray_layouts(self):
        """Atualiza o submenu de layouts no tray."""
        self._tray.update_layouts(
            self._profiles.get_layout_names(),
            self._profiles.get_active_layout_name(),
        )

    @Slot(str)
    def _on_layout_combo_changed(self, name: str):
        """Troca de layout pelo combobox."""
        if name:
            self._profiles.switch_layout(name)
            self._update_tray_layouts()
            self._statusbar.showMessage(f"Layout trocado para: {name}", 3000)

    @Slot(str)
    def _on_tray_layout_selected(self, name: str):
        """Troca de layout pelo tray menu."""
        self._profiles.switch_layout(name)
        self._update_layout_combo()
        self._update_tray_layouts()

    @Slot(str)
    def _on_layout_switch_request(self, name: str):
        """Troca de layout solicitada pelo dispatcher (botão do deck)."""
        if self._profiles.switch_layout(name):
            self._update_layout_combo()
            self._update_tray_layouts()
            self._statusbar.showMessage(f"Layout trocado para: {name}", 3000)

    def _on_add_layout(self):
        """Adiciona novo layout."""
        name, ok = QInputDialog.getText(
            self, "Novo Layout", "Nome do layout:"
        )
        if ok and name.strip():
            if self._profiles.create_layout(name.strip()):
                self._profiles.switch_layout(name.strip())
                self._update_layout_combo()
                self._update_tray_layouts()
            else:
                QMessageBox.warning(self, "Erro", f"Layout '{name}' já existe.")

    def _on_duplicate_layout(self):
        """Duplica o layout ativo."""
        current = self._profiles.get_active_layout_name()
        name, ok = QInputDialog.getText(
            self, "Duplicar Layout",
            f"Nome para a cópia de '{current}':",
            text=f"{current} (cópia)",
        )
        if ok and name.strip():
            if self._profiles.duplicate_layout(current, name.strip()):
                self._profiles.switch_layout(name.strip())
                self._update_layout_combo()
                self._update_tray_layouts()
            else:
                QMessageBox.warning(self, "Erro", f"Layout '{name}' já existe.")

    def _on_rename_layout(self):
        """Renomeia o layout ativo."""
        current = self._profiles.get_active_layout_name()
        name, ok = QInputDialog.getText(
            self, "Renomear Layout",
            f"Novo nome para '{current}':",
            text=current,
        )
        if ok and name.strip() and name.strip() != current:
            if self._profiles.rename_layout(current, name.strip()):
                self._update_layout_combo()
                self._update_tray_layouts()
            else:
                QMessageBox.warning(self, "Erro", "Não foi possível renomear.")

    def _on_delete_layout(self):
        """Deleta o layout ativo."""
        current = self._profiles.get_active_layout_name()
        reply = QMessageBox.question(
            self, "Excluir Layout",
            f"Tem certeza que deseja excluir o layout '{current}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            if not self._profiles.delete_layout(current):
                QMessageBox.warning(
                    self, "Erro",
                    "Não é possível excluir o último layout."
                )
            else:
                self._update_layout_combo()
                self._update_tray_layouts()

    # ==========================================================
    # Action Configuration
    # ==========================================================

    @Slot(int, int)
    def _on_button_config(self, row: int, col: int):
        """Abre diálogo de configuração para um botão."""
        current = self._profiles.get_button_action(row, col)
        dialog = ActionDialog(
            f"Configurar Botão [{row},{col}]",
            current,
            for_pot=False,
            parent=self,
        )
        if dialog.exec() == ActionDialog.Accepted:
            result = dialog.get_result()
            self._profiles.set_button_action(
                row, col,
                result["action"],
                result["params"],
                result["label"],
            )

    @Slot(int)
    def _on_pot_config(self, index: int):
        """Abre diálogo de configuração para um potenciômetro."""
        current = self._profiles.get_pot_action(index)
        dialog = ActionDialog(
            f"Configurar Potenciômetro {index} (A{index})",
            current,
            for_pot=True,
            parent=self,
        )
        if dialog.exec() == ActionDialog.Accepted:
            result = dialog.get_result()
            self._profiles.set_pot_action(
                index,
                result["action"],
                result["params"],
                result["label"],
            )

    # ==========================================================
    # Serial Events (feedback visual)
    # ==========================================================

    @Slot(int, int, bool)
    def _on_serial_button(self, row: int, col: int, pressed: bool):
        """Feedback visual quando um botão é pressionado no Arduino."""
        if pressed:
            self._dashboard_grid.flash_button(row, col)
            self._mapping_grid.flash_button(row, col)

    @Slot(int, int)
    def _on_serial_pot(self, index: int, value: int):
        """Atualiza barras dos potenciômetros."""
        self._dashboard_pots.update_value(index, value)
        self._mapping_pots.update_value(index, value)

    # ==========================================================
    # Serial Connection
    # ==========================================================

    def _refresh_ports(self):
        """Atualiza lista de portas seriais."""
        self._port_combo.clear()
        ports = SerialWorker.list_ports()
        saved_port = self._profiles.get_serial_config().get("port", "")

        for port in ports:
            display = f"{port['device']} — {port['description']}"
            self._port_combo.addItem(display, port["device"])

        if not ports:
            self._port_combo.addItem("Nenhuma porta encontrada", "")

        # Seleciona a porta salva se disponível
        for i in range(self._port_combo.count()):
            if self._port_combo.itemData(i) == saved_port:
                self._port_combo.setCurrentIndex(i)
                break

    @Slot()
    def _on_serial_connect(self):
        """Conecta à porta serial selecionada."""
        port = self._port_combo.currentData()
        if not port:
            QMessageBox.warning(self, "Erro", "Selecione uma porta serial.")
            return

        baud = self._baud_spin.value()
        self._profiles.set_serial_config(port, baud)
        self._serial_mgr.connect_serial(port, baud)
        self._statusbar.showMessage(f"Conectando a {port}...")

    @Slot()
    def _on_serial_disconnect(self):
        """Desconecta da porta serial."""
        self._serial_mgr.disconnect_serial()

    @Slot(bool)
    def _on_serial_status_changed(self, connected: bool):
        """Atualiza UI quando status serial muda."""
        if connected:
            self._serial_status.setText("● Conectado")
            self._serial_status.setStyleSheet(STATUS_CONNECTED)
            self._serial_connect_btn.setEnabled(False)
            self._serial_disconnect_btn.setEnabled(True)
        else:
            self._serial_status.setText("● Desconectado")
            self._serial_status.setStyleSheet(STATUS_DISCONNECTED)
            self._serial_connect_btn.setEnabled(True)
            self._serial_disconnect_btn.setEnabled(False)

        self._tray.update_serial_status(connected)

    @Slot(str)
    def _on_serial_error(self, msg: str):
        """Mostra erro serial."""
        self._statusbar.showMessage(f"Erro Serial: {msg}", 8000)
        logger.error("Erro serial: %s", msg)

    # ==========================================================
    # OBS Connection
    # ==========================================================

    @Slot()
    def _on_obs_connect(self):
        """Conecta ao OBS WebSocket."""
        host = self._obs_host.text().strip() or "localhost"
        port = self._obs_port.value()
        password = self._obs_password.text()

        self._profiles.set_obs_config(host, port, password)
        self._statusbar.showMessage(f"Conectando ao OBS em {host}:{port}...")

        success = self._obs.connect(host, port, password)
        if not success:
            self._statusbar.showMessage("Falha ao conectar ao OBS.", 5000)

    @Slot()
    def _on_obs_disconnect(self):
        """Desconecta do OBS."""
        self._obs.disconnect()

    @Slot(bool)
    def _on_obs_status_changed(self, connected: bool):
        """Atualiza UI quando status OBS muda."""
        if connected:
            self._obs_status.setText("● Conectado")
            self._obs_status.setStyleSheet(STATUS_CONNECTED)
            self._obs_connect_btn.setEnabled(False)
            self._obs_disconnect_btn.setEnabled(True)
            self._statusbar.showMessage("OBS conectado!", 3000)
        else:
            self._obs_status.setText("● Desconectado")
            self._obs_status.setStyleSheet(STATUS_DISCONNECTED)
            self._obs_connect_btn.setEnabled(True)
            self._obs_disconnect_btn.setEnabled(False)

        self._tray.update_obs_status(connected)

    @Slot(str)
    def _on_obs_error(self, msg: str):
        """Mostra erro OBS."""
        self._statusbar.showMessage(f"Erro OBS: {msg}", 8000)

    # ==========================================================
    # Action Feedback
    # ==========================================================

    @Slot(str)
    def _on_action_executed(self, description: str):
        """Mostra última ação executada."""
        self._last_action_label.setText(description)
        self._statusbar.showMessage(f"Ação: {description}", 3000)

    # ==========================================================
    # Window Events
    # ==========================================================

    def closeEvent(self, event):
        """Minimiza para o tray em vez de fechar."""
        event.ignore()
        self.hide()
        self._tray.showMessage(
            "StreamDeck DIY",
            "Minimizado para a bandeja. Clique duplo para abrir.",
            QSystemTrayIcon.Information,
            2000,
        )

    def _show_from_tray(self):
        """Mostra a janela a partir do tray."""
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def _on_quit(self):
        """Encerra a aplicação."""
        self._serial_mgr.cleanup()
        self._obs.disconnect()
        from PySide6.QtWidgets import QApplication
        QApplication.instance().quit()
