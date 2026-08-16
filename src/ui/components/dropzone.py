"""Drag and drop file upload zone widget."""

from __future__ import annotations

from pathlib import Path
from typing import Optional
from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QPainter, QPen, QColor
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class DropZoneWidget(QWidget):
    """Interactive drag-and-drop zone with animated state highlighting."""

    file_dropped = pyqtSignal(str)  # Emits absolute file path

    SUPPORTED_EXTENSIONS = {".zip", ".rar", ".manifest", ".lua", ".vdf"}

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._is_hovered = False

        self.setMinimumHeight(180)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)

        # Icon / Emoji Label
        self.icon_label = QLabel("📦", self)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setStyleSheet("font-size: 42px; background: transparent; border: none;")

        # Primary Text
        self.title_label = QLabel("Paket veya Dosyayı Buraya Sürükleyip Bırakın", self)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #f3f6f9; background: transparent; border: none;")

        # Subtitle
        self.subtitle_label = QLabel(
            "Desteklenen formatlar: .zip, .rar, .manifest, .lua", self
        )
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle_label.setStyleSheet("font-size: 12px; color: #93a7ba; background: transparent; border: none;")

        # Browse Button
        self.browse_btn = QPushButton("📁 Dosya Seç...", self)
        self.browse_btn.setFixedWidth(140)
        self.browse_btn.clicked.connect(self._open_file_dialog)

        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_layout.addWidget(self.browse_btn)

        layout.addWidget(self.icon_label)
        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)
        layout.addLayout(btn_layout)

    def _open_file_dialog(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Paket veya Manifest Dosyası Seçin",
            "",
            "Steam Paketleri (*.zip *.rar *.manifest *.lua *.vdf);;Tüm Dosyalar (*.*)",
        )
        if file_path:
            self.file_dropped.emit(file_path)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                path = Path(urls[0].toLocalFile())
                if path.suffix.lower() in self.SUPPORTED_EXTENSIONS or path.is_dir():
                    self._is_hovered = True
                    self.update()
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dragLeaveEvent(self, event) -> None:
        self._is_hovered = False
        self.update()
        event.accept()

    def dropEvent(self, event: QDropEvent) -> None:
        self._is_hovered = False
        self.update()
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if file_path:
                self.file_dropped.emit(file_path)
                event.acceptProposedAction()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background color
        bg_color = QColor("#1e3048") if self._is_hovered else QColor("#172332")
        painter.setBrush(bg_color)

        # Dashed Border
        border_color = QColor("#66c0f4") if self._is_hovered else QColor("#2a425f")
        pen = QPen(border_color, 2, Qt.PenStyle.DashLine)
        painter.setPen(pen)

        rect = self.rect().adjusted(2, 2, -2, -2)
        painter.drawRoundedRect(rect, 12, 12)
