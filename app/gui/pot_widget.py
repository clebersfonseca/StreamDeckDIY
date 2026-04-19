"""
PotWidget — Widget visual dos potenciômetros do StreamDeck.

Mostra 3 barras de progresso com valores em tempo real
e labels configuráveis.
"""

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton,
    QFrame,
)
from PySide6.QtGui import QPainter, QPen, QColor, QBrush, QPaintEvent

from app.core.profile_manager import ActionType, ProfileManager, ACTION_METADATA
from app.gui.styles import COLORS, ACTION_COLORS


class CircularGauge(QFrame):
    """Gauge circular para visualização do potenciômetro."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(60, 60)
        self._value = 0
        self._max_value = 1023
        self._color = QColor(COLORS["accent"])

    def set_value(self, value: int):
        self._value = value
        self.update()

    def set_color(self, color: str):
        self._color = QColor(color)
        self.update()

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        center = self.rect().center()
        radius = min(self.width(), self.height()) // 2 - 6

        border_color = QColor(COLORS["border"])
        painter.setPen(QPen(border_color, 4))
        painter.drawEllipse(center, radius, radius)

        if self._value > 0:
            angle = -90 + (self._value / self._max_value) * 360
            painter.setPen(QPen(self._color, 4))
            painter.setBrush(QBrush(self._color))
            painter.drawArc(
                center.x() - radius,
                center.y() - radius,
                radius * 2,
                radius * 2,
                -90 * 16,
                int(angle * 16),
            )

        painter.end()


class PotWidget(QWidget):
    """Widget visual para os 3 potenciômetros."""

    pot_config_requested = Signal(int)

    NUM_POTS = 3
    POT_LABELS = ["Pot A0", "Pot A1", "Pot A2"]

    def __init__(self, profile_manager: ProfileManager, parent=None):
        super().__init__(parent)
        self._profiles = profile_manager
        self._bars: dict[int, QProgressBar] = {}
        self._gauges: dict[int, CircularGauge] = {}
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
            pot_layout = QHBoxLayout()
            pot_layout.setSpacing(12)

            gauge = CircularGauge()
            self._gauges[i] = gauge

            controls = QVBoxLayout()
            controls.setSpacing(4)

            top_row = QHBoxLayout()

            name_label = QLabel(self.POT_LABELS[i])
            name_label.setStyleSheet(f"font-weight: 700; color: {COLORS['cyan']};")
            self._labels[i] = name_label

            action_label = QLabel("Sem ação")
            action_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
            self._action_labels[i] = action_label

            config_btn = QPushButton("⚙")
            config_btn.setFixedSize(24, 24)
            config_btn.setToolTip("Configurar ação")
            config_btn.clicked.connect(
                lambda checked, idx=i: self.pot_config_requested.emit(idx)
            )

            top_row.addWidget(name_label)
            top_row.addStretch()
            top_row.addWidget(config_btn)

            value_label = QLabel("0%")
            value_label.setStyleSheet(
                f"color: {COLORS['text_secondary']}; font-size: 18px; font-weight: 700;"
            )
            self._value_labels[i] = value_label

            controls.addLayout(top_row)
            controls.addWidget(action_label)
            controls.addWidget(value_label)

            bar = QProgressBar()
            bar.setRange(0, 1023)
            bar.setValue(0)
            bar.setTextVisible(False)
            bar.setFixedHeight(8)
            bar.setStyleSheet(
                f"""
                QProgressBar {{
                    background-color: {COLORS['bg_input']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 4px;
                }}
                QProgressBar::chunk {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {COLORS['accent']}, stop:1 {COLORS['cyan']});
                    border-radius: 3px;
                }}
                """
            )
            self._bars[i] = bar

            controls.addWidget(bar)

            pot_layout.addWidget(gauge)
            pot_layout.addLayout(controls)
            main_layout.addLayout(pot_layout)

        main_layout.addStretch()

    def _update_labels(self):
        """Atualiza os labels de ação dos potenciômetros."""
        for i in range(self.NUM_POTS):
            action = self._profiles.get_pot_action(i)
            action_type = action.get("action", ActionType.NONE.value)
            label = action.get("label", "")
            inverted = action.get("inverted", False)

            metadata = ACTION_METADATA.get(ActionType(action_type), {})
            category = metadata.get("category", "Geral")
            color_info = ACTION_COLORS.get(category, ACTION_COLORS["Geral"])

            if action_type == ActionType.NONE.value:
                self._action_labels[i].setText("Sem ação")
                self._action_labels[i].setStyleSheet(
                    f"color: {COLORS['text_muted']}; font-size: 11px;"
                )
                self._gauges[i].set_color(COLORS["border"])
            else:
                display = label if label else action_type.replace("_", " ").title()
                if inverted:
                    display = f"🔄 {display}"
                self._action_labels[i].setText(display)
                self._action_labels[i].setStyleSheet(
                    f"color: {color_info['text']}; font-size: 11px;"
                )
                self._gauges[i].set_color(color_info["border"])

    def update_value(self, index: int, value: int):
        """Atualiza o valor de um potenciômetro (0-1023)."""
        if index in self._bars:
            self._bars[index].setValue(value)
            self._gauges[index].set_value(value)
            percent = int(value / 1023.0 * 100)
            self._value_labels[index].setText(f"{percent}%")
