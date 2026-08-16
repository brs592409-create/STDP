"""Interactive game display card with 1-click injection button."""

from __future__ import annotations

from typing import Optional
import requests
from PyQt6.QtCore import QByteArray, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.core.models import AppInfo


class ImageLoaderThread(QThread):
    """Background worker to download banner images without blocking UI."""

    image_loaded = pyqtSignal(bytes)

    def __init__(self, url: str) -> None:
        super().__init__()
        self.url = url

    def run(self) -> None:
        try:
            resp = requests.get(self.url, timeout=5)
            if resp.status_code == 200:
                self.image_loaded.emit(resp.content)
        except Exception:
            pass


class GameCardWidget(QFrame):
    """Card widget representing a game with its banner and injection action."""

    inject_requested = pyqtSignal(AppInfo)

    def __init__(self, app_info: AppInfo, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.app_info = app_info
        self.setProperty("class", "surface-card")
        self.setFixedHeight(120)

        self._init_ui()
        self._load_banner()

    def _init_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 14, 10)
        layout.setSpacing(14)

        # 1. Game Banner Image
        self.banner_label = QLabel(self)
        self.banner_label.setFixedSize(184, 86)
        self.banner_label.setStyleSheet("background-color: #0d141d; border-radius: 6px; border: 1px solid #2a425f;")
        self.banner_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.banner_label.setText("Görsel Yok")

        # 2. Metadata Middle Column
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # Title + AppID Tag
        title_row = QHBoxLayout()
        self.title_label = QLabel(self.app_info.name, self)
        self.title_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #f3f6f9;")
        self.title_label.setWordWrap(True)

        self.appid_badge = QLabel(f"AppID: {self.app_info.app_id}", self)
        self.appid_badge.setProperty("class", "status-badge")
        self.appid_badge.setFixedHeight(22)

        title_row.addWidget(self.title_label, 1)
        title_row.addWidget(self.appid_badge)

        # Details row
        depot_count = len(self.app_info.depots)
        size_gb = self.app_info.total_size_bytes / (1024 ** 3)
        size_text = f"{size_gb:.1f} GB" if size_gb >= 0.1 else f"{self.app_info.total_size_bytes / (1024**2):.1f} MB"
        if depot_count == 0:
            details_str = "Resmi Steam İstemcisi Üzerinden İndirilecek"
        else:
            details_str = f"📦 {depot_count} Depot Dosyası | Boyut: ~{size_text}"

        self.details_label = QLabel(details_str, self)
        self.details_label.setStyleSheet("font-size: 12px; color: #93a7ba;")

        info_layout.addLayout(title_row)
        info_layout.addWidget(self.details_label)

        # 3. Action Button Right Column
        action_layout = QVBoxLayout()
        action_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.inject_btn = QPushButton("⚡ 1-Tıkla Aktar", self)
        self.inject_btn.setProperty("class", "primary-btn")
        self.inject_btn.setFixedSize(140, 38)
        self.inject_btn.clicked.connect(lambda: self.inject_requested.emit(self.app_info))

        action_layout.addWidget(self.inject_btn)

        layout.addWidget(self.banner_label)
        layout.addLayout(info_layout, 1)
        layout.addLayout(action_layout)

    def _load_banner(self) -> None:
        url = self.app_info.header_url or self.app_info.thumbnail_url
        if url:
            self._loader = ImageLoaderThread(url)
            self._loader.image_loaded.connect(self._set_pixmap)
            self._loader.start()

    def _set_pixmap(self, raw_bytes: bytes) -> None:
        pixmap = QPixmap()
        if pixmap.loadFromData(raw_bytes):
            scaled = pixmap.scaled(
                self.banner_label.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.banner_label.setPixmap(scaled)
            self.banner_label.setText("")
