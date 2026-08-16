"""Unit and sanity tests for PyQt6 UI components."""

import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication
import pytest

from src.core.models import AppInfo, DepotInfo
from src.ui.browser_view import BrowserView
from src.ui.components.disk_selector import DiskSelectorWidget
from src.ui.components.dropzone import DropZoneWidget
from src.ui.components.game_card import GameCardWidget
from src.ui.components.log_console import LogConsoleWidget
from src.ui.health_view import HealthView
from src.ui.main_window import MainWindow
from src.ui.onlinefix_view import OnlineFixView
from src.ui.settings_view import SettingsView


@pytest.fixture(scope="session")
def qapp():
    """Ensure single QApplication instance for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


def test_components_instantiation(qapp):
    dropzone = DropZoneWidget()
    assert dropzone is not None

    disk_selector = DiskSelectorWidget()
    assert disk_selector is not None

    app_info = AppInfo(app_id=1091500, name="Cyberpunk 2077", depots=[DepotInfo(depot_id=1091501)])
    game_card = GameCardWidget(app_info)
    assert game_card is not None
    assert game_card.title_label.text() == "Cyberpunk 2077"

    log_console = LogConsoleWidget()
    assert log_console is not None


def test_views_instantiation(qapp, monkeypatch):
    monkeypatch.setattr("src.steam.detector.steam_detector.find_steam_path", lambda: None)
    monkeypatch.setattr("src.steam.detector.steam_detector.get_library_folders", lambda *args, **kwargs: [])

    settings_view = SettingsView()
    assert settings_view is not None

    health_view = HealthView()
    assert health_view is not None

    onlinefix_view = OnlineFixView()
    assert onlinefix_view is not None


def test_main_window_instantiation(qapp, monkeypatch):
    monkeypatch.setattr("src.steam.detector.steam_detector.find_steam_path", lambda: None)
    monkeypatch.setattr("src.steam.detector.steam_detector.get_library_folders", lambda *args, **kwargs: [])

    win = MainWindow()
    assert win is not None
    assert win.stack.count() == 4
    win._switch_tab(1)
    assert win.stack.currentIndex() == 1
    win._switch_tab(2)
    assert win.stack.currentIndex() == 2
    win._switch_tab(3)
    assert win.stack.currentIndex() == 3
    win._switch_tab(0)
    assert win.stack.currentIndex() == 0
