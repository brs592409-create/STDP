"""Main application window assembly and layout."""

from __future__ import annotations

from typing import Optional
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.core.config import config_manager
from src.core.logger import get_logger
from src.steam.detector import steam_detector
from src.ui.browser_view import BrowserView
from src.ui.components.log_console import LogConsoleWidget
from src.ui.health_view import HealthView
from src.ui.onlinefix_view import OnlineFixView
from src.ui.settings_view import SettingsView

logger = get_logger("ui.main_window")


class MainWindow(QMainWindow):
    """Main window hosting navigation sidebar, stacked views, and live log console."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("STDP - Steam Tool Depotbox Pipeline")
        self.resize(1120, 780)
        self.setMinimumSize(980, 660)

        self._init_ui()
        self._update_status_badges()

    def _init_ui(self) -> None:
        central_widget = QWidget(self)
        central_widget.setObjectName("CentralWidget")
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Top Header Bar
        header_bar = self._create_header_bar()
        root_layout.addWidget(header_bar)

        # 2. Main Splitter (Left Sidebar + Center Views / Bottom Console)
        main_h_layout = QHBoxLayout()
        main_h_layout.setContentsMargins(0, 0, 0, 0)
        main_h_layout.setSpacing(0)

        # Sidebar
        sidebar = self._create_sidebar()
        main_h_layout.addWidget(sidebar)

        # Center + Console Vertical Splitter
        v_splitter = QSplitter(Qt.Orientation.Vertical)
        v_splitter.setStyleSheet("QSplitter::handle { background-color: #1e3048; height: 3px; }")

        # Views Stack
        self.stack = QStackedWidget(self)
        self.browser_view = BrowserView(self)
        self.onlinefix_view = OnlineFixView(self)
        self.health_view = HealthView(self)
        self.settings_view = SettingsView(self)

        self.stack.addWidget(self.browser_view)    # index 0 (Default - DepotBox Web)
        self.stack.addWidget(self.onlinefix_view)  # index 1 (Online-Fix Steam_Fix)
        self.stack.addWidget(self.health_view)     # index 2 (Health & Diagnostics)
        self.stack.addWidget(self.settings_view)   # index 3 (Settings)

        # Bottom Console
        self.log_console = LogConsoleWidget(self)
        self.log_console.setMinimumHeight(100)

        v_splitter.addWidget(self.stack)
        v_splitter.addWidget(self.log_console)
        v_splitter.setStretchFactor(0, 5)
        v_splitter.setStretchFactor(1, 1)

        main_h_layout.addWidget(v_splitter, 1)
        root_layout.addLayout(main_h_layout, 1)

    def _create_header_bar(self) -> QWidget:
        header = QFrame(self)
        header.setFixedHeight(54)
        header.setStyleSheet("background-color: #0b1016; border-bottom: 1px solid #1e3048;")

        layout = QHBoxLayout(header)
        layout.setContentsMargins(18, 0, 18, 0)
        layout.setSpacing(12)

        # Logo & App Title
        logo_label = QLabel("⚡ STDP", header)
        logo_label.setStyleSheet("font-size: 18px; font-weight: 800; color: #66c0f4;")

        desc_label = QLabel("Steam Tool Depotbox & Online-Fix Pipeline", header)
        desc_label.setStyleSheet("font-size: 12px; color: #93a7ba; font-weight: 500;")

        # Status Badges
        self.steam_badge = QLabel("Steam: Denetleniyor...", header)
        self.steam_badge.setProperty("class", "status-badge")

        self.hook_badge = QLabel("Kanca: SteamTools", header)
        self.hook_badge.setProperty("class", "status-badge")

        layout.addWidget(logo_label)
        layout.addWidget(desc_label)
        layout.addStretch()
        layout.addWidget(self.steam_badge)
        layout.addWidget(self.hook_badge)

        return header

    def _create_sidebar(self) -> QWidget:
        sidebar = QWidget(self)
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(200)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 16, 0, 16)
        layout.setSpacing(4)

        self.nav_buttons: list[QPushButton] = []

        nav_items = [
            ("🌐  DepotBox Web", 0),
            ("🎮  Online-Fix (Steam)", 1),
            ("🩺  Teşhis & Sağlık", 2),
            ("⚙️  Ayarlar", 3),
        ]

        for title, idx in nav_items:
            btn = QPushButton(title, sidebar)
            btn.setProperty("class", "nav-btn")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, i=idx: self._switch_tab(i))
            layout.addWidget(btn)
            self.nav_buttons.append(btn)

        layout.addStretch()

        # Set first button active
        if self.nav_buttons:
            self.nav_buttons[0].setChecked(True)

        return sidebar

    def _switch_tab(self, index: int) -> None:
        """Switch stacked widget index and highlight active sidebar button."""
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)

        # Trigger view-specific refreshes
        if index == 1:
            self.onlinefix_view.refresh_installed_games()
        elif index == 2:
            self.health_view.refresh_health()
        elif index == 3:
            self.settings_view.load_settings()

        self._update_status_badges()

    def _update_status_badges(self) -> None:
        """Refresh header status indicator badges."""
        is_running, pid = steam_detector.is_steam_running()
        if is_running:
            self.steam_badge.setText(f"Steam: Aktif (PID {pid})")
            self.steam_badge.setStyleSheet(
                "background-color: #1b384c; color: #57cb65; border: 1px solid #57cb65; "
                "border-radius: 4px; padding: 3px 8px; font-weight: bold;"
            )
        else:
            self.steam_badge.setText("Steam: Kapalı")
            self.steam_badge.setStyleSheet(
                "background-color: #172332; color: #93a7ba; border: 1px solid #2a425f; "
                "border-radius: 4px; padding: 3px 8px;"
            )

        active_unl = config_manager.config.active_unlocker
        self.hook_badge.setText(f"Kanca: {active_unl.upper()}")
