"""
Estilos da aplicação StreamDeck DIY — Dark Theme moderno.
"""

# Paleta de cores
COLORS = {
    "bg_darkest": "#0f0f1a",
    "bg_dark": "#1a1a2e",
    "bg_surface": "#252542",
    "bg_card": "#2d2d50",
    "bg_hover": "#363660",
    "bg_input": "#1e1e38",
    "accent": "#7c3aed",
    "accent_hover": "#9333ea",
    "accent_light": "#a855f7",
    "cyan": "#06b6d4",
    "cyan_dark": "#0891b2",
    "green": "#22c55e",
    "green_dark": "#16a34a",
    "red": "#ef4444",
    "red_dark": "#dc2626",
    "orange": "#f59e0b",
    "yellow": "#eab308",
    "text": "#f1f5f9",
    "text_secondary": "#94a3b8",
    "text_muted": "#64748b",
    "border": "#374151",
    "border_light": "#4b5563",
}

DARK_THEME = f"""
/* ============================================
   StreamDeck DIY — Dark Theme
   ============================================ */

QMainWindow, QDialog {{
    background-color: {COLORS['bg_dark']};
    color: {COLORS['text']};
}}

QWidget {{
    color: {COLORS['text']};
    font-family: 'Segoe UI', 'Inter', 'Roboto', sans-serif;
    font-size: 13px;
}}

/* ---- Abas (QTabWidget) ---- */

QTabWidget::pane {{
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    background-color: {COLORS['bg_surface']};
    padding: 8px;
}}

QTabBar::tab {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['text_secondary']};
    border: 1px solid {COLORS['border']};
    border-bottom: none;
    padding: 10px 24px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: 600;
}}

QTabBar::tab:selected {{
    background-color: {COLORS['bg_surface']};
    color: {COLORS['accent_light']};
    border-bottom: 2px solid {COLORS['accent']};
}}

QTabBar::tab:hover:!selected {{
    background-color: {COLORS['bg_hover']};
    color: {COLORS['text']};
}}

/* ---- Botões ---- */

QPushButton {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
    min-height: 20px;
}}

QPushButton:hover {{
    background-color: {COLORS['bg_hover']};
    border-color: {COLORS['accent']};
}}

QPushButton:pressed {{
    background-color: {COLORS['accent']};
}}

QPushButton:disabled {{
    background-color: {COLORS['bg_darkest']};
    color: {COLORS['text_muted']};
    border-color: {COLORS['bg_surface']};
}}

/* Botão primário */
QPushButton[class="primary"] {{
    background-color: {COLORS['accent']};
    border-color: {COLORS['accent']};
    color: white;
}}

QPushButton[class="primary"]:hover {{
    background-color: {COLORS['accent_hover']};
}}

/* Botão de sucesso */
QPushButton[class="success"] {{
    background-color: {COLORS['green_dark']};
    border-color: {COLORS['green']};
    color: white;
}}

QPushButton[class="success"]:hover {{
    background-color: {COLORS['green']};
}}

/* Botão de perigo */
QPushButton[class="danger"] {{
    background-color: {COLORS['red_dark']};
    border-color: {COLORS['red']};
    color: white;
}}

QPushButton[class="danger"]:hover {{
    background-color: {COLORS['red']};
}}

/* ---- Inputs ---- */

QLineEdit, QSpinBox, QComboBox {{
    background-color: {COLORS['bg_input']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 8px 12px;
    selection-background-color: {COLORS['accent']};
    min-height: 20px;
}}

QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border-color: {COLORS['accent']};
}}

QComboBox::drop-down {{
    border: none;
    padding-right: 8px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid {COLORS['text_secondary']};
    margin-right: 8px;
}}

QComboBox QAbstractItemView {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    selection-background-color: {COLORS['accent']};
    outline: none;
}}

/* ---- Labels ---- */

QLabel {{
    color: {COLORS['text']};
    background: transparent;
}}

QLabel[class="title"] {{
    font-size: 18px;
    font-weight: 700;
    color: {COLORS['text']};
}}

QLabel[class="subtitle"] {{
    font-size: 14px;
    font-weight: 600;
    color: {COLORS['text_secondary']};
}}

QLabel[class="muted"] {{
    color: {COLORS['text_muted']};
    font-size: 12px;
}}

/* ---- Group Box ---- */

QGroupBox {{
    background-color: {COLORS['bg_card']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    margin-top: 16px;
    padding: 16px;
    padding-top: 28px;
    font-weight: 600;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 16px;
    padding: 0 8px;
    color: {COLORS['accent_light']};
}}

/* ---- Scroll ---- */

QScrollArea {{
    border: none;
    background: transparent;
}}

QScrollBar:vertical {{
    background: {COLORS['bg_darkest']};
    width: 8px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical {{
    background: {COLORS['border']};
    border-radius: 4px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background: {COLORS['border_light']};
}}

QScrollBar::add-line, QScrollBar::sub-line {{
    height: 0px;
}}

/* ---- Progress Bar (potenciômetros) ---- */

QProgressBar {{
    background-color: {COLORS['bg_input']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    text-align: center;
    color: {COLORS['text']};
    min-height: 24px;
    font-weight: 600;
}}

QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {COLORS['accent']}, stop:1 {COLORS['cyan']});
    border-radius: 5px;
}}

/* ---- Status Bar ---- */

QStatusBar {{
    background-color: {COLORS['bg_darkest']};
    color: {COLORS['text_secondary']};
    border-top: 1px solid {COLORS['border']};
    padding: 4px;
}}

/* ---- Menu ---- */

QMenu {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 4px;
}}

QMenu::item {{
    padding: 8px 32px 8px 16px;
    border-radius: 4px;
}}

QMenu::item:selected {{
    background-color: {COLORS['accent']};
    color: white;
}}

QMenu::separator {{
    height: 1px;
    background: {COLORS['border']};
    margin: 4px 8px;
}}

/* ---- ToolTip ---- */

QToolTip {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    padding: 6px 10px;
}}
"""

