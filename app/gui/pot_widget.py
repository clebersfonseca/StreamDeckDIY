"""
PotWidget — Widget visual dos potenciômetros do StreamDeck.

Mostra 3 barras de progresso com valores em tempo real
e labels configuráveis.
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton,
)

from app.core.profile_manager import ActionType, ProfileManager
from app.gui.styles import COLORS


class PotWidget(QWidget):
    """Widget visual para os 3 potenciômetros."""

    # Sinal para configurar um potenciômetro
    pot_config_requested = Signal(int)  # índice do pot

    NUM_POTS = 3
    POT_LABELS = ["Pot A0", "Pot A1", "Pot A2"]

    def __init__(self, profile_manager: ProfileManager, parent=None):
        super().__init__(parent)
        self._profiles = profile_manager
        self._bars: dict[int, QProgressBar] = {}
        self._labels: dict[int, QLabel] = {}
        self._value_labels: dict[int, QLabel] = {}
        self._action_labels: dict[int, QLabel] = {}

        self._setup_ui()
        self._update_labels()

        self._profiles.config_changed.connect(self._update_labels)
        self._profiles.layout_changed.connect(lambda _: self._update_labels())

    def _setup_ui(self):
        """Cria os widgets dos potenciômetros."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(8, 8, 8, 8)

        for i in range(self.NUM_POTS):
            pot_layout = QVBoxLayout()
            pot_layout.setSpacing(4)

            # Linha do topo: label + valor
            top_row = QHBoxLayout()

            name_label = QLabel(self.POT_LABELS[i])
            name_label.setStyleSheet(f"font-weight: 700; color: {COLORS['cyan']};")
            self._labels[i] = name_label

            action_label = QLabel("Sem ação")
            action_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
            self._action_labels[i] = action_label

            value_label = QLabel("0%")
            value_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-weight: 600;")
            value_label.setFixedWidth(50)
            self._value_labels[i] = value_label

            config_btn = QPushButton("⚙")
            config_btn.setFixedSize(28, 28)
            config_btn.setToolTip("Configurar ação")
            config_btn.clicked.connect(
                lambda checked, idx=i: self.pot_config_requested.emit(idx)
            )

            top_row.addWidget(name_label)
            top_row.addWidget(action_label)
            top_row.addStretch()
            top_row.addWidget(value_label)
            top_row.addWidget(config_btn)

            # Barra de progresso
            bar = QProgressBar()
            bar.setRange(0, 1023)
            bar.setValue(0)
            bar.setTextVisible(False)
            bar.setFixedHeight(16)
            self._bars[i] = bar

            pot_layout.addLayout(top_row)
            pot_layout.addWidget(bar)
            main_layout.addLayout(pot_layout)

        main_layout.addStretch()

    def _update_labels(self):
        """Atualiza os labels de ação dos potenciômetros."""
        for i in range(self.NUM_POTS):
            action = self._profiles.get_pot_action(i)
            action_type = action.get("action", ActionType.NONE.value)
            label = action.get("label", "")

            if action_type == ActionType.NONE.value:
                self._action_labels[i].setText("Sem ação")
                self._action_labels[i].setStyleSheet(
                    f"color: {COLORS['text_muted']}; font-size: 11px;"
                )
            else:
                display = label if label else action_type.replace("_", " ").title()
                self._action_labels[i].setText(display)
                self._action_labels[i].setStyleSheet(
                    f"color: {COLORS['accent_light']}; font-size: 11px;"
                )

    def update_value(self, index: int, value: int):
        """Atualiza o valor de um potenciômetro (0-1023)."""
        if index in self._bars:
            self._bars[index].setValue(value)
            percent = int(value / 1023.0 * 100)
            self._value_labels[index].setText(f"{percent}%")
