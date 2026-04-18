"""
ButtonGrid — Widget visual da matriz 3x5 de botões do StreamDeck.

Mostra uma grade de botões que:
- Refletem a ação configurada (label + cor)
- Acendem quando pressionados no Arduino (feedback visual)
- São clicáveis para abrir o diálogo de configuração
"""

from PySide6.QtCore import Signal, QTimer
from PySide6.QtWidgets import QWidget, QGridLayout, QPushButton

from app.core.profile_manager import ActionType, ProfileManager, ACTION_METADATA
from app.gui.styles import (
    DECK_BUTTON_STYLE,
    DECK_BUTTON_ACTIVE_STYLE,
    DECK_BUTTON_CONFIGURED_STYLE,
    COLORS,
    ACTION_COLORS,
    ACTION_ICONS,
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

    def _get_button_style(self, action_type: str) -> str:
        """Gera estilo dinâmico baseado no tipo de ação."""
        metadata = ACTION_METADATA.get(ActionType(action_type), {})
        category = metadata.get("category", "Geral")
        color_info = ACTION_COLORS.get(category, ACTION_COLORS["Geral"])

        return f"""
QPushButton {{
    background-color: {color_info['bg']};
    color: {color_info['text']};
    border: 2px solid {color_info['border']};
    border-radius: 10px;
    padding: 8px;
    font-size: 11px;
    font-weight: 600;
    min-width: 80px;
    min-height: 60px;
}}

QPushButton:hover {{
    background-color: {COLORS['bg_hover']};
    border-color: {color_info['text']};
}}

QPushButton:pressed {{
    background-color: {color_info['border']};
    border-color: {COLORS['accent_light']};
}}
"""

    def _update_labels(self):
        """Atualiza os textos e estilos dos botões baseado no layout ativo."""
        for (row, col), btn in self._buttons.items():
            action = self._profiles.get_button_action(row, col)
            action_type = action.get("action", ActionType.NONE.value)
            label = action.get("label", "")

            icon = ACTION_ICONS.get(action_type, ACTION_ICONS["none"])

            if action_type == ActionType.NONE.value:
                btn.setText(f"{row},{col}")
                btn.setStyleSheet(DECK_BUTTON_STYLE)
                btn.setToolTip(f"Botão [{row},{col}]\nSem ação configurada\nClique para configurar")
            else:
                display_text = label if label else action_type.replace("_", " ").title()
                if len(display_text) > 12:
                    display_text = display_text[:10] + "…"
                btn.setText(f"{icon} {display_text}")
                btn.setStyleSheet(self._get_button_style(action_type))
                btn.setToolTip(
                    f"Botão [{row},{col}]\n"
                    f"Ação: {action_type}\n"
                    f"Label: {label}\n"
                    f"Clique para editar"
                )

    def flash_button(self, row: int, col: int):
        """Acende um botão com animação."""
        key = (row, col)
        if key not in self._buttons:
            return

        btn = self._buttons[key]
        action = self._profiles.get_button_action(row, col)
        action_type = action.get("action", ActionType.NONE.value)

        metadata = ACTION_METADATA.get(ActionType(action_type), {})
        category = metadata.get("category", "Geral")
        color_info = ACTION_COLORS.get(category, ACTION_COLORS["Geral"])

        flash_style = f"""
QPushButton {{
    background-color: {color_info['border']};
    color: white;
    border: 2px solid {COLORS['accent_light']};
    border-radius: 10px;
    padding: 8px;
    font-size: 11px;
    font-weight: 700;
    min-width: 80px;
    min-height: 60px;
}}
"""

        original_style = btn.styleSheet()
        btn.setStyleSheet(flash_style)
        btn.setGraphicsEffect(None)

        if key in self._flash_timers:
            self._flash_timers[key].stop()
            del self._flash_timers[key]

        timer = QTimer(self)
        timer.setSingleShot(True)
        timeout_count = [0]

        def restore():
            timeout_count[0] += 1
            if timeout_count[0] >= 2:
                btn.setStyleSheet(original_style)
                timer.stop()
            else:
                btn.setStyleSheet(DECK_BUTTON_ACTIVE_STYLE)

        timer.timeout.connect(restore)
        timer.start(150)
        self._flash_timers[key] = timer
