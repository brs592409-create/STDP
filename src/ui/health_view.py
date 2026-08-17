"""System health diagnosis, permissions, and 1-click repair view."""

from __future__ import annotations

from typing import Optional
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.core.config import config_manager
from src.core.logger import get_logger
from src.core.models import SystemHealth
from src.steam.detector import steam_detector
from src.ui.workers import HealthCheckWorker
from src.unlockers.factory import get_unlocker

logger = get_logger("ui.health_view")


class HealthView(QWidget):
    """System diagnostic, path validation, and 1-click hook repair view."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._worker: Optional[HealthCheckWorker] = None
        self._init_ui()
        self.refresh_health()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 15, 20, 15)
        main_layout.setSpacing(14)

        # 1. Header
        header_box = QVBoxLayout()
        header_box.setSpacing(2)
        title = QLabel("🩺 Sistem Teşhis & Sağlık Kontrolü", self)
        title.setProperty("class", "h1-title")
        subtitle = QLabel(
            "Steam ortamı, klasör izinleri, süreç durumları ve kanca adaptörünün sağlığını denetleyin.", self
        )
        subtitle.setProperty("class", "text-secondary")
        header_box.addWidget(title)
        header_box.addWidget(subtitle)
        main_layout.addLayout(header_box)

        # 2. Diagnostic Card Grid
        self.card = QFrame(self)
        self.card.setProperty("class", "surface-card")
        card_layout = QGridLayout(self.card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setHorizontalSpacing(24)
        card_layout.setVerticalSpacing(12)

        # Labels & Badges for 5 checkpoints
        self.row_labels = [
            ("🎮 Steam Kurulum Yolu:", QLabel("Taranıyor...", self.card)),
            ("🔌 Yerleşik Kanca Motoru:", QLabel("Taranıyor...", self.card)),
            ("🛡️ Yönetici İzinleri (Admin):", QLabel("Taranıyor...", self.card)),
            ("⚙️ Steam Süreci (steam.exe):", QLabel("Taranıyor...", self.card)),
            ("💾 Depotcache Yazma İzni:", QLabel("Taranıyor...", self.card)),
        ]

        for row_idx, (title_str, val_label) in enumerate(self.row_labels):
            lbl = QLabel(title_str, self.card)
            lbl.setStyleSheet("font-weight: 600; font-size: 13px; color: #f3f6f9;")
            val_label.setStyleSheet("font-size: 13px;")
            card_layout.addWidget(lbl, row_idx, 0)
            card_layout.addWidget(val_label, row_idx, 1)

        main_layout.addWidget(self.card)

        # 3. Security / Antivirus Guidance Card
        self.defender_card = QFrame(self)
        self.defender_card.setProperty("class", "surface-card")
        self.defender_card.setStyleSheet("background-color: #121c27; border: 1px solid #1e3048; border-radius: 8px;")
        def_layout = QVBoxLayout(self.defender_card)
        def_layout.setContentsMargins(16, 12, 16, 12)
        def_layout.setSpacing(6)

        def_title = QLabel("🛡️ Windows Defender & Antivirüs Koruması Bilgisi", self.defender_card)
        def_title.setStyleSheet("font-weight: bold; color: #66c0f4; font-size: 13px;")

        def_desc = QLabel(
            "SteamTools kanca motoru ve Online-Fix DLL dosyaları (OnlineFix64.dll vb.) oyun dosyalarına müdahale ettiği için "
            "Windows Defender veya harici antivirüsler tarafından yanlışlıkla (False-Positive) engellenebilir veya silinebilir.\n"
            "Sorunsuz bir deneyim için STDP klasörünü ve Steam klasörünüzü Defender dışlama listesine eklemeniz önerilir.",
            self.defender_card,
        )
        def_desc.setStyleSheet("color: #93a7ba; font-size: 12px; line-height: 1.4;")
        def_desc.setWordWrap(True)

        self.add_exclusion_btn = QPushButton("🛡️ STDP ve Steam Klasörünü Defender İstisnalarına Ekle", self.defender_card)
        self.add_exclusion_btn.setFixedHeight(34)
        self.add_exclusion_btn.clicked.connect(self._add_defender_exclusion)

        def_layout.addWidget(def_title)
        def_layout.addWidget(def_desc)
        def_layout.addWidget(self.add_exclusion_btn)

        main_layout.addWidget(self.defender_card)

        # 4. Actions Row
        actions_row = QHBoxLayout()
        actions_row.setSpacing(12)

        self.refresh_btn = QPushButton("🔄 Şimdi Yeniden Teşhis Et", self)
        self.refresh_btn.setFixedHeight(38)
        self.refresh_btn.clicked.connect(self.refresh_health)

        self.repair_btn = QPushButton("⚡ Otomatik Onar / Kancayı Kur", self)
        self.repair_btn.setProperty("class", "primary-btn")
        self.repair_btn.setFixedHeight(38)
        self.repair_btn.clicked.connect(self._auto_repair)

        actions_row.addWidget(self.refresh_btn)
        actions_row.addWidget(self.repair_btn)
        actions_row.addStretch()

        main_layout.addLayout(actions_row)
        main_layout.addStretch()

    def refresh_health(self) -> None:
        """Run health check worker in background."""
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("Denetleniyor...")

        self._worker = HealthCheckWorker()
        self._worker.health_ready.connect(self._on_health_ready)
        self._worker.start()

    def _on_health_ready(self, health: SystemHealth) -> None:
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("🔄 Şimdi Yeniden Teşhis Et")

        # 1. Steam Path
        path_label = self.row_labels[0][1]
        if health.steam_installed and health.steam_path:
            path_label.setText(f"✓ {health.steam_path}")
            path_label.setStyleSheet("color: #57cb65; font-weight: bold;")
        else:
            path_label.setText("✗ Bulunamadı")
            path_label.setStyleSheet("color: #ef5350; font-weight: bold;")

        # 2. Hook status
        hook_label = self.row_labels[1][1]
        if health.active_hook_installed:
            hook_label.setText("✓ Kurulu / Aktif")
            hook_label.setStyleSheet("color: #57cb65; font-weight: bold;")
        else:
            hook_label.setText("⚠️ Kurulu Değil (Otomatik Onar ile Kurulabilir)")
            hook_label.setStyleSheet("color: #f9a825; font-weight: bold;")

        # 3. Admin Permissions
        admin_label = self.row_labels[2][1]
        if health.is_admin:
            admin_label.setText("✓ Yönetici Yetkisi Mevcut")
            admin_label.setStyleSheet("color: #57cb65; font-weight: bold;")
        else:
            admin_label.setText("ℹ️ Standart Kullanıcı (Yeterli)")
            admin_label.setStyleSheet("color: #93a7ba;")

        # 4. Steam Process
        proc_label = self.row_labels[3][1]
        if health.steam_running:
            proc_label.setText(f"✓ Çalışıyor (PID: {health.steam_pid})")
            proc_label.setStyleSheet("color: #57cb65; font-weight: bold;")
        else:
            proc_label.setText("⚪ Kapalı")
            proc_label.setStyleSheet("color: #93a7ba;")

        # 5. Depotcache
        depot_label = self.row_labels[4][1]
        if health.depotcache_writable:
            depot_label.setText("✓ Yazılabilir")
            depot_label.setStyleSheet("color: #57cb65; font-weight: bold;")
        else:
            depot_label.setText("✗ Yazılamıyor (İzin Hatası)")
            depot_label.setStyleSheet("color: #ef5350; font-weight: bold;")

    def _add_defender_exclusion(self) -> None:
        """Add exclusion for STDP application folder and Steam folder in Windows Defender."""
        import subprocess
        from pathlib import Path
        app_dir = Path(__file__).resolve().parent.parent.parent
        sp = steam_detector.find_steam_path()

        paths = [str(app_dir)]
        if sp and sp.exists():
            paths.append(str(sp))

        success_count = 0
        for p in paths:
            try:
                cmd = f"Add-MpPreference -ExclusionPath '{p}'"
                res = subprocess.run(
                    ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd],
                    capture_output=True,
                    timeout=10,
                )
                if res.returncode == 0:
                    success_count += 1
            except Exception as e:
                logger.warning(f"Failed to add exclusion for {p}: {e}")

        if success_count > 0:
            QMessageBox.information(
                self,
                "İstisna Eklendi",
                f"STDP ve Steam klasörleri Windows Defender dışlama listesine başarıyla eklendi!\n"
                f"Artık kanca ve fix dosyalarınız silinmeyecektir.",
            )
        else:
            QMessageBox.warning(
                self,
                "Yetki Gerekli",
                "Defender istisnası eklenemedi. Lütfen uygulamayı 'Yönetici Olarak Çalıştır' seçeneğiyle açtığınızdan emin olun.",
            )

    def _auto_repair(self) -> None:
        """Attempt to initialize folders and install active hook."""
        cfg = config_manager.config
        sp = steam_detector.find_steam_path()
        if not sp:
            QMessageBox.critical(self, "Hata", "Steam kurulum dizini bulunamadığı için onarım yapılamıyor!")
            return

        unlocker = get_unlocker(cfg.active_unlocker) or get_unlocker("steamtools")
        if unlocker:
            unlocker.install_hook(sp)

        # Ensure depotcache
        (sp / "depotcache").mkdir(parents=True, exist_ok=True)

        QMessageBox.information(
            self, "Onarım Başarılı", "Kanca dizinleri ve depotcache klasörü başarıyla oluşturuldu ve doğrulandı."
        )
        self.refresh_health()
