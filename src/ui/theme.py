"""PyQt6 QSS theme and styling system for STDP."""

from __future__ import annotations

# Color Tokens from docs/DESIGN.md
COLOR_BG_PRIMARY = "#101822"
COLOR_BG_SURFACE = "#172332"
COLOR_BG_ELEVATED = "#1e3048"
COLOR_BORDER_SUBTLE = "#2a425f"
COLOR_ACCENT_PRIMARY = "#66c0f4"
COLOR_ACCENT_HOVER = "#80d0ff"
COLOR_TEXT_PRIMARY = "#f3f6f9"
COLOR_TEXT_SECONDARY = "#93a7ba"
COLOR_TEXT_MUTED = "#627588"
COLOR_STATUS_SUCCESS = "#57cb65"
COLOR_STATUS_WARNING = "#f9a825"
COLOR_STATUS_ERROR = "#ef5350"

STYLESHEET = """
/* Global Window Styling */
QMainWindow, QDialog, QWidget#CentralWidget {
    background-color: #101822;
    color: #f3f6f9;
    font-family: 'Segoe UI', 'Inter', -apple-system, sans-serif;
    font-size: 13px;
}

/* Sidebar Navigation */
QWidget#Sidebar {
    background-color: #0b1118;
    border-right: 1px solid #1e3048;
}

QPushButton.nav-btn {
    background-color: transparent;
    color: #93a7ba;
    font-size: 14px;
    font-weight: 600;
    text-align: left;
    padding: 12px 18px;
    border: none;
    border-left: 3px solid transparent;
    border-radius: 0px;
}

QPushButton.nav-btn:hover {
    background-color: #172332;
    color: #f3f6f9;
}

QPushButton.nav-btn:checked, QPushButton.nav-btn.active {
    background-color: #172332;
    color: #66c0f4;
    border-left: 3px solid #66c0f4;
}

/* Surface Containers & Cards */
QFrame.surface-card {
    background-color: #172332;
    border: 1px solid #1e3048;
    border-radius: 8px;
}

QFrame.surface-card:hover {
    border: 1px solid #2a425f;
}

/* Buttons */
QPushButton {
    background-color: #1e3048;
    color: #f3f6f9;
    border: 1px solid #2a425f;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
    font-size: 13px;
}

QPushButton:hover {
    background-color: #263d5c;
    border-color: #66c0f4;
}

QPushButton:pressed {
    background-color: #172332;
}

QPushButton:disabled {
    background-color: #141e2b;
    color: #627588;
    border-color: #1e3048;
}

QPushButton.primary-btn {
    background-color: #66c0f4;
    color: #101822;
    border: none;
    font-weight: bold;
    font-size: 13px;
    border-radius: 6px;
    padding: 9px 18px;
}

QPushButton.primary-btn:hover {
    background-color: #80d0ff;
}

QPushButton.primary-btn:pressed {
    background-color: #4196c7;
}

QPushButton.primary-btn:disabled {
    background-color: #2a425f;
    color: #627588;
}

QPushButton.success-btn {
    background-color: #2e7d32;
    color: #f3f6f9;
    border: none;
    font-weight: bold;
}

QPushButton.success-btn:hover {
    background-color: #388e3c;
}

/* Inputs & LineEdits */
QLineEdit {
    background-color: #172332;
    border: 1px solid #2a425f;
    border-radius: 6px;
    color: #f3f6f9;
    padding: 9px 14px;
    font-size: 13px;
    selection-background-color: #66c0f4;
    selection-color: #101822;
}

QLineEdit:focus {
    border: 1px solid #66c0f4;
    background-color: #1e3048;
}

QLineEdit:disabled {
    background-color: #121a24;
    color: #627588;
    border-color: #1e3048;
}

/* ComboBox */
QComboBox {
    background-color: #172332;
    border: 1px solid #2a425f;
    border-radius: 6px;
    color: #f3f6f9;
    padding: 8px 12px;
    font-size: 13px;
}

QComboBox:hover {
    border-color: #66c0f4;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox QAbstractItemView {
    background-color: #172332;
    border: 1px solid #2a425f;
    color: #f3f6f9;
    selection-background-color: #1e3048;
    selection-color: #66c0f4;
    outline: none;
    padding: 4px;
}

/* Progress Bar */
QProgressBar {
    background-color: #0d141d;
    border: 1px solid #1e3048;
    border-radius: 6px;
    text-align: center;
    color: #f3f6f9;
    font-size: 11px;
    font-weight: bold;
    height: 18px;
}

QProgressBar::chunk {
    background-color: #66c0f4;
    border-radius: 5px;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background-color: #101822;
    width: 10px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background-color: #2a425f;
    min-height: 25px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background-color: #66c0f4;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    border: none;
    background-color: #101822;
    height: 10px;
}

QScrollBar::handle:horizontal {
    background-color: #2a425f;
    min-width: 25px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #66c0f4;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* Text Edit / Console */
QTextEdit, QPlainTextEdit {
    background-color: #0d131a;
    border: 1px solid #1e3048;
    border-radius: 6px;
    color: #d1d9e0;
    font-family: 'Consolas', 'Cascadia Code', monospace;
    font-size: 12px;
    padding: 8px;
}

/* Labels */
QLabel {
    color: #f3f6f9;
}

QLabel.text-secondary {
    color: #93a7ba;
}

QLabel.text-muted {
    color: #627588;
}

QLabel.h1-title {
    font-size: 20px;
    font-weight: bold;
    color: #f3f6f9;
}

QLabel.h2-title {
    font-size: 15px;
    font-weight: 600;
    color: #f3f6f9;
}

/* Badges and Tags */
QLabel.status-badge {
    background-color: #1e3048;
    border: 1px solid #2a425f;
    border-radius: 4px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 600;
    color: #66c0f4;
}

/* CheckBox */
QCheckBox {
    color: #f3f6f9;
    spacing: 8px;
    font-size: 13px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    background-color: #172332;
    border: 1px solid #2a425f;
    border-radius: 4px;
}

QCheckBox::indicator:checked {
    background-color: #66c0f4;
    border-color: #66c0f4;
}

/* GroupBox */
QGroupBox {
    background-color: #172332;
    border: 1px solid #1e3048;
    border-radius: 8px;
    margin-top: 18px;
    padding-top: 14px;
    font-weight: bold;
    color: #66c0f4;
    font-size: 13px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    background-color: #172332;
}

/* Tab Widget & TabBar */
QTabWidget::pane {
    border: 1px solid #1e3048;
    background-color: #121a24;
    border-radius: 6px;
    top: -1px;
}

QTabBar::tab {
    background-color: #101822;
    color: #93a7ba;
    border: 1px solid #1e3048;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 8px 16px;
    margin-right: 2px;
    font-weight: 600;
    font-size: 12px;
}

QTabBar::tab:hover {
    background-color: #172332;
    color: #f3f6f9;
}

QTabBar::tab:selected {
    background-color: #172332;
    color: #66c0f4;
    border-bottom: 2px solid #66c0f4;
}

/* Table Widget & TableView (Dark Theme) */
QTableWidget, QTableView {
    background-color: #121a24;
    alternate-background-color: #16202c;
    border: 1px solid #1e3048;
    border-radius: 6px;
    gridline-color: #1e3048;
    color: #f3f6f9;
    font-size: 12px;
    selection-background-color: #1b384c;
    selection-color: #66c0f4;
    outline: none;
}

QTableWidget::item {
    padding: 6px 10px;
    border-bottom: 1px solid #182330;
}

QTableWidget::item:selected {
    background-color: #1b384c;
    color: #66c0f4;
    font-weight: bold;
}

QTableWidget::item:hover {
    background-color: #1a2839;
}

/* Table Headers */
QHeaderView {
    background-color: #0d141d;
}

QHeaderView::section {
    background-color: #0d141d;
    color: #66c0f4;
    font-weight: bold;
    font-size: 12px;
    border: none;
    border-right: 1px solid #1e3048;
    border-bottom: 2px solid #1e3048;
    padding: 8px 10px;
}

QHeaderView::section:vertical {
    background-color: #0d141d;
    color: #627588;
    border: none;
    border-bottom: 1px solid #1e3048;
    border-right: 1px solid #1e3048;
    padding: 4px 6px;
}

QHeaderView::section:hover {
    background-color: #141e2b;
}

QTableCornerButton::section {
    background-color: #0d141d;
    border: none;
}

/* ToolTip */
QToolTip {
    background-color: #172332;
    color: #f3f6f9;
    border: 1px solid #2a425f;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
}
"""


def apply_theme(app) -> None:
    """Apply the custom dark Steam stylesheet to the QApplication."""
    app.setStyleSheet(STYLESHEET)