# Estilo especial para os botões do grid do StreamDeck
DECK_BUTTON_STYLE = f"""
QPushButton {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['text']};
    border: 2px solid {COLORS['border']};
    border-radius: 10px;
    padding: 8px;
    font-size: 11px;
    font-weight: 600;
    min-width: 80px;
    min-height: 60px;
}}

QPushButton:hover {{
    background-color: {COLORS['bg_hover']};
    border-color: {COLORS['accent']};
}}

QPushButton:pressed {{
    background-color: {COLORS['accent']};
    border-color: {COLORS['accent_light']};
}}
"""

DECK_BUTTON_ACTIVE_STYLE = f"""
QPushButton {{
    background-color: {COLORS['accent']};
    color: white;
    border: 2px solid {COLORS['accent_light']};
    border-radius: 10px;
    padding: 8px;
    font-size: 11px;
    font-weight: 600;
    min-width: 80px;
    min-height: 60px;
}}
"""

DECK_BUTTON_CONFIGURED_STYLE = f"""
QPushButton {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['cyan']};
    border: 2px solid {COLORS['cyan_dark']};
    border-radius: 10px;
    padding: 8px;
    font-size: 11px;
    font-weight: 600;
    min-width: 80px;
    min-height: 60px;
}}

QPushButton:hover {{
    background-color: {COLORS['bg_hover']};
    border-color: {COLORS['cyan']};
}}

QPushButton:pressed {{
    background-color: {COLORS['accent']};
    border-color: {COLORS['accent_light']};
}}
"""

# Indicadores de status (conexão)
STATUS_CONNECTED = f"color: {COLORS['green']}; font-weight: 700;"
STATUS_DISCONNECTED = f"color: {COLORS['red']}; font-weight: 700;"
STATUS_IDLE = f"color: {COLORS['text_muted']}; font-weight: 600;"
