"""
StreamDeck DIY — Entry Point

Aplicação desktop para controlar o OBS e o Windows
através de um StreamDeck DIY baseado em Arduino Pro Micro.
"""

import sys
import logging

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from app.gui.main_window import MainWindow
from app.gui.styles import DARK_THEME


def setup_logging():
    """Configura o sistema de logging."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    # Reduz verbosidade de libs externas
    logging.getLogger("serial").setLevel(logging.WARNING)
    logging.getLogger("obsws_python").setLevel(logging.WARNING)


def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Iniciando StreamDeck DIY...")

    app = QApplication(sys.argv)
    app.setApplicationName("StreamDeck DIY")
    app.setOrganizationName("StreamDeckDIY")

    # Não sai quando a última janela é fechada (fica no tray)
    app.setQuitOnLastWindowClosed(False)

    # Aplica tema escuro
    app.setStyleSheet(DARK_THEME)

    # Configura ícone da aplicação
    from pathlib import Path
    from PySide6.QtGui import QIcon
    icon_path = Path(__file__).parent / "gui" / "assets" / "icon.svg"
    app.setWindowIcon(QIcon(str(icon_path)))

    # Janela principal
    window = MainWindow()
    window.show()

    logger.info("Aplicação pronta.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
