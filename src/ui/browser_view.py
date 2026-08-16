"""Embedded Chromium web browser with automated 1-click DepotBox download interception."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Optional
from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWebEngineCore import QWebEngineDownloadRequest, QWebEnginePage, QWebEngineProfile
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.core.logger import get_logger
from src.core.models import GamePackage
from src.depotbox.extractor import archive_extractor
from src.ui.adblocker import setup_adblocker_on_profile
from src.ui.components.disk_selector import DiskSelectorWidget
from src.ui.workers import InjectGameWorker

logger = get_logger("ui.browser_view")


class BrowserView(QWidget):
    """Integrated Chromium browser that intercepts DepotBox downloads and injects games into Steam."""

    HOME_URL = "https://depotbox.org/"

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._download_dir = Path(tempfile.gettempdir()) / "STDP_BrowserDownloads"
        self._download_dir.mkdir(parents=True, exist_ok=True)
        self._profile_storage = Path.home() / "AppData" / "Local" / "STDP" / "WebEngineProfile"
        self._profile_storage.mkdir(parents=True, exist_ok=True)

        self._inject_worker: Optional[InjectGameWorker] = None
        self._active_downloads: list[QWebEngineDownloadRequest] = []

        self._init_ui()
        self._setup_browser_engine()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 8, 10, 8)
        main_layout.setSpacing(8)

        # 1. Navigation Toolbar + Library Selector
        top_bar = QFrame(self)
        top_bar.setProperty("class", "surface-card")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(8, 6, 8, 6)
        top_layout.setSpacing(6)

        # Navigation Buttons
        self.btn_back = QPushButton("◀", top_bar)
        self.btn_back.setToolTip("Geri")
        self.btn_back.setFixedSize(32, 32)
        self.btn_back.clicked.connect(self._go_back)

        self.btn_forward = QPushButton("▶", top_bar)
        self.btn_forward.setToolTip("İleri")
        self.btn_forward.setFixedSize(32, 32)
        self.btn_forward.clicked.connect(self._go_forward)

        self.btn_refresh = QPushButton("🔄", top_bar)
        self.btn_refresh.setToolTip("Sayfayı Yenile")
        self.btn_refresh.setFixedSize(32, 32)
        self.btn_refresh.clicked.connect(self._reload_page)

        self.btn_home = QPushButton("🏠", top_bar)
        self.btn_home.setToolTip("DepotBox Ana Sayfası")
        self.btn_home.setFixedSize(32, 32)
        self.btn_home.clicked.connect(self._go_home)

        # Address bar
        self.url_input = QLineEdit(top_bar)
        self.url_input.setPlaceholderText("https://depotbox.org/ veya AppID girin...")
        self.url_input.returnPressed.connect(self._navigate_url)

        self.btn_go = QPushButton("➔ Git", top_bar)
        self.btn_go.setProperty("class", "primary-btn")
        self.btn_go.setFixedSize(70, 32)
        self.btn_go.clicked.connect(self._navigate_url)

        top_layout.addWidget(self.btn_back)
        top_layout.addWidget(self.btn_forward)
        top_layout.addWidget(self.btn_refresh)
        top_layout.addWidget(self.btn_home)
        top_layout.addWidget(self.url_input, 1)
        top_layout.addWidget(self.btn_go)

        main_layout.addWidget(top_bar)

        # 2. Target Disk Bar
        disk_bar = QFrame(self)
        disk_bar.setProperty("class", "surface-card")
        disk_layout = QHBoxLayout(disk_bar)
        disk_layout.setContentsMargins(8, 4, 8, 4)
        disk_layout.setSpacing(10)

        info_lbl = QLabel("🎯 Hedef Steam Diski:", disk_bar)
        info_lbl.setStyleSheet("color: #66c0f4; font-weight: bold; font-size: 12px;")

        self.disk_selector = DiskSelectorWidget(disk_bar)

        disk_layout.addWidget(info_lbl)
        disk_layout.addWidget(self.disk_selector, 1)
        main_layout.addWidget(disk_bar)

        # 3. Intercept & Progress Banner (Hidden by default)
        self.progress_banner = QFrame(self)
        self.progress_banner.setProperty("class", "surface-card")
        self.progress_banner.setStyleSheet(
            "background-color: #122338; border: 1px solid #66c0f4; border-radius: 8px;"
        )
        self.progress_banner.setVisible(False)
        banner_layout = QVBoxLayout(self.progress_banner)
        banner_layout.setContentsMargins(12, 10, 12, 10)
        banner_layout.setSpacing(6)

        self.progress_status_label = QLabel("İndirme yakalandı...", self.progress_banner)
        self.progress_status_label.setStyleSheet("font-weight: bold; color: #66c0f4; font-size: 13px;")

        self.progress_bar = QProgressBar(self.progress_banner)
        self.progress_bar.setRange(0, 100)

        banner_layout.addWidget(self.progress_status_label)
        banner_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.progress_banner)

        # 4. Chromium WebEngine View
        self.web_view = QWebEngineView(self)
        main_layout.addWidget(self.web_view, 1)

    def _setup_browser_engine(self) -> None:
        """Configure persistent Chromium profile, storage, cookies, and download interception."""
        self.profile = QWebEngineProfile("STDP_Persistent_Profile", self)
        self.profile.setPersistentStoragePath(str(self._profile_storage))
        self.profile.setCachePath(str(self._profile_storage / "Cache"))
        self.profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies
        )
        self.profile.downloadRequested.connect(self._on_download_requested)

        # Attach AdBlocker
        self._ad_interceptor = setup_adblocker_on_profile(self.profile)

        self.web_page = QWebEnginePage(self.profile, self.web_view)
        self.web_page.setBackgroundColor(QColor("#101822"))
        self.web_view.setPage(self.web_page)
        self.web_view.setStyleSheet("background-color: #101822;")
        self.web_view.setUrl(QUrl(self.HOME_URL))
        self.web_view.urlChanged.connect(self._on_url_changed)
        self.web_view.loadProgress.connect(self._on_load_progress)
        self.web_view.loadFinished.connect(self._on_load_finished)
        logger.info("Persistent Chromium profile and download hook initialized.")

    def _go_back(self) -> None:
        self.web_view.back()

    def _go_forward(self) -> None:
        self.web_view.forward()

    def _reload_page(self) -> None:
        self.web_view.reload()

    def _go_home(self) -> None:
        self.web_view.setUrl(QUrl(self.HOME_URL))

    def _navigate_url(self) -> None:
        raw_text = self.url_input.text().strip()
        if not raw_text:
            return

        if raw_text.isdigit():
            target = f"https://depotbox.org/game/{raw_text}"
        elif not raw_text.startswith(("http://", "https://")):
            target = f"https://{raw_text}"
        else:
            target = raw_text

        self.web_view.setUrl(QUrl(target))

    def _on_url_changed(self, qurl: QUrl) -> None:
        self.url_input.setText(qurl.toString())

    def _on_load_progress(self, progress: int) -> None:
        if progress < 100:
            self.btn_refresh.setText("⏳")
        else:
            self.btn_refresh.setText("🔄")

    def _on_load_finished(self, success: bool) -> None:
        """Inject cookie and DOM overrides to auto-bypass the 15-second promo modal."""
        if not success:
            return

        js_bypass = """
        (function() {
            try {
                // 1. Set the cookie that DepotBox checks
                document.cookie = "hideAnnouncementModal=true; path=/; max-age=31536000";
                
                // 2. Hide modal element if already in DOM
                const modal = document.getElementById("announcementModal");
                if (modal) {
                    modal.classList.add("hidden");
                    modal.style.display = "none";
                }
                
                // 3. Mark checkbox as checked
                const chk = document.getElementById("hideAnnouncementModal");
                if (chk) {
                    chk.checked = true;
                }
                
                // 4. Enable and click close button if visible
                const closeBtn = document.getElementById("closeAnnouncementModalBtn");
                if (closeBtn) {
                    closeBtn.disabled = false;
                    closeBtn.click();
                }
            } catch(e) {
                console.error("STDP modal bypass error:", e);
            }
        })();
        """
        self.web_view.page().runJavaScript(js_bypass)

    def _on_download_requested(self, download: QWebEngineDownloadRequest) -> None:
        """Intercept any download stream from DepotBox and route it to auto-injection."""
        filename = download.downloadFileName() or "depotbox_package.zip"
        dest_path = self._download_dir / filename

        # Set destination path
        download.setDownloadDirectory(str(self._download_dir))
        download.setDownloadFileName(filename)
        download.accept()

        self._active_downloads.append(download)
        logger.info(f"Intercepted download: {filename} -> {dest_path}")

        # Show banner
        self.progress_banner.setVisible(True)
        self.progress_status_label.setText(f"📥 Paket indiriliyor: {filename}...")
        self.progress_bar.setValue(20)

        download.isFinishedChanged.connect(lambda: self._on_download_finished(download, dest_path))

    def _on_download_finished(self, download: QWebEngineDownloadRequest, file_path: Path) -> None:
        """Trigger automatic extraction and injection upon download completion."""
        state = download.state()
        if state == QWebEngineDownloadRequest.DownloadState.DownloadCompleted:
            logger.info(f"Download completed successfully: {file_path}")
            self.progress_status_label.setText(f"⚡ '{file_path.name}' paketi işleniyor ve Steam'e aktarılıyor...")
            self.progress_bar.setValue(60)

            try:
                pkg = archive_extractor.extract_package(file_path)
                target_lib = self.disk_selector.get_selected_library()

                if not target_lib:
                    QMessageBox.warning(self, "Kütüphane Hatası", "Lütfen geçerli bir hedef Steam kütüphanesi seçin!")
                    self.progress_banner.setVisible(False)
                    return

                self._inject_worker = InjectGameWorker(
                    app_info=pkg.app_info,
                    target_library_path=target_lib,
                    package=pkg,
                )
                self._inject_worker.progress.connect(self._on_inject_progress)
                self._inject_worker.finished.connect(self._on_inject_finished)
                self._inject_worker.start()

            except Exception as e:
                logger.error(f"Auto-injection failed for {file_path}: {e}")
                self.progress_banner.setVisible(False)
                QMessageBox.critical(self, "Paket Hatası", f"Paket açılırken hata oluştu: {e}")

        elif state == QWebEngineDownloadRequest.DownloadState.DownloadCancelled:
            self.progress_banner.setVisible(False)
            logger.warning(f"Download cancelled: {file_path}")
        elif state == QWebEngineDownloadRequest.DownloadState.DownloadInterrupted:
            self.progress_banner.setVisible(False)
            logger.error(f"Download interrupted: {file_path}")
            QMessageBox.warning(self, "İndirme Kesildi", "Dosya indirilirken bir bağlantı hatası oluştu.")

    def _on_inject_progress(self, status: str, pct: int) -> None:
        self.progress_status_label.setText(status)
        self.progress_bar.setValue(pct)

    def _on_inject_finished(self, success: bool, msg: str) -> None:
        self.progress_banner.setVisible(False)
        if success:
            QMessageBox.information(
                self,
                "1-Tıkla Aktarım Başarılı! 🎉",
                msg + "\n\nOyun Steam kütüphanenize eklendi! Steam üzerinden dilediğiniz sürücüyü seçip indirmeyi başlatabilirsiniz.\n\n💡 Not: Lisans hatası almamak için arka planda SteamTools kilit motorunun çalıştığından emin olun (sağ altta sistem tepsisinde simgesi görünmelidir)."
            )
        else:
            QMessageBox.critical(self, "Aktarım Hatası", msg)
