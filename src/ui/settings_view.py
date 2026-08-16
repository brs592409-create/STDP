"""Application and Steam configuration settings view."""

from __future__ import annotations

from pathlib import Path
from typing import Optional
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.core.config import config_manager
from src.core.logger import get_logger
from src.steam.detector import steam_detector
from src.unlockers.factory import list_unlockers

logger = get_logger("ui.settings_view")


class SettingsView(QWidget):
    """View for adjusting directories, unlocker adapters, and pipeline behaviors."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_ui()
        self.load_settings()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 15, 20, 15)
        main_layout.setSpacing(16)

        # 1. Header
        header_box = QVBoxLayout()
        header_box.setSpacing(2)
        title = QLabel("⚙️ Uygulama & Kütüphane Ayarları", self)
        title.setProperty("class", "h1-title")
        subtitle = QLabel(
            "Steam dizin yollarını, aktif kanca motorunu ve otomasyon tercihlerini yapılandırın.", self
        )
        subtitle.setProperty("class", "text-secondary")
        header_box.addWidget(title)
        header_box.addWidget(subtitle)
        main_layout.addLayout(header_box)

        # 2. Form Card
        self.form_card = QFrame(self)
        self.form_card.setProperty("class", "surface-card")
        form_layout = QGridLayout(self.form_card)
        form_layout.setContentsMargins(18, 16, 18, 16)
        form_layout.setHorizontalSpacing(16)
        form_layout.setVerticalSpacing(14)

        # Steam Path
        lbl_steam = QLabel("🎮 Steam Kurulum Yolu:", self.form_card)
        lbl_steam.setStyleSheet("font-weight: 600;")
        self.steam_path_input = QLineEdit(self.form_card)
        self.steam_browse_btn = QPushButton("📁 Gözat", self.form_card)
        self.steam_browse_btn.setFixedWidth(80)
        self.steam_browse_btn.clicked.connect(self._browse_steam_path)

        steam_row = QHBoxLayout()
        steam_row.addWidget(self.steam_path_input, 1)
        steam_row.addWidget(self.steam_browse_btn)

        # Active Unlocker
        lbl_unlocker = QLabel("🔌 Aktif Kilit Açıcı Motor:", self.form_card)
        lbl_unlocker.setStyleSheet("font-weight: 600;")
        self.unlocker_combo = QComboBox(self.form_card)
        for unl in list_unlockers():
            self.unlocker_combo.addItem(f"{unl.name} — {unl.description}", unl.identifier)

        # Depotbox API
        lbl_api = QLabel("🌐 Depotbox API / Web Adresi:", self.form_card)
        lbl_api.setStyleSheet("font-weight: 600;")
        self.api_input = QLineEdit(self.form_card)

        # Checkboxes
        self.auto_shutdown_cb = QCheckBox("Manifest yazarken Steam'i otomatik kapat", self.form_card)
        self.auto_restart_cb = QCheckBox("Aktarım bittiğinde Steam'i otomatik yeniden başlat ve indirmeyi tetikle", self.form_card)

        form_layout.addWidget(lbl_steam, 0, 0)
        form_layout.addLayout(steam_row, 0, 1)

        form_layout.addWidget(lbl_unlocker, 1, 0)
        form_layout.addWidget(self.unlocker_combo, 1, 1)

        form_layout.addWidget(lbl_api, 2, 0)
        form_layout.addWidget(self.api_input, 2, 1)

        form_layout.addWidget(self.auto_shutdown_cb, 3, 1)
        form_layout.addWidget(self.auto_restart_cb, 4, 1)

        main_layout.addWidget(self.form_card)

        # 3. Actions Row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.save_btn = QPushButton("💾 Değişiklikleri Kaydet", self)
        self.save_btn.setProperty("class", "primary-btn")
        self.save_btn.setFixedHeight(38)
        self.save_btn.clicked.connect(self.save_settings)

        self.reset_btn = QPushButton("Varsayılana Sıfırla", self)
        self.reset_btn.setFixedHeight(38)
        self.reset_btn.clicked.connect(self.reset_defaults)

        btn_row.addWidget(self.save_btn)
        btn_row.addWidget(self.reset_btn)
        btn_row.addStretch()

        main_layout.addLayout(btn_row)
        main_layout.addStretch()

    def load_settings(self) -> None:
        """Populate form fields from configuration."""
        cfg = config_manager.config
        sp = cfg.steam_path or str(steam_detector.find_steam_path() or "")
        self.steam_path_input.setText(sp)
        self.api_input.setText(cfg.depotbox_api_url)
        self.auto_shutdown_cb.setChecked(cfg.auto_shutdown_steam)
        self.auto_restart_cb.setChecked(cfg.auto_restart_steam)

        idx = self.unlocker_combo.findData(cfg.active_unlocker)
        if idx >= 0:
            self.unlocker_combo.setCurrentIndex(idx)

    def save_settings(self) -> None:
        """Save form values back to config.json."""
        active_unl = self.unlocker_combo.currentData()
        config_manager.update(
            steam_path=self.steam_path_input.text().strip() or None,
            active_unlocker=active_unl,
            depotbox_api_url=self.api_input.text().strip(),
            auto_shutdown_steam=self.auto_shutdown_cb.isChecked(),
            auto_restart_steam=self.auto_restart_cb.isChecked(),
        )
        QMessageBox.information(self, "Ayarlar Kaydedildi", "Ayarlar başarıyla kaydedildi!")

    def reset_defaults(self) -> None:
        reply = QMessageBox.question(
            self, "Sıfırlama Onayı", "Tüm ayarları varsayılan değerlerine sıfırlamak istediğinize emin misiniz?"
        )
        if reply == QMessageBox.StandardButton.Yes:
            config_manager.reset_to_defaults()
            self.load_settings()

    def _browse_steam_path(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Steam Kurulum Dizinini Seçin")
        if path:
            self.steam_path_input.setText(path)
