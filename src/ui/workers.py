"""Background QThread workers for non-blocking UI operations."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Union
from PyQt6.QtCore import QThread, pyqtSignal

from src.core.config import config_manager
from src.core.logger import get_logger
from src.core.models import AppInfo, GamePackage, SystemHealth
from src.depotbox.client import depotbox_client
from src.depotbox.downloader import manifest_downloader
from src.depotbox.extractor import archive_extractor
from src.steam.acf_builder import ACFBuilder
from src.steam.detector import steam_detector
from src.steam.key_injector import KeyInjector
from src.steam.process_manager import SteamProcessManager
from src.unlockers.factory import get_unlocker

logger = get_logger("ui.workers")


class SearchWorker(QThread):
    """Asynchronous search worker."""

    results_ready = pyqtSignal(list)  # List[AppInfo]
    error_occurred = pyqtSignal(str)

    def __init__(self, query: str) -> None:
        super().__init__()
        self.query = query

    def run(self) -> None:
        try:
            results = depotbox_client.search(self.query)
            self.results_ready.emit(results)
        except Exception as e:
            logger.error(f"Search worker error: {e}")
            self.error_occurred.emit(str(e))


class PackageImportWorker(QThread):
    """Worker for parsing dropped archives and files."""

    package_ready = pyqtSignal(object)  # GamePackage
    error_occurred = pyqtSignal(str)

    def __init__(self, file_path: Union[Path, str]) -> None:
        super().__init__()
        self.file_path = file_path

    def run(self) -> None:
        try:
            pkg = archive_extractor.extract_package(self.file_path)
            self.package_ready.emit(pkg)
        except Exception as e:
            logger.error(f"Archive extraction worker error: {e}")
            self.error_occurred.emit(str(e))


class InjectGameWorker(QThread):
    """End-to-end game manifest download, ACF generation, config key injection, and hook injection worker."""

    progress = pyqtSignal(str, int)  # (status_message, percent 0-100)
    finished = pyqtSignal(bool, str)  # (success, message)

    def __init__(
        self,
        app_info: AppInfo,
        target_library_path: Path,
        package: Optional[GamePackage] = None,
        ready_to_install: bool = True,
    ) -> None:
        super().__init__()
        self.app_info = app_info
        self.target_library_path = target_library_path
        self.package = package
        self.ready_to_install = ready_to_install

    def run(self) -> None:
        cfg = config_manager.config
        steam_path = (
            Path(cfg.steam_path) if cfg.steam_path else steam_detector.find_steam_path()
        )

        if not steam_path or not steam_path.exists():
            self.finished.emit(False, "Steam kurulum dizini bulunamadı!")
            return

        try:
            # 1. Step: Steam Shutdown if running and configured
            if cfg.auto_shutdown_steam and SteamProcessManager.is_running():
                self.progress.emit("Steam istemcisi güvenle kapatılıyor...", 15)
                logger.info("Auto-shutting down Steam for safe file writing...")
                SteamProcessManager.shutdown_steam(steam_path=steam_path, timeout_seconds=10)

            # 2. Step: Download / Transfer Manifests
            self.progress.emit("Manifest dosyaları kopyalanıyor...", 35)
            if self.package and self.package.manifests:
                from src.steam.depotcache_manager import DepotCacheManager
                dm = DepotCacheManager(steam_path)
                for mf in self.package.manifests:
                    dm.save_manifest(mf.depot_id, mf.manifest_id, mf.file_path)
            elif self.app_info.depots:
                self.progress.emit("Manifestler indiriliyor...", 45)
                manifest_downloader.download_app_manifests(
                    self.app_info,
                    steam_path,
                )

            # 3. Step: Inject Depot Decryption Keys directly into Steam/config/config.vdf
            self.progress.emit("Depot anahtarları konfigürasyona işleniyor...", 60)
            KeyInjector.inject_depot_keys_to_config_vdf(steam_path, self.app_info)

            # 4. Step: Clean any stale/fake ACF and library registration so Steam displays the clean 'YÜKLE' button
            self.progress.emit("Steam kütüphane kaydı hazırlanıyor...", 75)
            ACFBuilder.remove_app_manifest_and_registration(
                steam_path=steam_path,
                app_id=self.app_info.app_id,
            )

            # 5. Step: Inject via Active Unlocker (SteamTools / GreenLuma Hook)
            self.progress.emit("Kilit açıcı adaptörü uygulanıyor...", 85)
            unlocker = get_unlocker(cfg.active_unlocker or "steamtools")
            if unlocker:
                if hasattr(unlocker, "ensure_steamtools_running"):
                    unlocker.ensure_steamtools_running(steam_path)
                unlocker.inject_game(steam_path, self.app_info, self.package)

            # 6. Step: Restart Steam
            if cfg.auto_restart_steam:
                self.progress.emit("Steam yeniden başlatılıyor ve kilit motoru bağlanıyor...", 90)
                if unlocker and hasattr(unlocker, "ensure_steamtools_running"):
                    unlocker.ensure_steamtools_running(steam_path)
                SteamProcessManager.start_steam(steam_path)
                self.progress.emit("Steam kütüphanesi yükleniyor...", 95)
                QThread.msleep(4500)

            # 7. Step: Navigate to game in Steam Library & open install dialog
            self.progress.emit("Steam kütüphanesine yönlendiriliyor...", 98)
            SteamProcessManager.trigger_install(self.app_info.app_id)
            QThread.msleep(800)
            SteamProcessManager.trigger_nav_game(self.app_info.app_id)

            self.progress.emit("Tamamlandı!", 100)
            self.finished.emit(
                True,
                f"'{self.app_info.name}' (AppID: {self.app_info.app_id}) Steam kütüphanenize başarıyla eklendi!\n\n"
                f"Steam kütüphanenizde doğrudan 'YÜKLE / İNDİR' butonu açılmıştır. Butona tıklayarak oyunun asıl dosyalarını doğrudan Steam üzerinden indirebilirsiniz.\n\n"
                f"💡 Not: Lisans hatası almamak için arka planda SteamTools kilit motorunun açık kalması gerekir (sağ altta sistem tepsisinde simgesi görünmelidir)."
            )

        except Exception as e:
            logger.error(f"Error during game injection pipeline: {e}")
            self.finished.emit(False, f"Aktarım hatası: {e}")


class HealthCheckWorker(QThread):
    """Background system diagnostic worker."""

    health_ready = pyqtSignal(object)  # SystemHealth

    def run(self) -> None:
        health = steam_detector.check_system_health()
        self.health_ready.emit(health)
