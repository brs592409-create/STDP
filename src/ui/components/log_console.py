"""Real-time colorized log stream viewer widget."""

from __future__ import annotations

import html
from typing import Optional
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.core.logger import add_log_listener, remove_log_listener


class LogBridge(QObject):
    """Bridge object to safely route log messages across Qt threads via signals."""
    log_received = pyqtSignal(str, str, str)


class LogConsoleWidget(QFrame):
    """Realtime log console widget displaying colorized events."""

    LEVEL_COLORS = {
        "INFO": "#c7d5e0",
        "DEBUG": "#627588",
        "WARNING": "#f9a825",
        "WARN": "#f9a825",
        "ERROR": "#ef5350",
        "CRITICAL": "#ff1744",
        "SUCCESS": "#57cb65",
    }

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("LogConsoleWidget")
        self.setProperty("class", "surface-card")

        self._bridge = LogBridge()
        self._bridge.log_received.connect(self._append_log_entry)

        self._init_ui()
        add_log_listener(self._handle_raw_log)

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        # Header Control Bar
        header_layout = QHBoxLayout()
        title_label = QLabel("📊 Canlı Konsol & Olay Akışı", self)
        title_label.setStyleSheet("font-weight: 600; color: #f3f6f9; font-size: 12px;")

        self.auto_scroll_cb = QCheckBox("Otomatik Kaydır", self)
        self.auto_scroll_cb.setChecked(True)
        self.auto_scroll_cb.setStyleSheet("font-size: 11px; color: #93a7ba;")

        self.clear_btn = QPushButton("Temizle", self)
        self.clear_btn.setFixedSize(65, 24)
        self.clear_btn.setStyleSheet("font-size: 11px; padding: 2px 6px;")
        self.clear_btn.clicked.connect(self.clear_console)

        self.export_btn = QPushButton("Dışa Aktar", self)
        self.export_btn.setFixedSize(75, 24)
        self.export_btn.setStyleSheet("font-size: 11px; padding: 2px 6px;")
        self.export_btn.clicked.connect(self._export_logs)

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.auto_scroll_cb)
        header_layout.addWidget(self.clear_btn)
        header_layout.addWidget(self.export_btn)

        # Text Console Area
        self.text_edit = QPlainTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.text_edit.setMaximumBlockCount(1000)
        self.text_edit.setStyleSheet(
            "background-color: #0b1016; border: 1px solid #1e3048; border-radius: 4px; "
            "color: #c7d5e0; font-family: 'Consolas', monospace; font-size: 11px;"
        )

        layout.addLayout(header_layout)
        layout.addWidget(self.text_edit)

    def _handle_raw_log(self, timestamp: str, level: str, message: str) -> None:
        """Called from any thread by logger handler."""
        self._bridge.log_received.emit(timestamp, level, message)

    def _append_log_entry(self, timestamp: str, level: str, message: str) -> None:
        """Executed on Qt Main Thread."""
        color = self.LEVEL_COLORS.get(level.upper(), "#c7d5e0")
        if "success" in message.lower() or "başarılı" in message.lower():
            color = self.LEVEL_COLORS["SUCCESS"]

        escaped_time = html.escape(timestamp)
        escaped_level = html.escape(level)
        escaped_msg = html.escape(message)

        formatted_line = (
            f"<span style='color: #627588;'>[{escaped_time}]</span> "
            f"<span style='color: {color}; font-weight: bold;'>[{escaped_level}]</span> "
            f"<span style='color: {color};'>{escaped_msg}</span>"
        )

        self.text_edit.appendHtml(formatted_line)

        if self.auto_scroll_cb.isChecked():
            self.text_edit.moveCursor(QTextCursor.MoveOperation.End)

    def clear_console(self) -> None:
        self.text_edit.clear()

    def _export_logs(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Logları Kaydet", "stdp_console.txt", "Text Dosyaları (*.txt)"
        )
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self.text_edit.toPlainText())

    def closeEvent(self, event) -> None:
        remove_log_listener(self._handle_raw_log)
        super().closeEvent(event)
