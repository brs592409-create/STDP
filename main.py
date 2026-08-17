"""STDP (Steam Tool Depotbox Pipeline) Desktop Application Entry Point."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

from src.core.logger import get_logger, setup_logger
from src.ui.main_window import MainWindow
from src.ui.theme import apply_theme

logger = get_logger("main")


def main() -> int:
    """Initialize and run the STDP PyQt6 Desktop Application."""
    setup_logger()
    logger.info("Initializing STDP (Steam Tool Depotbox Pipeline)...")

    # High DPI scaling attributes
    if hasattr(Qt.ApplicationAttribute, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("STDP")
    app.setApplicationDisplayName("STDP - Steam Tool Depotbox Pipeline")
    app.setOrganizationName("STDP")

    # Set default modern font
    font = QFont("Segoe UI", 10)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(font)

    # Apply Dark Steam Theme QSS
    apply_theme(app)

    # Launch Main Window
    window = MainWindow()
    window.show()

    logger.info("Application UI successfully launched.")
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
