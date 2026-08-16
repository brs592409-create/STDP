"""Modern PyQt6 view for managing Online-Fix.me multiplayer fixes with browser, popup handling, and 1-click install."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional
from PyQt6.QtCore import QThread, QUrl, Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWebEngineCore import QWebEngineDownloadRequest, QWebEnginePage, QWebEngineProfile
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.core.config import config_manager
from src.core.logger import get_logger
from src.onlinefix.installer import InstalledGameInfo, online_fix_installer
from src.ui.adblocker import setup_adblocker_on_profile

logger = get_logger("ui.onlinefix_view")


class CustomWebEnginePage(QWebEnginePage):
    """Custom WebEnginePage that intercepts new window popups and strictly filters out ad redirects."""

    ALLOWED_HOST_KEYWORDS = [
        "online-fix",
        "pixeldrain",
        "drive.google",
        "google",
        "mega.nz",
        "qiwi",
        "fichier",
        "mediafire",
        "gofile",
        "torrent",
        "steam",
    ]

    def __init__(self, profile: QWebEngineProfile, view: QWebEngineView) -> None:
        super().__init__(profile, view)
        self._view = view

    def acceptNavigationRequest(self, url: QUrl, _type: QWebEnginePage.NavigationType, isMainFrame: bool) -> bool:
        """Strictly block malicious redirect domains and popunder hijackings."""
        host = url.host().lower()
        url_str = url.toString().lower()

        # 1. Block known malicious redirect domains
        if "eflewandatnig" in host or "eflewandatnig" in url_str:
            logger.info(f"Blocked malicious redirect: {url_str}")
            return False

        # 2. If it's a popup or third-party redirect to unknown non-whitelisted domain
        if host and not any(kw in host for kw in self.ALLOWED_HOST_KEYWORDS):
            # Check if it looks like an ad network
            if any(ad_kw in host for ad_kw in ["ad", "click", "pop", "track", "cash", "bet", "redirect"]):
                logger.info(f"Blocked ad navigation request: {url_str}")
                return False

        return super().acceptNavigationRequest(url, _type, isMainFrame)

    def createWindow(self, _type: QWebEnginePage.WebWindowType) -> Optional[QWebEnginePage]:
        """Suppress separate popup windows to prevent blanking out the active page."""
        return None


class ScanGamesWorker(QThread):
    """Background worker for scanning installed Steam games across all libraries."""

    finished = pyqtSignal(list)

    def run(self) -> None:
        games = online_fix_installer.scan_installed_games()
        self.finished.emit(games)


class InstallFixWorker(QThread):
    """Background worker for extracting and installing Steam_Fix into game directory."""

    progress = pyqtSignal(str, int)
    finished = pyqtSignal(bool, str)

    def __init__(
        self,
        archive_path: Path,
        target_game: InstalledGameInfo,
        nickname: Optional[str] = None,
        language: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.archive_path = archive_path
        self.target_game = target_game
        self.nickname = nickname
        self.language = language

    def run(self) -> None:
        self.progress.emit("Arşiv ayıklanıyor ve şifre çözülüyor...", 30)
        success, msg = online_fix_installer.install_fix(
            archive_path=self.archive_path,
            target_game=self.target_game,
            custom_nickname=self.nickname,
            custom_language=self.language,
        )
        self.progress.emit("Tamamlandı!", 100)
        self.finished.emit(success, msg)


class OnlineFixView(QWidget):
    """View for searching, browsing, and installing Online-Fix.me Steam_Fixes with Smart Anchor matching."""

    ONLINEFIX_HOME = "https://online-fix.me/"

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._installed_games: List[InstalledGameInfo] = []
        self._selected_game: Optional[InstalledGameInfo] = None
        self._download_dir = Path(tempfile.gettempdir()) / "STDP_OnlineFixDownloads"
        self._download_dir.mkdir(parents=True, exist_ok=True)
        self._profile_storage = Path.home() / "AppData" / "Local" / "STDP" / "OnlineFixProfile"
        self._profile_storage.mkdir(parents=True, exist_ok=True)

        self._active_downloads: list[QWebEngineDownloadRequest] = []
        self._scan_worker: Optional[ScanGamesWorker] = None
        self._install_worker: Optional[InstallFixWorker] = None

        self._init_ui()
        self._setup_browser_engine()
        self.refresh_installed_games()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 8, 10, 8)
        main_layout.setSpacing(8)

        # 0. Prominent Login Reminder Banner
        self.login_notice_banner = QFrame(self)
        self.login_notice_banner.setStyleSheet(
            "background-color: #24190b; border: 2px solid #f9a825; border-radius: 8px; padding: 8px 14px;"
        )
        banner_layout = QHBoxLayout(self.login_notice_banner)
        banner_layout.setContentsMargins(12, 8, 12, 8)
        banner_layout.setSpacing(14)

        icon_lbl = QLabel("⚠️", self.login_notice_banner)
        icon_lbl.setStyleSheet("font-size: 26px;")

        msg_lbl = QLabel(
            "<b style='color: #f9a825; font-size: 13.5px; letter-spacing: 0.5px;'>ONLINE-FIX KULLANABİLMEK İÇİN MUHAKKAK HESAP GİRİŞİ YAPMALISINIZ BURADAKİ ARAYÜZDEN</b><br>"
            "<span style='color: #e2d2ba; font-size: 12px;'>Online-Fix.me üzerinden indirme linklerini görebilmek ve dosyaları sorunsuz indirebilmek için sitede aktif bir hesabınızın açık olması gerekir. "
            "Sağ taraftaki dahili tarayıcıdan kendi hesabınızla <b>1 kez</b> giriş yapmanız yeterlidir; oturumunuz STDP içinde <b>kalıcı olarak</b> kaydedilecektir.</span>",
            self.login_notice_banner,
        )
        msg_lbl.setWordWrap(True)

        self.btn_dismiss_login = QPushButton("✕ Bir daha gösterme", self.login_notice_banner)
        self.btn_dismiss_login.setStyleSheet(
            "background-color: #f9a825; color: #101822; font-weight: bold; font-size: 12px; padding: 8px 16px; border-radius: 5px;"
        )
        self.btn_dismiss_login.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_dismiss_login.clicked.connect(self._dismiss_login_notice)

        banner_layout.addWidget(icon_lbl)
        banner_layout.addWidget(msg_lbl, 1)
        banner_layout.addWidget(self.btn_dismiss_login)

        main_layout.addWidget(self.login_notice_banner)

        # Hide banner if already dismissed previously
        if config_manager.config.onlinefix_login_prompt_shown:
            self.login_notice_banner.setVisible(False)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background-color: #1e3048; width: 3px; }")

        # ----------------- LEFT PANEL: Installed Games -----------------
        left_panel = QFrame(self)
        left_panel.setProperty("class", "surface-card")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(8)

        # Header
        left_hdr = QHBoxLayout()
        hdr_title = QLabel("🎮 Yüklü Steam Oyunları", left_panel)
        hdr_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #66c0f4;")
        
        self.btn_refresh_games = QPushButton("🔄 Yenile", left_panel)
        self.btn_refresh_games.setFixedSize(75, 28)
        self.btn_refresh_games.clicked.connect(self.refresh_installed_games)

        left_hdr.addWidget(hdr_title)
        left_hdr.addStretch()
        left_hdr.addWidget(self.btn_refresh_games)
        left_layout.addLayout(left_hdr)

        # Search filter
        self.game_search_input = QLineEdit(left_panel)
        self.game_search_input.setPlaceholderText("🔍 Yüklü oyunlarda ara...")
        self.game_search_input.textChanged.connect(self._filter_games_table)
        left_layout.addWidget(self.game_search_input)

        # Games Table
        self.games_table = QTableWidget(left_panel)
        self.games_table.setColumnCount(4)
        self.games_table.setHorizontalHeaderLabels(["Oyun Adı", "AppID", "Motor", "Fix Durumu"])
        self.games_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.games_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.games_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.games_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.games_table.verticalHeader().setVisible(False)
        self.games_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.games_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.games_table.itemSelectionChanged.connect(self._on_game_selected)
        left_layout.addWidget(self.games_table, 1)

        # Selected Game Details & Fix Config Box
        self.details_box = QGroupBox("Seçili Oyun İşlemleri", left_panel)
        details_layout = QVBoxLayout(self.details_box)
        details_layout.setContentsMargins(10, 10, 10, 10)
        details_layout.setSpacing(6)

        self.lbl_selected_game = QLabel("Bir oyun seçilmedi.", self.details_box)
        self.lbl_selected_game.setStyleSheet("font-weight: bold; color: #f3f6f9; font-size: 13px;")

        self.lbl_selected_path = QLabel("", self.details_box)
        self.lbl_selected_path.setStyleSheet("color: #93a7ba; font-size: 11px;")
        self.lbl_selected_path.setWordWrap(True)

        self.lbl_anchor_hint = QLabel("", self.details_box)
        self.lbl_anchor_hint.setStyleSheet("color: #57cb65; font-size: 11px; font-weight: bold;")

        # Config inputs
        cfg_layout = QHBoxLayout()
        self.input_nick = QLineEdit("STDP_Player", self.details_box)
        self.input_nick.setPlaceholderText("Online Nickname")
        self.input_lang = QLineEdit("turkish", self.details_box)
        self.input_lang.setPlaceholderText("Dil (english, turkish...)")
        cfg_layout.addWidget(QLabel("Nick:", self.details_box))
        cfg_layout.addWidget(self.input_nick)
        cfg_layout.addWidget(QLabel("Dil:", self.details_box))
        cfg_layout.addWidget(self.input_lang)

        # Action Buttons
        self.btn_install_direct = QPushButton("⚡ Seçili Oyuna Steam_Fix Kur (.zip / .rar)", self.details_box)
        self.btn_install_direct.setProperty("class", "primary-btn")
        self.btn_install_direct.setFixedHeight(36)
        self.btn_install_direct.setStyleSheet(
            "background-color: #57cb65; color: #101822; font-weight: bold; font-size: 13px;"
        )
        self.btn_install_direct.clicked.connect(self._on_install_direct_clicked)

        btn_layout = QHBoxLayout()
        self.btn_open_folder = QPushButton("📂 Klasörü Aç", self.details_box)
        self.btn_open_folder.clicked.connect(self._open_game_folder)

        self.btn_revert_fix = QPushButton("🔄 Fix'i Kaldır (Orijinale Dön)", self.details_box)
        self.btn_revert_fix.setStyleSheet("background-color: #3b2024; color: #ef5350; border: 1px solid #ef5350;")
        self.btn_revert_fix.clicked.connect(self._revert_selected_fix)

        btn_layout.addWidget(self.btn_open_folder)
        btn_layout.addWidget(self.btn_revert_fix)

        details_layout.addWidget(self.lbl_selected_game)
        details_layout.addWidget(self.lbl_selected_path)
        details_layout.addWidget(self.lbl_anchor_hint)
        details_layout.addLayout(cfg_layout)
        details_layout.addWidget(self.btn_install_direct)
        details_layout.addLayout(btn_layout)

        left_layout.addWidget(self.details_box)
        splitter.addWidget(left_panel)

        # ----------------- RIGHT PANEL: Online-Fix Browser & Manual Drop -----------------
        right_panel = QFrame(self)
        right_panel.setProperty("class", "surface-card")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(8, 8, 8, 8)
        right_layout.setSpacing(6)

        self.right_tabs = QTabWidget(right_panel)

        # Tab 1: Embedded Online-Fix Browser
        browser_tab = QWidget()
        browser_layout = QVBoxLayout(browser_tab)
        browser_layout.setContentsMargins(4, 4, 4, 4)
        browser_layout.setSpacing(6)

        # Browser Nav bar
        b_nav = QHBoxLayout()
        self.btn_b_back = QPushButton("◀", browser_tab)
        self.btn_b_back.setFixedSize(30, 28)
        self.btn_b_back.clicked.connect(lambda: self.web_view.back())

        self.btn_b_refresh = QPushButton("🔄", browser_tab)
        self.btn_b_refresh.setFixedSize(30, 28)
        self.btn_b_refresh.clicked.connect(lambda: self.web_view.reload())

        self.btn_b_home = QPushButton("🏠", browser_tab)
        self.btn_b_home.setFixedSize(30, 28)
        self.btn_b_home.clicked.connect(lambda: self.web_view.setUrl(QUrl(self.ONLINEFIX_HOME)))

        self.b_url_input = QLineEdit(browser_tab)
        self.b_url_input.setPlaceholderText("https://online-fix.me/ veya oyun ara...")
        self.b_url_input.returnPressed.connect(self._navigate_browser_url)

        self.btn_b_go = QPushButton("➔ Git", browser_tab)
        self.btn_b_go.setFixedSize(60, 28)
        self.btn_b_go.setProperty("class", "primary-btn")
        self.btn_b_go.clicked.connect(self._navigate_browser_url)

        b_nav.addWidget(self.btn_b_back)
        b_nav.addWidget(self.btn_b_refresh)
        b_nav.addWidget(self.btn_b_home)
        b_nav.addWidget(self.b_url_input, 1)
        b_nav.addWidget(self.btn_b_go)
        browser_layout.addLayout(b_nav)

        # Download Intercept Banner
        self.fix_banner = QFrame(browser_tab)
        self.fix_banner.setStyleSheet("background-color: #122338; border: 1px solid #66c0f4; border-radius: 6px;")
        self.fix_banner.setVisible(False)
        fb_layout = QVBoxLayout(self.fix_banner)
        fb_layout.setContentsMargins(10, 8, 10, 8)
        fb_layout.setSpacing(4)

        self.fix_banner_label = QLabel("📥 Fix İndiriliyor...", self.fix_banner)
        self.fix_banner_label.setStyleSheet("color: #66c0f4; font-weight: bold;")
        self.fix_banner_progress = QProgressBar(self.fix_banner)
        fb_layout.addWidget(self.fix_banner_label)
        fb_layout.addWidget(self.fix_banner_progress)
        browser_layout.addWidget(self.fix_banner)

        # WebEngine
        self.web_view = QWebEngineView(browser_tab)
        browser_layout.addWidget(self.web_view, 1)
        self.right_tabs.addTab(browser_tab, "🌐 Online-Fix.me Web Tarayıcısı")

        # Tab 2: Manual Fix File Installer & Drop
        manual_tab = QWidget()
        manual_layout = QVBoxLayout(manual_tab)
        manual_layout.setContentsMargins(16, 16, 16, 16)
        manual_layout.setSpacing(12)

        m_info = QLabel(
            "📦 İndirdiğiniz Steam_Fix (.zip, .rar, .7z) dosyasını buraya yükleyin.\n"
            "Şifre ('online-fix.me') otomatik çözülecek, oyun motoru hiyerarşisi tespit edilecek ve dosyalar doğru alt klasöre yerleştirilecektir.",
            manual_tab,
        )
        m_info.setStyleSheet("color: #93a7ba; font-size: 13px; line-height: 1.4;")
        m_info.setWordWrap(True)
        manual_layout.addWidget(m_info)

        # Drop/Select File Box
        self.btn_select_fix_file = QPushButton("📁 Bilgisayardan Fix Dosyası Seç (.zip / .rar / .7z)", manual_tab)
        self.btn_select_fix_file.setProperty("class", "primary-btn")
        self.btn_select_fix_file.setFixedHeight(44)
        self.btn_select_fix_file.clicked.connect(self._browse_fix_file)
        manual_layout.addWidget(self.btn_select_fix_file)

        # File preview info
        self.lbl_fix_file_info = QLabel("Henüz dosya seçilmedi.", manual_tab)
        self.lbl_fix_file_info.setStyleSheet("color: #66c0f4; font-size: 12px; font-weight: bold;")
        manual_layout.addWidget(self.lbl_fix_file_info)

        self.btn_install_manual_fix = QPushButton("⚡ Seçili Oyuna Bu Fix'i Kur", manual_tab)
        self.btn_install_manual_fix.setFixedHeight(40)
        self.btn_install_manual_fix.setStyleSheet("background-color: #57cb65; color: #101822; font-weight: bold;")
        self.btn_install_manual_fix.setEnabled(False)
        self.btn_install_manual_fix.clicked.connect(self._install_manual_selected_fix)
        manual_layout.addWidget(self.btn_install_manual_fix)

        manual_layout.addStretch()
        self.right_tabs.addTab(manual_tab, "📦 Manuel Fix Yükle (.zip/.rar)")

        right_layout.addWidget(self.right_tabs, 1)
        splitter.addWidget(right_panel)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        main_layout.addWidget(splitter, 1)

        self._current_manual_archive: Optional[Path] = None

    def _setup_browser_engine(self) -> None:
        """Configure persistent profile and download interception with popup handler."""
        self.profile = QWebEngineProfile("STDP_OnlineFix_Profile", self)
        self.profile.setPersistentStoragePath(str(self._profile_storage))
        self.profile.setCachePath(str(self._profile_storage / "Cache"))
        self.profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies
        )
        self.profile.downloadRequested.connect(self._on_download_requested)

        # Attach AdBlocker
        self._ad_interceptor = setup_adblocker_on_profile(self.profile)

        # Use custom page with popup createWindow redirection
        self.web_page = CustomWebEnginePage(self.profile, self.web_view)
        self.web_page.setBackgroundColor(QColor("#101822"))
        self.web_view.setPage(self.web_page)
        self.web_view.setStyleSheet("background-color: #101822;")
        self.web_view.setUrl(QUrl(self.ONLINEFIX_HOME))
        self.web_view.urlChanged.connect(lambda qurl: self.b_url_input.setText(qurl.toString()))

    def _navigate_browser_url(self) -> None:
        raw = self.b_url_input.text().strip()
        if not raw:
            return
        if not raw.startswith(("http://", "https://")):
            raw = f"https://online-fix.me/index.php?do=search&subaction=search&story={raw}"
        self.web_view.setUrl(QUrl(raw))

    def refresh_installed_games(self) -> None:
        """Scan installed games in background thread."""
        self.btn_refresh_games.setEnabled(False)
        self.btn_refresh_games.setText("⏳ Taranıyor...")
        self._scan_worker = ScanGamesWorker()
        self._scan_worker.finished.connect(self._on_games_scanned)
        self._scan_worker.start()

    def _on_games_scanned(self, games: List[InstalledGameInfo]) -> None:
        self._installed_games = games
        self.btn_refresh_games.setEnabled(True)
        self.btn_refresh_games.setText("🔄 Yenile")
        self._populate_games_table(games)

    def _populate_games_table(self, games: List[InstalledGameInfo]) -> None:
        self.games_table.setAlternatingRowColors(True)
        self.games_table.setRowCount(0)
        for row, g in enumerate(games):
            self.games_table.insertRow(row)

            # Name
            name_item = QTableWidgetItem(g.name)
            self.games_table.setItem(row, 0, name_item)

            # AppID
            appid_item = QTableWidgetItem(str(g.app_id))
            appid_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.games_table.setItem(row, 1, appid_item)

            # Engine
            engine_item = QTableWidgetItem(g.detected_engine)
            engine_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.games_table.setItem(row, 2, engine_item)

            # Fix Status
            if g.has_online_fix:
                status_item = QTableWidgetItem("✓ Fix Kurulu")
                status_item.setForeground(Qt.GlobalColor.green)
            else:
                status_item = QTableWidgetItem("Orijinal")
                status_item.setForeground(Qt.GlobalColor.gray)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.games_table.setItem(row, 3, status_item)

    def _filter_games_table(self, text: str) -> None:
        query = text.lower().strip()
        filtered = [g for g in self._installed_games if query in g.name.lower() or query in str(g.app_id)]
        self._populate_games_table(filtered)

    def _on_game_selected(self) -> None:
        selected_rows = self.games_table.selectionModel().selectedRows()
        if not selected_rows:
            self._selected_game = None
            self.lbl_selected_game.setText("Bir oyun seçilmedi.")
            self.lbl_selected_path.setText("")
            self.lbl_anchor_hint.setText("")
            return

        row = selected_rows[0].row()
        name_item = self.games_table.item(row, 0)
        if not name_item:
            return

        game_name = name_item.text()
        for g in self._installed_games:
            if g.name == game_name:
                self._selected_game = g
                status_text = "🟢 [Fix Aktif]" if g.has_online_fix else "⚪ [Orijinal]"
                self.lbl_selected_game.setText(f"{g.name} (AppID: {g.app_id}) {status_text}")
                self.lbl_selected_path.setText(f"📁 {g.game_path}")

                sub = f" ➔ Hedef Alt Dizin: '{g.target_subfolder}'" if g.target_subfolder else " ➔ Kök Dizin"
                exe_hint = f" | Ana Exe: '{g.primary_exe}'" if g.primary_exe else ""
                self.lbl_anchor_hint.setText(f"🔍 Motor: {g.detected_engine}{sub}{exe_hint}")
                break

    def _dismiss_login_notice(self) -> None:
        """Dismiss the login reminder banner and save preference."""
        self.login_notice_banner.setVisible(False)
        config_manager.update(onlinefix_login_prompt_shown=True)

    def _on_install_direct_clicked(self) -> None:
        """Directly install a fix archive to the currently selected game."""
        if not self._selected_game:
            QMessageBox.warning(self, "Oyun Seçilmedi", "Lütfen önce soldaki listeden fix kurmak istediğiniz oyuna tıklayın.")
            return

        # Check if there is any recently downloaded fix in STDP download cache
        recent_archives = (
            list(self._download_dir.glob("*.zip"))
            + list(self._download_dir.glob("*.rar"))
            + list(self._download_dir.glob("*.7z"))
        )
        recent_archives.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        if recent_archives:
            latest = recent_archives[0]
            reply = QMessageBox.question(
                self,
                "İndirilen Fix Paketi Bulundu",
                f"Son indirilen fix paketi bulundu:\n'{latest.name}'\n\n"
                f"Bu dosya doğrudan '{self._selected_game.name}' oyununa kurulsun mu?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._start_fix_installation(latest, self._selected_game)
                return

        # Otherwise, open file dialog for user to select the downloaded .zip/.rar
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            f"'{self._selected_game.name}' İçin Fix Dosyası Seç (.zip / .rar / .7z)",
            "",
            "Fix Paketleri (*.zip *.rar *.7z);;Tüm Dosyalar (*.*)",
        )
        if file_path:
            self._start_fix_installation(Path(file_path), self._selected_game)

    def _open_game_folder(self) -> None:
        if not self._selected_game or not self._selected_game.game_path.exists():
            QMessageBox.warning(self, "Klasör Hatası", "Lütfen önce geçerli bir oyun seçin.")
            return
        os.startfile(self._selected_game.game_path)

    def _revert_selected_fix(self) -> None:
        if not self._selected_game:
            QMessageBox.warning(self, "Seçim Yok", "Lütfen fix'i kaldırılacak oyunu seçin.")
            return

        reply = QMessageBox.question(
            self,
            "Fix'i Kaldır",
            f"'{self._selected_game.name}' oyunundaki Steam_Fix kaldırılıp orijinal dosyalar geri yüklensin mi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        success, msg = online_fix_installer.revert_fix(self._selected_game)
        if success:
            QMessageBox.information(self, "Başarılı", msg)
            self.refresh_installed_games()
        else:
            QMessageBox.critical(self, "Hata", msg)

    def _browse_fix_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Online-Fix / Steam_Fix Arşivi Seç",
            "",
            "Fix Paketleri (*.zip *.rar *.7z);;Tüm Dosyalar (*.*)",
        )
        if not file_path:
            return

        p = Path(file_path)
        self._current_manual_archive = p
        self.lbl_fix_file_info.setText(f"Seçilen Dosya: {p.name} ({p.stat().st_size / 1024 / 1024:.2f} MB)")
        self.btn_install_manual_fix.setEnabled(True)

        analysis = online_fix_installer.analyze_fix_archive(p, self._installed_games)
        if analysis.matched_game:
            for row, g in enumerate(self._installed_games):
                if g.app_id == analysis.matched_game.app_id:
                    self.games_table.selectRow(row)
                    self.lbl_fix_file_info.setText(
                        f"🎯 Otomatik Eşleşti: '{g.name}' (%{int(analysis.confidence * 100)})\nDosya: {p.name}"
                    )
                    break

    def _install_manual_selected_fix(self) -> None:
        if not self._current_manual_archive or not self._selected_game:
            QMessageBox.warning(self, "Eksik Bilgi", "Lütfen hem bir oyun seçin hem de geçerli bir fix dosyası belirleyin.")
            return

        self._start_fix_installation(self._current_manual_archive, self._selected_game)

    def _on_download_requested(self, download: QWebEngineDownloadRequest) -> None:
        filename = download.downloadFileName() or "onlinefix_package.zip"
        dest_path = self._download_dir / filename

        download.setDownloadDirectory(str(self._download_dir))
        download.setDownloadFileName(filename)
        download.accept()

        self._active_downloads.append(download)
        self.fix_banner.setVisible(True)
        self.fix_banner_label.setText(f"📥 Fix Paketi İndiriliyor: {filename}...")
        self.fix_banner_progress.setValue(25)

        download.isFinishedChanged.connect(lambda: self._on_download_finished(download, dest_path))

    def _on_download_finished(self, download: QWebEngineDownloadRequest, file_path: Path) -> None:
        if download.state() == QWebEngineDownloadRequest.DownloadState.DownloadCompleted:
            self.fix_banner_label.setText(f"⚡ '{file_path.name}' inceleniyor...")
            self.fix_banner_progress.setValue(70)

            analysis = online_fix_installer.analyze_fix_archive(file_path, self._installed_games)
            target = analysis.matched_game or self._selected_game

            if target:
                reply = QMessageBox.question(
                    self,
                    "Fix İndirildi - Kurulsun mu?",
                    f"İndirilen '{file_path.name}' paketi '{target.name}' oyunu için tespit edildi.\n\n"
                    f"Motor / Hedef: {target.detected_engine} ({target.target_subfolder or 'Kök Dizin'})\n"
                    "Orijinal dosyalar otomatik yedeklenerek Fix kurulsun mu?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self._start_fix_installation(file_path, target)
                else:
                    self.fix_banner.setVisible(False)
            else:
                self.fix_banner.setVisible(False)
                QMessageBox.information(
                    self,
                    "Fix İndirildi",
                    f"'{file_path.name}' indirildi. Lütfen soldaki listeden hedef oyunu seçip 'Manuel Fix Yükle' sekmesinden kurulumu başlatın.",
                )
        else:
            self.fix_banner.setVisible(False)

    def _start_fix_installation(self, archive_path: Path, target_game: InstalledGameInfo) -> None:
        self.fix_banner.setVisible(True)
        self.fix_banner_label.setText(f"⚡ '{target_game.name}' için Steam_Fix kuruluyor...")
        self.fix_banner_progress.setValue(50)

        nick = self.input_nick.text().strip() or "STDP_Player"
        lang = self.input_lang.text().strip() or "turkish"

        self._install_worker = InstallFixWorker(
            archive_path=archive_path,
            target_game=target_game,
            nickname=nick,
            language=lang,
            parent=self,
        )
        self._install_worker.finished.connect(self._on_fix_install_finished)
        self._install_worker.start()

    def _on_fix_install_finished(self, success: bool, msg: str) -> None:
        self.fix_banner.setVisible(False)
        if success:
            QMessageBox.information(self, "Steam_Fix Kuruldu! 🎉", msg)
            self.refresh_installed_games()
        else:
            QMessageBox.critical(self, "Kurulum Hatası", msg)
