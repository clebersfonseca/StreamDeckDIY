"""
ButtonGrid — Widget visual da matriz 3x5 de botões do StreamDeck.

Mostra uma grade de botões que:
- Refletem a ação configurada (label + cor)
- Acendem quando pressionados no Arduino (feedback visual)
- São clicáveis para abrir o diálogo de configuração
"""

from PySide6.QtCore import Signal, QTimer
from PySide6.QtWidgets import QWidget, QGridLayout, QPushButton

from app.core.profile_manager import ActionType, ProfileManager
from app.gui.styles import (
    DECK_BUTTON_STYLE,
    DECK_BUTTON_ACTIVE_STYLE,
    DECK_BUTTON_CONFIGURED_STYLE,
)


class ButtonGrid(QWidget):
    """Grade visual 3x5 representando os botões do StreamDeck."""

    # Sinal emitido quando o usuário clica em um botão para configurar
    button_config_requested = Signal(int, int)  # (row, col)

    NUM_ROWS = 3
    NUM_COLS = 5

    def __init__(self, profile_manager: ProfileManager, parent=None):
        super().__init__(parent)
        self._profiles = profile_manager
        self._buttons: dict[tuple[int, int], QPushButton] = {}
        self._flash_timers: dict[tuple[int, int], QTimer] = {}

        self._setup_ui()
        self._update_labels()

        # Atualiza quando config muda
        self._profiles.config_changed.connect(self._update_labels)
        self._profiles.layout_changed.connect(lambda _: self._update_labels())

    def _setup_ui(self):
        """Cria a grade de botões."""
        layout = QGridLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)

        for row in range(self.NUM_ROWS):
            for col in range(self.NUM_COLS):
                btn = QPushButton()
                btn.setStyleSheet(DECK_BUTTON_STYLE)
                btn.setToolTip(f"Botão [{row},{col}]\nClique para configurar")

                # Captura row/col no closure
                btn.clicked.connect(
                    lambda checked, r=row, c=col: self.button_config_requested.emit(r, c)
                )

                layout.addWidget(btn, row, col)
                self._buttons[(row, col)] = btn

    def _update_labels(self):
        """Atualiza os textos e estilos dos botões baseado no layout ativo."""
        for (row, col), btn in self._buttons.items():
            action = self._profiles.get_button_action(row, col)
            action_type = action.get("action", ActionType.NONE.value)
            label = action.get("label", "")

            if action_type == ActionType.NONE.value:
                btn.setText(f"{row},{col}")
                btn.setStyleSheet(DECK_BUTTON_STYLE)
                btn.setToolTip(f"Botão [{row},{col}]\nSem ação configurada\nClique para configurar")
            else:
                display_text = label if label else action_type.replace("_", " ").title()
                # Trunca texto longo
                if len(display_text) > 14:
                    display_text = display_text[:12] + "…"
                btn.setText(display_text)
                btn.setStyleSheet(DECK_BUTTON_CONFIGURED_STYLE)
                btn.setToolTip(
                    f"Botão [{row},{col}]\n"
                    f"Ação: {action_type}\n"
                    f"Label: {label}\n"
                    f"Clique para editar"
                )

    def flash_button(self, row: int, col: int):
        """Acende um botão momentaneamente (feedback visual de pressionamento)."""
        key = (row, col)
        if key not in self._buttons:
            return

        btn = self._buttons[key]
        original_style = btn.styleSheet()
        btn.setStyleSheet(DECK_BUTTON_ACTIVE_STYLE)

        # Cancela timer anterior se existir
        if key in self._flash_timers:
            self._flash_timers[key].stop()

        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: btn.setStyleSheet(original_style))
        timer.start(200)  # Flash de 200ms
        self._flash_timers[key] = timer
